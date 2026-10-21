"""Behavioral and accounting checks independent of manuscript output formatting."""
from dataclasses import replace
import numpy as np
from model import Params, autonomous, benefits, equilibria, exploitability, solve,solve_verified_domain,reachable_bounds


def run():
    p=replace(Params.load(),horizon=4,capability_max=8,ai_max=50,ai_step=.5)
    for A,B in [(np.array([[1,-1],[-1,1.]]),np.array([[-1,1],[1,-1.]])),
                (np.array([[3,0],[5,1.]]),np.array([[3,5],[0,1.]])),
                (np.zeros((2,3)),np.zeros((2,3)))]:
        for x,y in equilibria(A,B):
            assert exploitability(A,B,x,y)<1e-6
            assert abs(x.sum()-1)<1e-8 and abs(y.sum()-1)<1e-8
    A=np.array([[1,0,-1],[-1,-5,2],[-2,-5,3.]])
    B=np.array([[-3,0,3],[2,-3,1],[2,1,-2.]])
    risk=np.ones((3,3));risk[2,0]=0
    assert min(x@risk@y for x,y in equilibria(A,B,fast=True))>.99
    assert min(x@risk@y for x,y in equilibria(A,B))<.8
    safe=solve(replace(p,q0=0))
    assert safe['doom']==0 and safe['escape']==0
    banned=solve(p,('ban','ban'))
    assert banned['doom']==0 and banned['escape']==0
    bounded=solve(replace(p,resource_enabled=False))
    assert bounded['doom']==0  # Initial resources exceed human subsistence.
    uncontrolled=autonomous(p)
    dead=p.resource_total-p.human_subsistence+1
    assert np.all(uncontrolled['doom'][:,:,dead:]==1)
    assert np.all(uncontrolled['life'][:,:,dead:]==0)
    assert np.all(uncontrolled['doom']>=0) and np.all(uncontrolled['doom']<=1+1e-10)
    outcome=solve(p)
    assert outcome['doom'] <= outcome['escape']+1e-8
    planner=solve(p,planner=True)
    assert planner['welfare']>=outcome['welfare']-1e-7
    tracked=solve(p,track_cdf=True)
    assert abs(tracked['doom']-outcome['doom'])<1e-10 and abs(tracked['escape']-outcome['escape'])<1e-10
    certificate=solve_verified_domain(p,certificate=True)['no_delegation_certificate']
    assert not certificate['passes'] and certificate['binding']['max_delegated_deviation']>0
    assert solve_verified_domain(p,('ban','ban'),certificate=True)['no_delegation_certificate']['empty_feasible_delegated_set']
    assert Params.load().safety_resource==replace(Params.load(),seizure_cost=3).safety_resource
    for sigma in (-1,0,1,2):
        test=replace(p,sigma=sigma)
        derivative=(benefits(3.00001,test)-benefits(2.99999,test))/.00002
        assert abs(derivative-test.commercial_scale*3**(-sigma))<1e-6
    # Curvature counterexamples: strictly concave commercial benefits can cross a danger threshold.
    a=np.log(10)
    assert a>2 and 10*(1-np.exp(-a))-a > 10*(1-np.exp(-2))-2
    assert .5<2  # Linear benefit a minus a^2 has optimum .5.
    # A selected-path clipping test can falsely certify stopping by deterring a deviation.
    tiny=replace(p,horizon=5,capability_max=1.1,capability_step=.1,prize=0,q0=0,
                 research_cost=1,external_finance=2)
    truncated=solve(tiny)
    certified=solve_verified_domain(tiny)
    assert truncated['initial_action_joint'][0][0]==1 and truncated['boundary_probability']==0
    assert certified['initial_action_joint'][0][0]<1 and certified['V1']>truncated['V1']
    referee_case=replace(p,horizon=1,terminal_years=1,prize=0,research_eta=2.1,research_cost=.75,cost_exponent=0,
                         external_finance=1,launch_capability=100,q0=0,capability_max=2,capability_step=.5)
    assert solve(referee_case)['research_cycles']==0
    assert solve_verified_domain(referee_case)['research_cycles']==2
    # Fixed-state autonomous behavior is invariant to a commercial parameter outside its problem.
    aa=autonomous(replace(p,horizon=20,containment=0))
    bb=autonomous(replace(p,horizon=20,containment=0,sigma=3))
    assert np.array_equal(aa['doom'],bb['doom'])
    idx=np.argmin(abs(aa['grid']-3))
    assert aa['doom'][20,idx,p.resource_initial]>.99
    # Recursive stopping benchmark: compare complete discounted flow paths to gain decomposition.
    beta,b,rate,lam,c0,a=.9,2.,.8,1.3,.4,4.
    K=beta*b*(1-lam**(-rate))/(1-beta)
    for xi in [-.2,rate,2.]:
        values=[]
        for N in range(61):
            n=np.arange(N);states=a*lam**n
            direct=np.sum(beta**n*(3-b*states**(-rate)-c0*states**(-xi)))
            direct+=beta**N*(3-b*(a*lam**N)**(-rate))/(1-beta)
            decomposition=np.sum(beta**n*(K*states**(-rate)-c0*states**(-xi)))
            assert abs(direct-(3-b*a**(-rate))/(1-beta)-decomposition)<1e-10
            values.append(direct)
        if xi<rate:
            assert np.argmax(values)<60 and values[-1]<max(values)-1e-5
        elif xi>rate:
            assert np.all(np.diff(values)>0)
    print('All equilibrium, mortality, resource, probability, planner and counterexample checks passed.')


if __name__=='__main__': run()
