"""Scenario analysis with empirically anchored bridges separated from assumptions."""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import Params,solve_verified_domain as solve,policy_game,autonomous

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'


def compact(r):
    return {k:r[k] for k in ['V1','V2','W1','W2','welfare','doom','escape','doom_given_escape',
                             'research_cycles','delegated_cycles','boundary_probability','diagnostics',
                             'grid_expansions','capability_ceiling','ai_ceiling']}


def run():
    p=Params.load()
    empirical=json.loads((OUT/'empirical.json').read_text())
    bridge=replace(p,research_eta=empirical['calibration']['eta_matching_one_year_frontier'],
                   cost_exponent=empirical['calibration']['cost_exponent_log_capability'])
    base=policy_game(p)
    results={'reference':base,'empirical_bridge':policy_game(bridge),'sensitivity':{}}
    cases={
        '5 years':replace(p,horizon=5), '25 years':replace(p,horizon=25),
        '25 years, no acquisition':replace(p,horizon=25,resource_enabled=False),
        '25 years, full common loss shock':replace(p,horizon=25,loss_correlation=1),
        '25 years, high-risk pure selection':replace(p,horizon=25,selection='high_risk'),
        '25 years, half capability mesh':replace(p,horizon=25,capability_step=.25,ai_step=.125),
        '25 years, double capability ceiling':replace(p,horizon=25,capability_max=28,ai_max=200),
        '25 years, zero terminal values':replace(p,horizon=25,terminal_years=0,terminal_ai=0),
        '25 years, long terminal values':replace(p,horizon=25,terminal_years=20,terminal_ai=5),
        '25 years, no containment':replace(p,horizon=25,containment=0),
        '25 years, no positional prize':replace(p,horizon=25,prize=0),
        '25 years, low research feedback':replace(p,horizon=25,research_feedback=.3),
        '25 years, high research feedback':replace(p,horizon=25,research_feedback=1.4),
        'bridge, half cost slope':replace(bridge,cost_exponent=bridge.cost_exponent/2),
        'bridge, double finance':replace(bridge,external_finance=2*p.external_finance),
        'bridge, ready to delegate':replace(bridge,launch_capability=1),
        'bridge, higher market scale':replace(bridge,commercial_scale=4),
    }
    for name,pp in cases.items():
        r=solve(pp)
        results['sensitivity'][name]=compact(r)
        print(name,round(r['doom'],6),round(r['escape'],6),'boundary',r['boundary_probability'],flush=True)
    long=replace(p,horizon=25)
    results['long_policy']=policy_game(long)
    # First-loss continuation evaluated at a fixed launch state: no commercial parameter enters.
    continuation=[]
    for horizon in [5,10,25]:
        for containment in [0,.01,.08,.2]:
            pp=replace(p,horizon=horizon,containment=containment)
            r=autonomous(pp);idx=np.argmin(abs(r['grid']-3))
            continuation.append({'years':horizon,'containment':containment,'capability':3,
                                 'doom':float(r['doom'][horizon,idx,p.resource_initial]),
                                 'seizures':float(r['seized'][horizon,idx,p.resource_initial])})
    results['autonomous_continuation']=continuation
    rows=[]
    for sigma in [-1.,0.,.5,1.,1.3,2.,3.]:
        for q in [0.,.01,.03,.1,.3,.6]:
            rr=solve(replace(long,sigma=sigma,q0=q))
            regime=('stopping' if rr['research_cycles']<1e-8 else 'controlled innovation' if rr['delegated_cycles']<1e-8
                    else 'exposure without extinction by T' if rr['doom']<1e-8 else 'positive extinction probability')
            rows.append({'sigma':sigma,'q0':q,'doom':rr['doom'],'escape':rr['escape'],
                         'research_cycles':rr['research_cycles'],'delegated_cycles':rr['delegated_cycles'],
                         'welfare':rr['welfare'],'boundary':rr['boundary_probability'],'regime':regime})
        print('curvature sweep',sigma,flush=True)
    pd.DataFrame(rows).to_csv(OUT/'tables/risk_regions.csv',index=False)
    results['sweep_max_boundary']=max(r['boundary'] for r in rows)
    # Exact PD example, with benefits paid only upon human survival.
    B,q,v,c=10.,.1,1.5,.1
    results['prisoners_dilemma']={'baseline':B,'q':q,'benefit':v,'cost':c,
        'both_pause':B,'launch_against_pause':(1-q)*(B+v)-c,
        'pause_against_launch':(1-q)*B,'both_launch':(1-q)**2*(B+v)-c,'doom_both_launch':1-(1-q)**2}
    (OUT/'model_results.json').write_text(json.dumps(results,indent=2)+'\n')
    policy_rows=[]
    for label,key in [('10 years','reference'),('25 years','long_policy'),('Empirical bridges','empirical_bridge')]:
        for pol,r in results[key]['cases'].items():
            policy_rows.append({'specification':label,'policy':pol,**{k:r[k] for k in ['welfare','doom','escape','research_cycles','delegated_cycles','boundary_probability']}})
    pd.DataFrame(policy_rows).to_csv(OUT/'tables/policies.csv',index=False)
    pd.DataFrame([{'specification':name,**{k:v for k,v in r.items() if k!='diagnostics'}} for name,r in results['sensitivity'].items()]).to_csv(OUT/'tables/sensitivity.csv',index=False)
    plt.rcParams.update({'font.family':'serif','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,ax=plt.subplots(1,2,figsize=(9,3.2))
    frame=pd.DataFrame(rows)
    for q in [.01,.03,.1,.3]:
        d=frame[frame.q0==q];ax[0].plot(d.sigma,100*d.doom,'o-',label=f'q = {q:g}')
    ax[0].set(xlabel='Commercial curvature, sigma',ylabel='Extinction probability by year 25 (%)',title='A. Selected development equilibria')
    ax[0].legend(frameon=False,fontsize=8)
    for containment in [0,.01,.08,.2]:
        d=pd.DataFrame(continuation);d=d[d.containment==containment]
        ax[1].plot(d.years,100*d.doom,'o-',label=f'Containment = {containment:g}')
    ax[1].set(xlabel='Years of autonomous continuation',ylabel='Conditional extinction probability (%)',title='B. Fixed autonomous state: a = 3, k = 1')
    ax[1].legend(frameon=False,fontsize=8)
    fig.tight_layout();fig.savefig(OUT/'figures/scenarios.pdf');fig.savefig(OUT/'figures/scenarios.png',dpi=180);plt.close(fig)
    print('Scenario results saved.',flush=True)
    return results


if __name__=='__main__':run()
