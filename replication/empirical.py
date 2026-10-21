"""Descriptive preference and cost estimates. No extinction parameter is estimated."""
from pathlib import Path
import json
import re
import zipfile
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
OUT=ROOT/'output'

# Explicitly reviewed weight/version aliases; no fuzzy join is used.
ECI={
 'claude-3-5-haiku-20241022':'Claude 3.5 Haiku',
 'claude-3-5-sonnet-20241022':'Claude 3.5 Sonnet (October 2024)',
 'claude-3-7-sonnet-20250219':'Claude 3.7 Sonnet',
 'claude-opus-4-20250514':'Claude Opus 4',
 'claude-sonnet-4-20250514':'Claude Sonnet 4',
 'deepseek-r1-0528':'DeepSeek-R1 (May 2025)',
 'deepseek-v3-0324':'DeepSeek-V3 (Mar 2025)',
 'gemini-2.0-flash-001':'Gemini 2.0 Flash (Feb 2025)',
 'gemini-2.0-flash-thinking-exp-01-21':'Gemini 2.0 Flash Thinking (Jan 2025)',
 'gemini-2.5-flash-preview-04-17':'Gemini 2.5 Flash (Apr 2025)',
 'gemini-2.5-pro-preview-03-25':'Gemini 2.5 Pro (Mar 2025)',
 'gemini-2.5-pro-preview-05-06':'Gemini 2.5 Pro (May 2025)',
 'gemma-3-27b-it':'Gemma 3 27B',
 'gpt-4.1-2025-04-14':'GPT-4.1',
 'gpt-4.1-mini-2025-04-14':'GPT-4.1 mini',
 'gpt-4o-2024-11-20':'GPT-4o (Nov 2024)',
 'gpt-4o-mini-2024-07-18':'GPT-4o mini',
 'grok-4-0709':'Grok 4',
 'kimi-k2-0711-preview':'Kimi K2 (Jul 2025)',
 'llama-3.3-70b-instruct':'Llama 3.3 70B',
 'llama-4-maverick-17b-128e-instruct':'Llama 4 Maverick',
 'llama-4-scout-17b-16e-instruct':'Llama 4 Scout',
 'mistral-medium-2505':'Mistral Medium 3',
 'mistral-small-3.1-24b-instruct-2503':'Mistral Small 3.1',
 'o3-2025-04-16':'o3','o3-mini':'o3-mini','o4-mini-2025-04-16':'o4-mini',
 'qwen-max-2025-01-25':'Qwen2.5-Max','qwen3-235b-a22b':'Qwen3-235B-A22B',
 'qwen3-235b-a22b-instruct-2507':'Qwen3-235B-A22B-Instruct (Jul 2025)',
 'qwen3-30b-a3b':'Qwen3-30B-A3B','qwq-32b':'QwQ-32B',
}
QUALIFIED={
 'gemini-2.5-pro':'Gemini 2.5 Pro (Jun 2025)',
 'gemini-2.5-flash':'Gemini 2.5 Flash (Jun 2025)',
 'grok-3-mini-beta':'Grok-3 mini', 'grok-3-mini-high':'Grok-3 mini',
 'grok-3-preview-02-24':'Grok 3',
 'claude-3-7-sonnet-20250219-thinking-32k':'Claude 3.7 Sonnet',
 'claude-opus-4-20250514-thinking-16k':'Claude Opus 4',
 'claude-sonnet-4-20250514-thinking-32k':'Claude Sonnet 4',
 'qwen3-235b-a22b-no-thinking':'Qwen3-235B-A22B',
}
GPQA={
 'claude-3-7-sonnet-20250219-thinking-32k':'claude-3-7-sonnet-20250219_32K',
 'claude-opus-4-20250514-thinking-16k':'claude-opus-4-20250514_16K',
 'claude-sonnet-4-20250514-thinking-32k':'claude-sonnet-4-20250514_32K',
 'deepseek-r1-0528':'DeepSeek-R1-0528','deepseek-v3-0324':'DeepSeek-V3-0324',
 'gemma-3-27b-it':'gemma-3-27b-it','grok-4-0709':'grok-4-0709',
 'llama-4-scout-17b-16e-instruct':'Llama-4-Scout-17B-16E-Instruct',
 'qwen3-235b-a22b':'qwen3-235b-a22b','qwen3-30b-a3b':'Qwen3-30B-A3B',
 'qwq-32b':'QwQ-32B', 'qwen-max-2025-01-25':'qwen-max-2025-01-25',
}
for key in ECI:
    if key.startswith(('claude-','gpt-4.1')): GPQA[key]=key


def family(model):
    if model.startswith(('gpt','chatgpt','o3','o4')): return 'OpenAI'
    if model.startswith('claude'): return 'Anthropic'
    if model.startswith(('gemini','gemma')): return 'Google'
    if model.startswith('deepseek'): return 'DeepSeek'
    if model.startswith(('qwen','qwq')): return 'Qwen'
    return model.split('-')[0]


def fit_logit(d,metric='eci',ties=False,quadratic=True):
    keep=d['winner'].isin(['model_a','model_b','tie'] if ties else ['model_a','model_b'])
    d=d[keep].dropna(subset=[metric+'_a',metric+'_b']).copy()
    center,scale=(140.,10.) if metric=='eci' else (.6,.1)
    za=(d[metric+'_a'].to_numpy()-center)/scale
    zb=(d[metric+'_b'].to_numpy()-center)/scale
    X=np.column_stack([np.ones(len(d)),za-zb,za**2-zb**2]) if quadratic else np.column_stack([np.ones(len(d)),za-zb])
    y=d.winner.map({'model_a':1.,'model_b':0.,'tie':.5}).to_numpy()
    def objective(b):
        z=X@b
        return np.sum(np.logaddexp(0,z)-y*z),X.T@(expit(z)-y)
    result=minimize(objective,np.zeros(X.shape[1]),jac=True,method='BFGS',options={'gtol':1e-6,'maxiter':300})
    score=X.T@(y-expit(X@result.x))
    assert np.max(np.abs(score))/len(d)<1e-7, (result.message,score)
    p=expit(X@result.x)
    bread=np.linalg.pinv((X.T*(p*(1-p)))@X)
    keys=np.array(['|'.join(sorted(pair)) for pair in zip(d.model_a,d.model_b)])
    groups,idx=np.unique(keys,return_inverse=True)
    scores=np.zeros((len(groups),X.shape[1]))
    np.add.at(scores,idx,X*(y-p)[:,None])
    correction=len(groups)/(len(groups)-1)*(len(d)-1)/(len(d)-X.shape[1])
    covariance=correction*bread@(scores.T@scores)@bread
    return {'n':len(d),'models':len(set(d.model_a)|set(d.model_b)),'clusters':len(groups),
            'coef':result.x.tolist(),'se':np.sqrt(np.diag(covariance)).tolist(),
            'covariance':covariance.tolist(),
            'metric':metric,'ties':ties,'quadratic':quadratic,
            'log_likelihood':-float(objective(result.x)[0]),
            'score_per_observation':float(np.max(np.abs(score))/len(d))}


def ols(X,y):
    b=np.linalg.lstsq(X,y,rcond=None)[0]
    residual=y-X@b
    bread=np.linalg.pinv(X.T@X)
    covariance=len(y)/(len(y)-X.shape[1])*bread@((X.T*residual**2)@X)@bread
    return b,np.sqrt(np.diag(covariance))


def run():
    (OUT/'tables').mkdir(parents=True,exist_ok=True)
    (OUT/'figures').mkdir(parents=True,exist_ok=True)
    scores=pd.read_csv(RAW/'eci_scores.csv').set_index('Model')
    assert scores.index.is_unique
    raw=pd.read_parquet(RAW/'arena_numeric.parquet')
    raw['timestamp']=pd.to_datetime(raw.timestamp)
    gpqa=pd.read_csv(zipfile.ZipFile(RAW/'benchmark_data.zip').open('gpqa_diamond.csv'))
    # Exact version duplicate evaluations, if any, are averaged transparently.
    g=gpqa.groupby('Model version').mean_score.mean()
    cross=[]
    for model in sorted(set(raw.model_a)|set(raw.model_b)):
        name=ECI.get(model,QUALIFIED.get(model,''))
        cross.append({'arena_model':model,'epoch_model':name,'family':family(model),
                      'status':'primary' if model in ECI else ('qualified' if model in QUALIFIED else 'unmatched'),
                      'eci':float(scores.loc[name,'eci']) if name else None,
                      'gpqa_version':GPQA.get(model,''),
                      'gpqa':float(g.get(GPQA.get(model,''),np.nan)),
                      'note':'Model-level ECI; evaluation budgets may differ' if model in ECI else 'Version or reasoning ambiguity; excluded from primary ECI sample'})
    cross=pd.DataFrame(cross)
    cross.to_csv(ROOT/'data/model_crosswalk.csv',index=False)
    def merge(qualified=False):
        use=cross if qualified else cross[cross.status=='primary']
        d=raw.copy()
        for side in ('a','b'):
            d=d.merge(use[['arena_model','eci','gpqa','family']].rename(columns={c:c+'_'+side for c in ['eci','gpqa','family']}),
                      left_on='model_'+side,right_on='arena_model',how='left',validate='many_to_one').drop(columns='arena_model')
        return d
    d=merge(); first=d[d.evaluation_order==1]
    results={
        'eci_linear':fit_logit(first,quadratic=False),
        'eci_quadratic':fit_logit(first),
        'ties_half':fit_logit(first,ties=True),
        'english':fit_logit(first[first.language=='en']),
        'code':fit_logit(first[first.is_code]),
        'non_code':fit_logit(first[~first.is_code]),
        'all_rounds':fit_logit(d),
        'qualified_aliases':fit_logit(merge(True).query('evaluation_order==1')),
        'gpqa_common':fit_logit(first.dropna(subset=['eci_a','eci_b','gpqa_a','gpqa_b']),'gpqa'),
        'eci_gpqa_common':fit_logit(first.dropna(subset=['eci_a','eci_b','gpqa_a','gpqa_b'])),
    }
    for f in sorted(set(cross.loc[cross.status=='primary','family'])):
        sub=first[(first.family_a!=f)&(first.family_b!=f)]
        results['exclude_'+f]=fit_logit(sub)
    # Cost data: exact names, exclude post-training derivatives sharing a base training run.
    models=pd.read_csv(RAW/'epoch_models.csv')
    cost=models[['Model','Publication date','Training compute cost (2023 USD)','Training compute (FLOP)']].merge(
        scores[['eci','date','Organization']],left_on='Model',right_index=True,validate='many_to_one')
    cost=cost.dropna(subset=['Training compute cost (2023 USD)'])
    cost=cost[cost['Training compute cost (2023 USD)']>0].copy()
    cost['excluded_shared_training']=cost.Model.str.contains(r'DeepSeek-R1|DeepSeek-V3 \(Mar',regex=True)
    cost.to_csv(ROOT/'data/cost_matches.csv',index=False)
    unique=cost[~cost.excluded_shared_training].copy()
    z=(unique.eci.to_numpy()-140)/10
    b,se=ols(np.column_stack([np.ones(len(z)),z]),np.log(unique['Training compute cost (2023 USD)'].to_numpy()))
    yr=pd.to_datetime(unique['Publication date']).dt.year.to_numpy()-2024
    bt,set_=ols(np.column_stack([np.ones(len(z)),z,yr]),np.log(unique['Training compute cost (2023 USD)'].to_numpy()))
    cost_results={'n':len(unique),'log_cost_per_10_eci':float(b[1]),'se_hc1':float(se[1]),
                  'with_year':float(bt[1]),'with_year_se':float(set_[1]),'median_cost_usd2023':float(unique['Training compute cost (2023 USD)'].median())}
    scores2=scores.reset_index();scores2['date']=pd.to_datetime(scores2.date)
    last=pd.Timestamp('2026-10-21');prior=last-pd.DateOffset(years=1)
    frontier_last=float(scores2.loc[scores2.date<=last,'eci'].max())
    frontier_prior=float(scores2.loc[scores2.date<=prior,'eci'].max())
    drift=frontier_last-frontier_prior
    calibration={'eci_frontier_2026':frontier_last,'eci_frontier_2025':frontier_prior,'eci_points_per_year':drift,
                 'eta_matching_one_year_frontier':float(np.expm1(drift/10)*1.05),
                 'cost_exponent_log_capability':float(b[1]),'capability_mapping':'a = exp((ECI-ECI_reference)/10)',
                 'warning':'Descriptive cross-sectional bridges, not causal or future technology estimates.'}
    output={'sample':{'raw':len(raw),'first_round':int((raw.evaluation_order==1).sum()),
                      'raw_models':len(cross),'primary_matched_models':int((cross.status=='primary').sum()),
                      'first_date':str(raw.timestamp.min()),'last_date':str(raw.timestamp.max())},
            'preference':results,'cost':cost_results,'calibration':calibration}
    (OUT/'empirical.json').write_text(json.dumps(output,indent=2)+'\n')
    rows=[]
    for name,r in results.items():
        rows.append({'specification':name,'observations':r['n'],'models':r['models'],'pairs':r['clusters'],
                     'linear':r['coef'][1],'linear_se':r['se'][1],
                     'quadratic':r['coef'][2] if r['quadratic'] else np.nan,
                     'quadratic_se':r['se'][2] if r['quadratic'] else np.nan})
    pd.DataFrame(rows).to_csv(OUT/'tables/preference_estimates.csv',index=False)
    plt.rcParams.update({'font.family':'serif','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'savefig.bbox':'tight','pdf.fonttype':42})
    fig,ax=plt.subplots(1,2,figsize=(9,3.1))
    matched_scores=cross.loc[cross.status=='primary','eci']
    x=np.linspace(matched_scores.min(),matched_scores.max()-10,100);zz=(x-140)/10
    for name,label in [('eci_linear','Linear latent utility'),('eci_quadratic','Quadratic latent utility')]:
        r=results[name];bb=r['coef']; delta=np.full_like(zz,bb[1])+(bb[2]*(2*zz+1) if r['quadratic'] else 0)
        ax[0].plot(x,100*(expit(delta)-.5),label=label)
        if r['quadratic']:
            contrasts=np.column_stack([np.zeros_like(zz),np.ones_like(zz),2*zz+1])
            standard=np.sqrt(np.einsum('ij,jk,ik->i',contrasts,np.array(r['covariance']),contrasts))
            ax[0].fill_between(x,100*(expit(delta-1.96*standard)-.5),100*(expit(delta+1.96*standard)-.5),alpha=.14,color='#ff7f0e')
    ax[0].set(xlabel='Starting ECI',ylabel='Preference advantage of +10 ECI (pp)',title='A. Decisive, first-round preferences')
    ax[0].legend(frameon=False,fontsize=8)
    ax[1].scatter(unique.eci,unique['Training compute cost (2023 USD)']/1e6,s=22,color='#315d7e')
    xx=np.linspace(unique.eci.min(),unique.eci.max(),100)
    ax[1].plot(xx,np.exp(b[0]+b[1]*(xx-140)/10)/1e6,color='#ad592a')
    ax[1].set(yscale='log',xlabel='ECI',ylabel='Training compute cost (2023 USD million)',title='B. Distinct training runs, exact matches')
    fig.tight_layout();fig.savefig(OUT/'figures/evidence.pdf');fig.savefig(OUT/'figures/evidence.png',dpi=180);plt.close(fig)
    print(json.dumps({'sample':output['sample'],'primary':results['eci_quadratic'],'cost':cost_results,'calibration':calibration},indent=2))
    return output


if __name__=='__main__':run()
