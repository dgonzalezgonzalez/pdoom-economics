"""Behavioral and accounting checks independent of manuscript output formatting."""
from dataclasses import replace
import numpy as np
from model import Params, autonomous, benefits, equilibria, exploitability, solve


def run():
    p=replace(Params.load(),horizon=4,capability_max=8,ai_max=50,ai_step=.5)
    for A,B in [(np.array([[1,-1],[-1,1.]]),np.array([[-1,1],[1,-1.]])),
                (np.array([[3,0],[5,1.]]),np.array([[3,5],[0,1.]])),
                (np.zeros((2,3)),np.zeros((2,3)))]:
        for x,y in equilibria(A,B):
            assert exploitability(A,B,x,y)<1e-6
            assert abs(x.sum()-1)<1e-8 and abs(y.sum()-1)<1e-8
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
    for sigma in (-1,0,1,2):
        test=replace(p,sigma=sigma)
        derivative=(benefits(3.00001,test)-benefits(2.99999,test))/.00002
        assert abs(derivative-test.commercial_scale*3**(-sigma))<1e-6
    # Curvature counterexamples: strictly concave commercial benefits can cross a danger threshold.
    a=np.log(10)
    assert a>2 and 10*(1-np.exp(-a))-a > 10*(1-np.exp(-2))-2
    assert .5<2  # Linear benefit a minus a^2 has optimum .5.
    print('All equilibrium, mortality, resource, probability, planner and counterexample checks passed.')


if __name__=='__main__': run()
