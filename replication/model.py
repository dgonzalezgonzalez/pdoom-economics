"""Finite-horizon public-state game. Arrays implement the paper's Bellman equations."""
from dataclasses import dataclass, replace
from itertools import combinations
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ("open", "standard", "ban")
ACTIONS = ("hold", "supervised", "delegate_low", "delegate_high")


@dataclass(frozen=True)
class Params:
    horizon: int = 10
    beta: float = .96
    beta_ai: float = .98
    terminal_years: float = 5
    terminal_ai: float = 1
    sigma: float = 1.3
    commercial_scale: float = 1
    capture_share: float = .5
    prize: float = 1
    government_prize: float = 0
    contest_power: float = 2
    private_life: float = 5
    social_life: float = 40
    research_cost: float = .25
    project_size: float = 1
    cost_exponent: float = .8
    safety_cost: float = .15
    safety_resource: float = .5
    recovery_share: float = 0
    acquisition_boundary: bool = False
    external_finance: float = .65
    research_eta: float = .4
    delegation_multiplier: float = 2.5
    research_feedback: float = .9
    research_difficulty: float = .5
    effort_elasticity: float = .6
    bottleneck: float = 20
    launch_capability: float = 2
    q0: float = .03
    loss_correlation: float = 0
    safety_effect: float = 2
    infrastructure: tuple = (1.5, 1.5)
    resource_total: int = 6
    resource_initial: int = 1
    human_subsistence: int = 2
    seizure_capability: float = 2.5
    seizure_cost: float = .5
    containment: float = .08
    containment_decay: float = .5
    resource_enabled: bool = True
    human_resource_elasticity: float = 1
    capability_max: float = 14
    capability_step: float = .5
    ai_max: float = 100
    ai_step: float = .25
    selection: str = "low_risk"
    seed: int = 20261021

    @classmethod
    def load(cls):
        return cls(**json.loads((ROOT / "replication/parameters.json").read_text()))


def benefits(a, p):
    """R_sigma(a) = m integral_1^a u^(-sigma) du; a is positive."""
    a = np.asarray(a)
    return p.commercial_scale * (np.log(a) if abs(p.sigma-1) < 1e-10
                                else np.expm1((1-p.sigma)*np.log(a))/(1-p.sigma))


def gain(a, e, p, delegated=False):
    return (p.research_eta * (p.delegation_multiplier if delegated else 1)
            * np.asarray(e)**p.effort_elasticity
            * np.asarray(a)**(p.research_feedback-p.research_difficulty)
            / (1+np.asarray(a)/p.bottleneck))


def interpolation(grid, points):
    points = np.asarray(points)
    high = np.searchsorted(grid, points, side="right").clip(1, len(grid)-1)
    low = high-1
    weight = ((points-grid[low])/(grid[high]-grid[low])).clip(0, 1)
    return low, high, weight


def interp(values, mapping):
    low, high, weight = mapping
    weight=np.asarray(weight)[(...,)+(None,)*(values.ndim-1)]
    return values[low]*(1-weight)+values[high]*weight


def supports(n):
    return [s for k in range(1, n+1) for s in combinations(range(n), k)]


def equilibria(A, B, tol=1e-8, fast=False):
    """Full mode: one LP representative per feasible support, including unequal supports.

    Fast mode first returns verified equal-size, nonsingular supports at the smallest
    successful size; only if none exist does it fall back to full LP enumeration.
    Neither mode parameterizes continua within a degenerate support.
    """
    out = []
    if fast:
        for size in range(2,min(A.shape)+1):
            for I in combinations(range(A.shape[0]),size):
                for J in combinations(range(A.shape[1]),size):
                    def balanced(C,own,other):
                        sub=C[np.ix_(own,other)]
                        system=np.block([[sub,-np.ones((size,1))],[np.ones((1,size)),np.zeros((1,1))]])
                        try: sol=np.linalg.solve(system,np.r_[np.zeros(size),1.])[:size]
                        except np.linalg.LinAlgError: return None
                        return sol if np.min(sol)>1e-10 else None
                    q=balanced(A,I,J);r=balanced(B.T,J,I)
                    if q is None or r is None:continue
                    x,y=np.zeros(A.shape[0]),np.zeros(A.shape[1])
                    x[list(I)]=r;y[list(J)]=q
                    if exploitability(A,B,x,y)<=1e-6:out.append((x,y))
            if out:return out
    for I in supports(A.shape[0]):
        for J in supports(A.shape[1]):
            def opponent(C, own, other):
                # Variables are probabilities on other, common payoff, positive support floor.
                m = len(other)
                eq = [np.r_[np.ones(m), 0, 0]]
                rhs = [1.]
                for i in own:
                    eq.append(np.r_[C[i, list(other)], -1., 0.])
                    rhs.append(0.)
                ub, bound = [], []
                for i in set(range(C.shape[0]))-set(own):
                    ub.append(np.r_[C[i, list(other)], -1., 0.])
                    bound.append(tol)
                for j in range(m):
                    row = np.zeros(m+2); row[j] = -1; row[-1] = 1
                    ub.append(row); bound.append(0.)
                sol = linprog(np.r_[np.zeros(m+1), -1.], A_ub=np.array(ub), b_ub=bound,
                              A_eq=eq, b_eq=rhs, bounds=[(0, 1)]*m+[(None,None),(0,1)], method="highs")
                return sol.x[:m] if sol.success and sol.x[-1] > 1e-10 else None
            q = opponent(A, I, J)
            if q is None: continue
            r = opponent(B.T, J, I)
            if r is None: continue
            x, y = np.zeros(A.shape[0]), np.zeros(A.shape[1])
            x[list(I)] = r; y[list(J)] = q
            if exploitability(A, B, x, y) <= 1e-6:
                out.append((x,y))
    if not out:
        raise ArithmeticError("No verified equilibrium found")
    return out


def exploitability(A, B, x, y):
    return max(float(np.max(A@y)-x@A@y), float(np.max(x@B)-x@B@y), 0.)


def autonomous(p,track_cdf=False):
    """Optimal AI policy plus human life-value and finite-horizon extinction probability."""
    grid = np.arange(1, p.ai_max+p.ai_step/2, p.ai_step)
    K = p.resource_total
    H = p.horizon
    value = np.zeros((H+1, len(grid), K+1))
    life = np.zeros_like(value)
    doom = np.zeros_like(value)
    seized = np.zeros_like(value)
    boundary = np.zeros_like(value)
    survival = np.zeros_like(value)
    recovery = np.zeros_like(value)
    cdf=np.zeros((H+1,H+1,len(grid),K+1)) if track_cdf else None
    initial_human = K-p.resource_initial
    safe = lambda h: (1-p.beta**h)/(1-p.beta)+p.beta**h*p.terminal_years
    for k in range(p.resource_initial, K+1):
        alive = K-k >= p.human_subsistence
        value[0,:,k] = p.terminal_ai*grid
        life[0,:,k] = p.terminal_years*((K-k)/initial_human)**p.human_resource_elasticity if alive else 0
        doom[0,:,k] = float(not alive)
        survival[0,:,k] = p.terminal_years if alive else 0
        if track_cdf:cdf[0,:,:,k]=float(not alive)
    for h in range(1, H+1):
        for k in range(p.resource_initial, K+1):
            alive = K-k >= p.human_subsistence
            candidates = []
            candidate_cdfs=[]
            for y in (0,1):
                if y and (not p.resource_enabled or k == K): continue
                efforts=[0., k/2, float(k)]
                if p.acquisition_boundary:efforts.append(max(0.,k-p.seizure_cost*y))
                for e in sorted(set(efforts)):
                    if e+p.seizure_cost*y > k+1e-10: continue
                    target = grid+gain(grid,e,p)
                    mapping = interpolation(grid,target)
                    risk = (p.containment*np.exp(-p.containment_decay*np.maximum(grid-p.seizure_capability,0))
                            if y and alive else np.zeros(len(grid)))
                    feasible = (grid >= p.seizure_capability) if y else np.ones(len(grid),bool)
                    next_k = k+y
                    w = grid+p.beta_ai*(1-risk)*interp(value[h-1,:,next_k],mapping)
                    w = np.where(feasible,w,-np.inf)
                    current_life = ((K-k)/initial_human)**p.human_resource_elasticity if alive else 0.
                    l = current_life+p.beta*((1-risk)*interp(life[h-1,:,next_k],mapping)+risk*safe(h-1)) if alive else np.zeros(len(grid))
                    d = (1-risk)*interp(doom[h-1,:,next_k],mapping) if alive else np.ones(len(grid))
                    z = (1-risk)*(y+interp(seized[h-1,:,next_k],mapping))
                    b = (1-risk)*np.maximum(target>grid[-1]+1e-9,interp(boundary[h-1,:,next_k],mapping))
                    sv=1+p.beta*((1-risk)*interp(survival[h-1,:,next_k],mapping)+risk*safe(h-1)) if alive else np.zeros(len(grid))
                    rc=p.beta*((1-risk)*interp(recovery[h-1,:,next_k],mapping)+risk*safe(h-1)) if alive else np.zeros(len(grid))
                    candidates.append((w,l,d,z,b,sv,rc))
                    if track_cdf:
                        candidate_cdfs.append(np.vstack([np.zeros(len(grid)),(1-risk)[None,:]*interp(cdf[h-1,:H,:,next_k].T,mapping).T]) if alive else np.ones((H+1,len(grid))))
            stacked = np.stack(candidates)
            best = np.argmax(stacked[:,0,:],axis=0)
            selected = stacked[best,:,np.arange(len(grid))]
            value[h,:,k],life[h,:,k],doom[h,:,k],seized[h,:,k],boundary[h,:,k],survival[h,:,k],recovery[h,:,k] = selected.T
            if track_cdf:cdf[h,:,:,k]=np.stack(candidate_cdfs).transpose(2,0,1)[np.arange(len(grid)),best].T
    result={"grid":grid,"value":value,"life":life,"doom":doom,"seized":seized,"boundary":boundary,
            "survival":survival,"recovery":recovery}
    if track_cdf:result['cdf']=cdf
    return result


def solve(p, policies=("open","open"), planner=False, rogue=None, certificate=False,track_cdf=False):
    """Backward induction; select lowest/highest-risk pure NE, otherwise a verified mixed NE.

    Mixed equilibria coexisting with pure ones are not enumerated. Selection sensitivity is
    an equilibrium comparison, never a bound on the entire equilibrium correspondence.
    """
    assert 0 < p.beta < 1 and 0 < p.capture_share <= 1 and 0 <= p.q0 <= 1
    assert policies[0] in POLICIES and policies[1] in POLICIES
    rogue = autonomous(p,track_cdf) if rogue is None or (track_cdf and 'cdf' not in rogue) else rogue
    grid = np.arange(1,p.capability_max+p.capability_step/2,p.capability_step)
    n, na = len(grid), len(ACTIONS)
    a,b = np.meshgrid(grid,grid,indexing="ij")
    R = benefits(grid,p)
    share = a**p.contest_power/(a**p.contest_power+b**p.contest_power)-.5
    private = [p.private_life+R[:,None]+p.prize*share,
               p.private_life+R[None,:]-p.prize*share]
    welfare = [p.social_life/2+R[:,None]/p.capture_share+p.government_prize*share,
               p.social_life/2+R[None,:]/p.capture_share-p.government_prize*share]
    # Quantities: private V1,V2; jurisdiction W1,W2; doom; escape; boundary.
    prev = np.stack([p.terminal_years*x for x in private+welfare]+[np.zeros((n,n))]*5
                    +[np.full((n,n),p.terminal_years)]*2
                    +[p.terminal_years*(R[:,None]+R[None,:])/p.capture_share,np.zeros((n,n))])
    if track_cdf:prev=np.concatenate([prev,np.zeros((2*(p.horizon+1),n,n))])
    loss_start=13;extinction_start=13+p.horizon+1
    maps,costs,allowed,qs=[],[],[],[]
    root_policies = None
    original_allowed=[]
    certificate_record=None
    certificate_reachable=None
    for i,policy in enumerate(policies):
        mm,cc,aa,qq,original=[],[],[],[],[]
        for action in range(na):
            e = p.project_size*float(action != 0)
            s = float(action == 3)
            delegated = action >= 2
            target = grid+gain(grid,e,p,delegated)
            cost = p.research_cost*grid**p.cost_exponent*e+p.safety_cost*s
            feasible = (cost <= R+p.external_finance+1e-10) & (e+s*p.safety_resource <= p.infrastructure[i]+1e-10)
            if delegated:
                feasible &= grid >= p.launch_capability
                if policy == "ban" or (policy == "standard" and action == 2): feasible[:] = False
            if action == 0: feasible[:]=True
            original.append(feasible.copy())
            if certificate and delegated:feasible[:]=False
            mm.append(interpolation(grid,target)); cc.append(cost); aa.append(feasible)
            qq.append(p.q0*np.exp(-p.safety_effect*s) if delegated else 0.)
        maps.append(mm);costs.append(cc);allowed.append(aa);qs.append(qq)
        original_allowed.append(original)
    reachable=[]
    if certificate:
        for player in range(2):
            levels=[np.arange(n)==0]
            for elapsed in range(p.horizon):
                next_level=np.zeros(n,bool)
                for act in range(na):
                    states=levels[-1]&original_allowed[player][act]
                    lo,hi,weight=maps[player][act]
                    next_level[lo[states&(weight<1)]]=True
                    next_level[hi[states&(weight>0)]]=True
                levels.append(next_level)
            reachable.append(levels)
    stats = {"multiple_pure_state_games":0,"mixed_state_games":0,"max_deviation_gain":0.,"state_games":0}
    initial_actions=[]
    for h in range(1,p.horizon+1):
        Q = np.zeros((len(prev),n,n,na,na))
        for u in range(na):
            li,hi,wi=maps[0][u]
            for v in range(na):
                lj,hj,wj=maps[1][v]
                expected=(prev[:,li[:,None],lj[None,:]]*(1-wi[:,None])*(1-wj[None,:])
                          +prev[:,hi[:,None],lj[None,:]]*wi[:,None]*(1-wj[None,:])
                          +prev[:,li[:,None],hj[None,:]]*(1-wi[:,None])*wj[None,:]
                          +prev[:,hi[:,None],hj[None,:]]*wi[:,None]*wj[None,:])
                q1,q2=qs[0][u],qs[1][v]
                overlap=(1-p.loss_correlation)*q1*q2+p.loss_correlation*min(q1,q2)
                none=1-q1-q2+overlap; f1=q1-overlap/2; f2=q2-overlap/2
                assert abs(none+f1+f2-1)<1e-12
                r1map=interpolation(rogue["grid"],grid+gain(grid,p.project_size*float(u!=0),p,u>=2))
                r2map=interpolation(rogue["grid"],grid+gain(grid,p.project_size*float(v!=0),p,v>=2))
                mix_life=f1*interp(rogue["life"][h-1,:,p.resource_initial],r1map)[:,None]+f2*interp(rogue["life"][h-1,:,p.resource_initial],r2map)[None,:]
                mix_doom=f1*interp(rogue["doom"][h-1,:,p.resource_initial],r1map)[:,None]+f2*interp(rogue["doom"][h-1,:,p.resource_initial],r2map)[None,:]
                mix_survival=f1*interp(rogue["survival"][h-1,:,p.resource_initial],r1map)[:,None]+f2*interp(rogue["survival"][h-1,:,p.resource_initial],r2map)[None,:]
                mix_recovery=f1*interp(rogue["recovery"][h-1,:,p.resource_initial],r1map)[:,None]+f2*interp(rogue["recovery"][h-1,:,p.resource_initial],r2map)[None,:]
                rtarget1=grid+gain(grid,p.project_size*float(u!=0),p,u>=2)
                rtarget2=grid+gain(grid,p.project_size*float(v!=0),p,v>=2)
                mix_boundary=(f1*np.maximum(rtarget1>rogue['grid'][-1]+1e-9,interp(rogue["boundary"][h-1,:,p.resource_initial],r1map))[:,None]
                              +f2*np.maximum(rtarget2>rogue['grid'][-1]+1e-9,interp(rogue["boundary"][h-1,:,p.resource_initial],r2map))[None,:])
                for j in range(2):
                    c=costs[j][u if j==0 else v]
                    c=c[:,None] if j==0 else c[None,:]
                    Q[j,:,:,u,v]=private[j]-c+p.beta*(none*expected[j]+p.private_life*mix_life+p.recovery_share*(private[j]-p.private_life)*mix_recovery)
                    Q[j+2,:,:,u,v]=welfare[j]-c+p.beta*(none*expected[j+2]+p.social_life/2*mix_life+p.recovery_share*(welfare[j]-p.social_life/2)*mix_recovery)
                Q[4,:,:,u,v]=none*expected[4]+mix_doom
                Q[5,:,:,u,v]=none*expected[5]+f1+f2
                target1=grid+gain(grid,p.project_size*float(u!=0),p,u>=2)
                target2=grid+gain(grid,p.project_size*float(v!=0),p,v>=2)
                hit=(target1[:,None]>grid[-1]+1e-9)|(target2[None,:]>grid[-1]+1e-9)
                Q[6,:,:,u,v]=none*np.maximum(expected[6],hit)+mix_boundary
                Q[7,:,:,u,v]=int(u!=0)+int(v!=0)+none*expected[7]
                Q[8,:,:,u,v]=int(u>=2)+int(v>=2)+none*expected[8]
                Q[9,:,:,u,v]=1+p.beta*(none*expected[9]+mix_life)
                Q[10,:,:,u,v]=1+p.beta*(none*expected[10]+mix_survival)
                task=(R[:,None]+R[None,:])/p.capture_share
                Q[11,:,:,u,v]=task+p.beta*(none*expected[11]+p.recovery_share*task*mix_recovery)
                Q[12,:,:,u,v]=costs[0][u][:,None]+costs[1][v][None,:]+p.beta*none*expected[12]
                if track_cdf:
                    for window in range(1,p.horizon+1):
                        Q[loss_start+window,:,:,u,v]=none*expected[loss_start+window-1]+f1+f2
                        mix_partial=(f1*interp(rogue['cdf'][h-1,window-1,:,p.resource_initial],r1map)[:,None]
                                     +f2*interp(rogue['cdf'][h-1,window-1,:,p.resource_initial],r2map)[None,:])
                        Q[extinction_start+window,:,:,u,v]=none*expected[extinction_start+window-1]+mix_partial
        mask=np.array(allowed[0]).T[:,None,:,None]&np.array(allowed[1]).T[None,:,None,:]
        A=np.where(mask,Q[0],-1e12);B=np.where(mask,Q[1],-1e12)
        joints=np.zeros((n,n,na,na))
        if planner:
            score=np.where(mask,Q[2]+Q[3],-np.inf)
            index=score.reshape(n,n,-1).argmax(axis=-1)
            joints.reshape(n,n,-1)[np.arange(n)[:,None],np.arange(n)[None,:],index]=1
        else:
            pure=mask&(A >= A.max(axis=-2,keepdims=True)-1e-9)&(B >= B.max(axis=-1,keepdims=True)-1e-9)
            counts=pure.sum(axis=(-1,-2))
            stats["multiple_pure_state_games"]+=int((counts>1).sum())
            stats["mixed_state_games"]+=int((counts==0).sum())
            stats["state_games"]+=n*n
            risk=Q[4] if p.selection=="low_risk" else -Q[4]
            best=np.where(pure,risk,np.inf).min(axis=(-1,-2),keepdims=True)
            candidate=pure&(risk<=best+1e-10)
            score=np.where(candidate,Q[0]+Q[1],-np.inf)
            index=score.reshape(n,n,-1).argmax(axis=-1)
            joints.reshape(n,n,-1)[np.arange(n)[:,None],np.arange(n)[None,:],index]=1
            for i,j in zip(*np.where(counts==0)):
                valid_i=np.where(np.array(allowed[0])[:,i])[0]
                valid_j=np.where(np.array(allowed[1])[:,j])[0]
                equilibria_here=equilibria(A[i,j][np.ix_(valid_i,valid_j)],B[i,j][np.ix_(valid_i,valid_j)],fast=True)
                def rank(eq):
                    x,y=eq
                    return float(x@risk[i,j][np.ix_(valid_i,valid_j)]@y)
                x,y=min(equilibria_here,key=rank)
                joints[i,j]=0
                joints[i,j][np.ix_(valid_i,valid_j)]=np.outer(x,y)
            x=joints.sum(axis=-1);y=joints.sum(axis=-2)
            va=(joints*A).sum(axis=(-1,-2)); vb=(joints*B).sum(axis=(-1,-2))
            deviation=max(float((np.einsum('ijuv,ijv->iju',A,y).max(axis=-1)-va).max()),
                          float((np.einsum('iju,ijuv->ijv',x,B).max(axis=-1)-vb).max()),0.)
            stats["max_deviation_gain"]=max(stats["max_deviation_gain"],deviation)
            if certificate:
                candidates=[np.einsum('ijuv,ijv->iju',Q[0],y)-va[:,:,None],
                            np.einsum('iju,ijuv->ijv',x,Q[1])-vb[:,:,None]]
                for player,margin in enumerate(candidates):
                    feasible=np.array(original_allowed[player]).T.copy();feasible[:,:2]=False
                    masked=np.where(feasible[:,None,:] if player==0 else feasible[None,:,:],margin,-np.inf)
                    elapsed=p.horizon-h
                    reach=reachable[0][elapsed][:,None]&reachable[1][elapsed][None,:]
                    on_tree=np.where(reach[:,:,None],masked,-np.inf)
                    ir,jr,ar=np.unravel_index(np.argmax(on_tree),on_tree.shape);dr=float(on_tree[ir,jr,ar])
                    if np.isfinite(dr) and (certificate_reachable is None or dr>certificate_reachable['max_delegated_deviation']):
                        certificate_reachable={'max_delegated_deviation':dr,'player':player+1,'a1':float(grid[ir]),'a2':float(grid[jr]),
                                               'remaining_years':h,'action':ACTIONS[ar]}
                    index=np.unravel_index(np.argmax(masked),masked.shape);delta=float(masked[index])
                    if np.isfinite(delta) and (certificate_record is None or delta>certificate_record['max_delegated_deviation']):
                        i,j,act=index;own=i if player==0 else j
                        def continuation(u,v):
                            li,hi,wi=maps[0][u];lj,hj,wj=maps[1][v]
                            return float((1-wi[i])*(1-wj[j])*prev[player,li[i],lj[j]]+wi[i]*(1-wj[j])*prev[player,hi[i],lj[j]]
                                         +(1-wi[i])*wj[j]*prev[player,li[i],hj[j]]+wi[i]*wj[j]*prev[player,hi[i],hj[j]])
                        Gs=sum(joints[i,j,u,v]*continuation(u,v) for u in range(na) for v in range(na))
                        rival=y[i,j] if player==0 else x[i,j]
                        Gd=sum(rival[v]*continuation(act,v) for v in range(na)) if player==0 else sum(rival[u]*continuation(u,act) for u in range(na))
                        target=grid[own]+gain(grid[own],p.project_size,p,True)
                        Zd=p.private_life*float(interp(rogue['life'][h-1,:,p.resource_initial],interpolation(rogue['grid'],target)))
                        # Certificate decomposition uses baseline post-loss rents, not recovery extension.
                        assert p.recovery_share==0
                        ownmix=x[i,j] if player==0 else y[i,j]
                        cs=sum(ownmix[u]*costs[player][u][own] for u in range(na));cd=costs[player][act][own]
                        N=p.beta*(Gd-Gs)-cd+cs;H=Gd-Zd;q=qs[player][act]
                        assert abs(delta-(N-p.beta*q*H))<1e-6
                        certificate_record={'max_delegated_deviation':delta,'player':player+1,'a1':float(grid[i]),'a2':float(grid[j]),
                                            'remaining_years':h,'action':ACTIONS[act],'N':float(N),'H':float(H),'q':float(q),
                                            'financing_slack':float(R[own]+p.external_finance-cd)}
        current=(Q*joints[None,:,:,:,:]).sum(axis=(-1,-2))
        prev=current
        initial_actions.append(joints[0,0].tolist())
        root_policies=joints[0,0]
    assert np.all(prev[4:6]>=-1e-8) and np.all(prev[4:6]<=1+1e-8)
    assert stats["max_deviation_gain"] < 1e-6
    result={"policies":list(policies),"planner":planner,"V1":float(prev[0,0,0]),"V2":float(prev[1,0,0]),
            "W1":float(prev[2,0,0]),"W2":float(prev[3,0,0]),"doom":float(prev[4,0,0]),
            "escape":float(prev[5,0,0]),"boundary_probability":float(prev[6,0,0]),
            "research_cycles":float(prev[7,0,0]),"delegated_cycles":float(prev[8,0,0]),
            "initial_action_joint":root_policies.tolist(),"diagnostics":stats}
    result["welfare"]=result["W1"]+result["W2"]
    result["doom_given_escape"]=result["doom"]/result["escape"] if result["escape"]>1e-12 else None
    annuity=(1-p.beta**p.horizon)/(1-p.beta)+p.beta**p.horizon*p.terminal_years
    result['welfare_components']={'baseline_no_loss':p.social_life*annuity,'task_surplus':float(prev[11,0,0]),
                                  'research_safety_cost':float(prev[12,0,0]),
                                  'mortality_loss':float(p.social_life*(annuity-prev[10,0,0])),
                                  'nonfatal_resource_loss':float(p.social_life*(prev[10,0,0]-prev[9,0,0]))}
    w=result['welfare_components']
    assert abs(result['welfare']-(w['baseline_no_loss']+w['task_surplus']-w['research_safety_cost']-w['mortality_loss']-w['nonfatal_resource_loss']))<1e-6
    if certificate:result['no_delegation_certificate']={'binding':certificate_record,'passes':certificate_record is None or certificate_record['max_delegated_deviation']<=1e-8,
                                                      'scope':'all states and dates of this finite grid game; not all equilibria or an unbounded-state limit',
                                                      'empty_feasible_delegated_set':certificate_record is None,
                                                      'action_reachable_binding':certificate_reachable,
                                                      'action_reachable_passes':certificate_reachable is None or certificate_reachable['max_delegated_deviation']<=1e-8,
                                                      'action_reachable_empty_delegated_set':certificate_reachable is None}
    if track_cdf:
        result['fixed_policy_cumulative_risk']=[{'year':d,'escape':float(prev[loss_start+d,0,0]),'doom':float(prev[extinction_start+d,0,0])} for d in range(p.horizon+1)]
        assert abs(result['fixed_policy_cumulative_risk'][-1]['doom']-result['doom'])<1e-8
        assert abs(result['fixed_policy_cumulative_risk'][-1]['escape']-result['escape'])<1e-8
        for field in ['escape','doom']:
            assert np.all(np.diff([row[field] for row in result['fixed_policy_cumulative_risk']])>=-1e-9)
        assert all(0<=row['doom']<=row['escape']+1e-9<=1+1e-8 for row in result['fixed_policy_cumulative_risk'])
    result["initial_delegate_probability"]=float(root_policies[2:,:].sum()+root_policies[:,2:].sum())/2
    return result


def policy_game(p):
    rogue=autonomous(p)
    cases={f"{x}/{y}":solve_verified_domain(p,(x,y),rogue=rogue) for x in POLICIES for y in POLICIES}
    A=np.array([[cases[f"{x}/{y}"]["W1"] for y in POLICIES] for x in POLICIES])
    B=np.array([[cases[f"{x}/{y}"]["W2"] for y in POLICIES] for x in POLICIES])
    eqs=equilibria(A,B)
    return {"cases":cases,"government_equilibria":[{"p1":x.tolist(),"p2":y.tolist(),"deviation":exploitability(A,B,x,y)} for x,y in eqs],
            "coordinated":max(cases,key=lambda k:cases[k]["welfare"]),"planner":solve_verified_domain(p,planner=True,rogue=rogue)}


def solve_verified_domain(p,policies=("open","open"),planner=False,rogue=None,certificate=False,track_cdf=False):
    """Cover all feasible paths, including deviations, before solving the game."""
    controlled,ai=reachable_bounds(p)
    expanded=controlled>p.capability_max or ai>p.ai_max
    p=replace(p,capability_max=max(p.capability_max,controlled),ai_max=max(p.ai_max,ai))
    if rogue is not None and rogue['grid'][-1]<p.ai_max-1e-9:rogue=None
    r=solve(p,policies,planner,rogue,certificate,track_cdf)
    if r['boundary_probability']>=1e-9:
        raise ArithmeticError('Clipping despite all-path domain bound')
    r.update(grid_expansions=int(expanded),capability_ceiling=p.capability_max,ai_ceiling=p.ai_max,
             domain_certificate={'controlled_all_path_bound':controlled,'autonomous_all_path_bound':ai,
                                 'covers':'every action path from a1=a2=1 through the finite horizon, including deviations'})
    return r


def reachable_bounds(p):
    """Conservative analytic envelopes; never use the selected equilibrium to set a grid.

    Every positive controlled action has e=project_size. When sigma>1, R<=m/(sigma-1)
    gives an action-independent financing cutoff. A single research jump can overshoot
    that cutoff, and is explicitly included. Autonomous bounds allow maximal compute
    for another full horizon after the largest possible launch, a conservative superset.
    """
    exponent=p.research_feedback-p.research_difficulty
    assert p.horizon>=1 and p.bottleneck>0 and p.capability_step>0 and p.ai_step>0 and p.project_size>0
    def rounded(a,step):
        return 1+math.ceil((a-1+1e-9)/step)*step
    def max_shape(upper):
        if exponent<=0:point=1.
        elif exponent<1:point=min(upper,max(1.,p.bottleneck*exponent/(1-exponent)))
        else:point=upper
        return point**exponent/(1+point/p.bottleneck)
    cutoff=math.inf
    if p.sigma>1 and p.cost_exponent>0 and p.research_cost>0:
        cutoff=((p.commercial_scale/(p.sigma-1)+p.external_finance)/(p.research_cost*p.project_size))**(1/p.cost_exponent)
    upper=1.
    for _ in range(p.horizon):
        feasible=min(upper,cutoff)
        if feasible>=1:
            jump=p.research_eta*max(1.,p.delegation_multiplier)*p.project_size**p.effort_elasticity*max_shape(feasible)
            upper=max(upper,rounded(feasible+jump,p.capability_step))
    controlled=rounded(upper,p.capability_step)
    upper=rounded(controlled,p.ai_step)
    for _ in range(p.horizon):
        jump=p.research_eta*p.resource_total**p.effort_elasticity*max_shape(upper)
        upper=rounded(upper+jump,p.ai_step)
    return controlled,rounded(upper,p.ai_step)
