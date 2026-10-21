"""Finite-horizon public-state game. Arrays implement the paper's Bellman equations."""
from dataclasses import dataclass, replace
from itertools import combinations
import json
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
    cost_exponent: float = .8
    safety_cost: float = .15
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
    return values[low]*(1-weight)+values[high]*weight


def supports(n):
    return [s for k in range(1, n+1) for s in combinations(range(n), k)]


def equilibria(A, B, tol=1e-8, fast=False):
    """One representative per feasible support; LP also handles unequal supports."""
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


def autonomous(p):
    """Optimal AI policy plus human life-value and finite-horizon extinction probability."""
    grid = np.arange(1, p.ai_max+p.ai_step/2, p.ai_step)
    K = p.resource_total
    H = p.horizon
    value = np.zeros((H+1, len(grid), K+1))
    life = np.zeros_like(value)
    doom = np.zeros_like(value)
    seized = np.zeros_like(value)
    boundary = np.zeros_like(value)
    initial_human = K-p.resource_initial
    safe = lambda h: (1-p.beta**h)/(1-p.beta)+p.beta**h*p.terminal_years
    for k in range(p.resource_initial, K+1):
        alive = K-k >= p.human_subsistence
        value[0,:,k] = p.terminal_ai*grid
        life[0,:,k] = p.terminal_years*((K-k)/initial_human)**p.human_resource_elasticity if alive else 0
        doom[0,:,k] = float(not alive)
    for h in range(1, H+1):
        for k in range(p.resource_initial, K+1):
            alive = K-k >= p.human_subsistence
            candidates = []
            for y in (0,1):
                if y and (not p.resource_enabled or k == K): continue
                for e in (0., k/2, float(k)):
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
                    candidates.append((w,l,d,z,b))
            stacked = np.stack(candidates)
            best = np.argmax(stacked[:,0,:],axis=0)
            selected = stacked[best,:,np.arange(len(grid))]
            value[h,:,k],life[h,:,k],doom[h,:,k],seized[h,:,k],boundary[h,:,k] = selected.T
    return {"grid":grid,"value":value,"life":life,"doom":doom,"seized":seized,"boundary":boundary}


def solve(p, policies=("open","open"), planner=False, rogue=None):
    """Backward induction; select lowest/highest-risk pure NE, otherwise a verified mixed NE.

    Mixed equilibria coexisting with pure ones are not enumerated. Selection sensitivity is
    an equilibrium comparison, never a bound on the entire equilibrium correspondence.
    """
    assert 0 < p.beta < 1 and 0 < p.capture_share <= 1 and 0 <= p.q0 <= 1
    assert policies[0] in POLICIES and policies[1] in POLICIES
    rogue = autonomous(p) if rogue is None else rogue
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
    prev = np.stack([p.terminal_years*x for x in private+welfare]+[np.zeros((n,n))]*5)
    maps,costs,allowed,qs=[],[],[],[]
    root_policies = None
    for i,policy in enumerate(policies):
        mm,cc,aa,qq=[],[],[],[]
        for action in range(na):
            e = float(action != 0)
            s = float(action == 3)
            delegated = action >= 2
            target = grid+gain(grid,e,p,delegated)
            cost = p.research_cost*grid**p.cost_exponent*e+p.safety_cost*s
            feasible = (cost <= R+p.external_finance+1e-10) & (e+s*p.seizure_cost <= p.infrastructure[i]+1e-10)
            if delegated:
                feasible &= grid >= p.launch_capability
                if policy == "ban" or (policy == "standard" and action == 2): feasible[:] = False
            if action == 0: feasible[:]=True
            mm.append(interpolation(grid,target)); cc.append(cost); aa.append(feasible)
            qq.append(p.q0*np.exp(-p.safety_effect*s) if delegated else 0.)
        maps.append(mm);costs.append(cc);allowed.append(aa);qs.append(qq)
    stats = {"multiple_pure_state_games":0,"mixed_state_games":0,"max_deviation_gain":0.,"state_games":0}
    initial_actions=[]
    for h in range(1,p.horizon+1):
        Q = np.zeros((9,n,n,na,na))
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
                r1map=interpolation(rogue["grid"],grid+gain(grid,float(u!=0),p,u>=2))
                r2map=interpolation(rogue["grid"],grid+gain(grid,float(v!=0),p,v>=2))
                mix_life=f1*interp(rogue["life"][h-1,:,p.resource_initial],r1map)[:,None]+f2*interp(rogue["life"][h-1,:,p.resource_initial],r2map)[None,:]
                mix_doom=f1*interp(rogue["doom"][h-1,:,p.resource_initial],r1map)[:,None]+f2*interp(rogue["doom"][h-1,:,p.resource_initial],r2map)[None,:]
                rtarget1=grid+gain(grid,float(u!=0),p,u>=2)
                rtarget2=grid+gain(grid,float(v!=0),p,v>=2)
                mix_boundary=(f1*np.maximum(rtarget1>rogue['grid'][-1]+1e-9,interp(rogue["boundary"][h-1,:,p.resource_initial],r1map))[:,None]
                              +f2*np.maximum(rtarget2>rogue['grid'][-1]+1e-9,interp(rogue["boundary"][h-1,:,p.resource_initial],r2map))[None,:])
                for j in range(2):
                    c=costs[j][u if j==0 else v]
                    c=c[:,None] if j==0 else c[None,:]
                    Q[j,:,:,u,v]=private[j]-c+p.beta*(none*expected[j]+p.private_life*mix_life)
                    Q[j+2,:,:,u,v]=welfare[j]-c+p.beta*(none*expected[j+2]+p.social_life/2*mix_life)
                Q[4,:,:,u,v]=none*expected[4]+mix_doom
                Q[5,:,:,u,v]=none*expected[5]+f1+f2
                target1=grid+gain(grid,float(u!=0),p,u>=2)
                target2=grid+gain(grid,float(v!=0),p,v>=2)
                hit=(target1[:,None]>grid[-1]+1e-9)|(target2[None,:]>grid[-1]+1e-9)
                Q[6,:,:,u,v]=none*np.maximum(expected[6],hit)+mix_boundary
                Q[7,:,:,u,v]=int(u!=0)+int(v!=0)+none*expected[7]
                Q[8,:,:,u,v]=int(u>=2)+int(v>=2)+none*expected[8]
        mask=np.array(allowed[0]).T[:,None,:,None]&np.array(allowed[1]).T[None,:,None,:]
        A=np.where(mask,Q[0],-1e12);B=np.where(mask,Q[1],-1e12)
        current=np.zeros((9,n,n)); joints=np.zeros((n,n,na,na))
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


def solve_verified_domain(p,policies=("open","open"),planner=False,rogue=None):
    """Expand computational ceilings until clipping is negligible at the initial state."""
    for attempt in range(5):
        r=solve(p,policies,planner,rogue)
        if r['boundary_probability']<1e-9:
            r.update(grid_expansions=attempt,capability_ceiling=p.capability_max,ai_ceiling=p.ai_max)
            return r
        p=replace(p,capability_max=2*p.capability_max,ai_max=2*p.ai_max)
        rogue=None
    raise ArithmeticError('Could not remove economically relevant capability clipping')
