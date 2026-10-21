"""Freeze a narrow, public-data-only Oracle bundle; never calls an AI model."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    results=json.loads((ROOT/'output/model_results.json').read_text())
    context={'reviewed_commit':commit,'repository':'https://github.com/dgonzalezgonzalez/pdoom-economics',
             'selection':'Lowest-risk pure equilibrium if one exists, otherwise verified mixed representative; not exhaustive equilibrium bounds.',
             'cases':{},'sensitivity':results['sensitivity'],'prisoners_dilemma':results['prisoners_dilemma'],
             'autonomous_continuation':results['autonomous_continuation'],'sweep_max_boundary':results['sweep_max_boundary']}
    for key in ['reference','long_policy','empirical_bridge']:
        context['cases'][key]={'cases':results[key]['cases'],'coordinated':results[key]['coordinated'],
                               'planner':results[key]['planner'],'government_equilibria':results[key]['government_equilibria']}
    (ROOT/'review/context.json').write_text(json.dumps(context,indent=2)+'\n')
    files=['paper/main.tex','paper/theory.tex','paper/evidence.tex','paper/proofs.tex','paper/appendices.tex',
           'paper/generated.tex','paper/references.bib','replication/model.py','replication/parameters.json',
           'replication/empirical.py','replication/experiments.py','replication/checks.py','replication/run.py',
           'output/empirical.json','output/validation.json','output/tables/risk_regions.csv','review/context.json',
           'data/model_crosswalk.csv','data/cost_matches.csv','data/README.md','README.md','requirements.txt']
    public_files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    with zipfile.ZipFile(ROOT/'review/repository-snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for file in filter(None,public_files):
            z.write(ROOT/file,file)
    args=['--prompt',(ROOT/'review/request.md').read_text(encoding='utf-8')]
    for file in files:args+=['--file',file]
    oracle=Path(os.environ['ORACLE_CLI'])
    node=os.environ.get('ORACLE_NODE','node')
    preview=subprocess.run([node,str(oracle),'--dry-run','summary','--files-report',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (ROOT/'review/bundle_scope.txt').write_text(preview.stdout+'\n'+preview.stderr,encoding='utf-8')
    if preview.returncode:raise RuntimeError('Oracle preview failed; inspect bundle_scope.txt')
    # Exact paths above contain only the public working paper, code, and numeric aggregates.
    rendered=subprocess.run([node,str(oracle),'--render','--render-plain','--copy',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if rendered.returncode:raise RuntimeError('Oracle render failed: '+rendered.stderr[:500])
    (ROOT/'review/bundle.txt').write_text(rendered.stdout,encoding='utf-8')
    manifest={'reviewed_commit':commit,'files':files,'oracle_version':'0.9.0',
              'bundle_sha256':hashlib.sha256((ROOT/'review/bundle.txt').read_bytes()).hexdigest(),
              'snapshot_sha256':hashlib.sha256((ROOT/'review/repository-snapshot.zip').read_bytes()).hexdigest(),
              'submission_count':0,'model_request':'Pro, power 5 of 5, observed in prepared browser tab'}
    (ROOT/'review/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Prepared review of',commit,'with',len(files),'explicit text files; no model request submitted.')


if __name__=='__main__':main()
