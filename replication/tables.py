"""Write manuscript tables directly from verified machine-readable results."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'


def escape(s):
    return str(s).replace('&',r'\&').replace('_',r'\_').replace('%',r'\%')


def table(path,header,rows,alignment):
    text=[r'\begin{tabular}{'+alignment+'}',r'\toprule', ' & '.join(header)+r' \\',r'\midrule']
    text+=[' & '.join(str(v) for v in row)+r' \\' for row in rows]
    text += [r'\bottomrule',r'\end{tabular}']
    (OUT/'tables'/path).write_text('\n'.join(text)+'\n')


def run():
    empirical=json.loads((OUT/'empirical.json').read_text())
    model=json.loads((OUT/'model_results.json').read_text())
    p=json.loads((ROOT/'replication/parameters.json').read_text())
    labels={'eci_linear':'Linear ECI','eci_quadratic':'Quadratic ECI','ties_half':'Ties weighted one-half',
            'qualified_aliases':'Qualified aliases','gpqa_common':'GPQA, common sample','eci_gpqa_common':'ECI, common sample',
            'code':'Coding prompts','non_code':'Other prompts','english':'English prompts'}
    rows=[]
    for key in labels:
        r=empirical['preference'][key]
        quadratic=f"{r['coef'][2]:.3f} ({r['se'][2]:.3f})" if r['quadratic'] else '--'
        rows.append([labels[key],f"{r['n']:,}",str(r['models']),f"{r['coef'][1]:.3f} ({r['se'][1]:.3f})",quadratic])
    table('preferences.tex',['Specification','$N$','Models',r'$\widehat\beta_1$ (s.e.)',r'$\widehat\beta_2$ (s.e.)'],rows,'lrrrr')
    rows=[]
    for key,label in [('reference','10 years'),('long_policy','25 years'),('empirical_bridge','Data bridges, 10 years')]:
        for policy in ['open/open','standard/open','standard/standard','ban/ban']:
            r=model[key]['cases'][policy]
            rows.append([label,policy,f"{100*r['escape']:.3f}",f"{100*r['doom']:.3f}",f"{r['welfare']:.3f}"])
        r=model[key]['planner']
        rows.append([label,'Planner',f"{100*r['escape']:.3f}",f"{100*r['doom']:.3f}",f"{r['welfare']:.3f}"])
    table('policies.tex',['Specification','Policy',r'Loss of control (\%)',r'Extinction (\%)','Welfare'],rows,'llrrr')
    rows=[]
    for first in ['open','ban']:
        cells=[]
        for second in ['open','ban']:
            r=model['long_policy']['cases'][first+'/'+second]
            cells.append(f"({r['W1']:.3f}, {r['W2']:.3f})")
        rows.append([first.capitalize()]+cells)
    table('government_game.tex',['Jurisdiction 1 / 2','Open','Ban'],rows,'lrr')
    rows=[]
    for name,r in model['sensitivity'].items():
        rows.append([escape(name),f"{100*r['escape']:.3f}",f"{100*r['doom']:.3f}",f"{100*r['boundary_probability']:.4f}"])
    table('sensitivity.tex',['Specification',r'Loss of control (\%)',r'Extinction (\%)',r'Boundary (\%)'],rows,'lrrr')
    rows=[]
    for key in ['beta','beta_ai','sigma','commercial_scale','prize','research_cost','cost_exponent',
                'research_eta','delegation_multiplier','research_feedback','research_difficulty','q0','safety_effect',
                'containment','terminal_years']:
        rows.append([r'\texttt{'+escape(key)+'}',str(p[key]),'Scenario assumption'])
    table('parameters.tex',['Replication parameter','Reference value','Status'],rows,'lrl')
    r=empirical['preference']['eci_quadratic'];c=empirical['cost'];cal=empirical['calibration']
    rows=[
        [r'Preference $\beta_1,\beta_2$',f"{r['coef'][1]:.3f}, {r['coef'][2]:.3f}",'Estimated, conditional on matching and scores'],
        ['Log-cost slope per ten ECI',f"{c['log_cost_per_10_eci']:.3f}",'Estimated cost-level association'],
        ['Annual retrospective frontier change',f"{cal['eci_points_per_year']:.2f}",'Observed snapshot difference, ECI points'],
        [r'Bridge $\gamma,\eta$',f"{c['log_cost_per_10_eci']:.3f}, {cal['eta_matching_one_year_frontier']:.3f}",'Imposed technology mapping of estimates'],
        [r'Initial $a$, project input, $\bar K$','1, 1, 6','Normalizations; project-size sensitivity'],
        [r'$\phi,\psi,\mu_D$','0.9, 0.5, 2.5','Literature-motivated scenario assumptions'],
        [r'$q_0,\rho_0,\underline H$','0.03, 0.08, 2','Unidentified technical and resource assumptions'],
        [r'$m,\ell_i,L,\chi$','1, 5, 40, 0.5','Unidentified commercial and welfare assumptions'],
    ]
    table('identification.tex',['Quantity','Value','Evidential status'],rows,r'p{.29\textwidth}p{.17\textwidth}p{.44\textwidth}')
    r=empirical['preference']['eci_quadratic']
    table('inference.tex',['Coefficient','Pair-cluster s.e.','Dyadic s.e.'],
          [[label,f"{r['se'][i]:.5f}",f"{r['se_dyadic'][i]:.5f}"] for i,label in [(1,'Linear ECI'),(2,'Quadratic ECI')]],'lrr')
    rows=[]
    for name,entry in model['certificates'].items():
        for scope,key in [('Full grid','binding'),('Action-reachable','action_reachable_binding')]:
            b=entry[key]
            rows.append([escape(name),scope,f"{b['max_delegated_deviation']:.3f}" if b else 'Empty',
                         f"({b['a1']:g}, {b['a2']:g})" if b else '--',str(b['remaining_years']) if b else '--'])
    table('certificates.tex',['Specification','Scope',r'$\Delta_{\max}$',r'$(a_1,a_2)$','Years left'],rows,'llrrr')
    rows=[]
    for name,r in [('Open/open',model['long_policy']['cases']['open/open']),('Ban/ban',model['long_policy']['cases']['ban/ban']),
                   ('Open, recovery',model['sensitivity']['25 years, post-containment recovery'])]:
        w=r['welfare_components']
        rows.append([name]+[f"{w[k]:.3f}" for k in ['baseline_no_loss','task_surplus','research_safety_cost','mortality_loss','nonfatal_resource_loss']]+[f"{r['welfare']:.3f}"])
    table('welfare_components.tex',['Policy','Baseline','Task surplus','Cost','Mortality loss','Resource loss','Welfare'],rows,'lrrrrrr')
    fixed=model['fixed_long_horizon']['fixed_policy_cumulative_risk']
    table('fixed_horizon_risk.tex',['Year',r'First loss (\%)',r'Extinction (\%)'],
          [[str(r['year']),f"{100*r['escape']:.4f}",f"{100*r['doom']:.4f}"] for r in fixed if r['year'] in [5,10,25]],'rrr')
    rows=[]
    for name,r in empirical['preference'].items():
        if name.startswith('exclude_'):
            rows.append([escape(name[8:]),f"{r['n']:,}",f"{r['coef'][2]:.3f}",f"{r['se'][2]:.3f}"])
    table('leave_family.tex',['Excluded family','$N$',r'$\widehat\beta_2$','s.e.'],rows,'lrrr')
    r=empirical['preference']['eci_quadratic'];c=empirical['cost'];cal=empirical['calibration']
    macros={'PrefN':f"{r['n']:,}",'PrefModels':str(r['models']),'PrefPairs':str(r['clusters']),
            'PrefLinear':f"{r['coef'][1]:.3f}",'PrefQuad':f"{r['coef'][2]:.3f}",
            'PrefQuadSE':f"{r['se'][2]:.3f}",'CostN':str(c['n']),'CostSlope':f"{c['log_cost_per_10_eci']:.3f}",
            'CostSE':f"{c['se_hc1']:.3f}",'FrontierDrift':f"{cal['eci_points_per_year']:.2f}",
            'BridgeEta':f"{cal['eta_matching_one_year_frontier']:.3f}",
            'LongDoom':f"{100*model['long_policy']['cases']['open/open']['doom']:.2f}",
            'LongEscape':f"{100*model['long_policy']['cases']['open/open']['escape']:.2f}"}
    (ROOT/'paper/generated.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in macros.items())+'\n')


if __name__=='__main__':run()
