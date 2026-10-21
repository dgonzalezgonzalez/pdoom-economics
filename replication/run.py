"""One-command, offline replication of the frozen working paper."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def verify_data():
    manifest=json.loads((ROOT/'data/data_manifest.json').read_text())
    records=[]
    for name,entry in manifest.items():
        if 'sha256' not in entry:
            raise ValueError(f'Missing frozen source: {name}')
        path=ROOT/Path(entry['path'].replace('\\','/'))
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==entry['sha256'],f'Frozen source changed: {name}'
        records.append({'source':name,'sha256':digest,'bytes':path.stat().st_size})
    return records


def compile_pdf():
    executable=shutil.which('pdflatex')
    if not executable:
        raise RuntimeError('pdflatex is required (MiKTeX or TeX Live).')
    commands=[[executable,'-interaction=nonstopmode','-halt-on-error','main.tex'],
              [shutil.which('bibtex') or 'bibtex','main'],
              [executable,'-interaction=nonstopmode','-halt-on-error','main.tex'],
              [executable,'-interaction=nonstopmode','-halt-on-error','main.tex']]
    build_log=[]
    for command in commands:
        result=subprocess.run(command,cwd=ROOT/'paper',capture_output=True,text=True,encoding='utf-8',errors='replace')
        build_log.append(result.stdout+'\n'+result.stderr)
        if result.returncode:
            (ROOT/'output/latex_build.log').write_text('\n'.join(build_log),encoding='utf-8')
            raise RuntimeError(f'LaTeX command failed: {command[0]}; see output/latex_build.log')
    log=(ROOT/'paper/main.log').read_text(encoding='utf-8',errors='replace')
    for bad in ['There were undefined references','There were undefined citations','Rerun to get cross-references right']:
        assert bad not in log,bad
    (ROOT/'output/pdf').mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'paper/main.pdf',ROOT/'output/pdf/paper.pdf')
    (ROOT/'output/latex_build.log').write_text('\n'.join(build_log),encoding='utf-8')
    import pymupdf
    qa=ROOT/'output/qa';qa.mkdir(exist_ok=True)
    doc=pymupdf.open(ROOT/'output/pdf/paper.pdf')
    pages=[]
    for i,page in enumerate(doc):
        page.get_pixmap(matrix=pymupdf.Matrix(1.15,1.15)).save(qa/f'page-{i+1:02}.png')
        pages.append({'page':i+1,'characters':len(page.get_text()),'width':page.rect.width,'height':page.rect.height})
    # Compact contact sheets are used only for visual review; page renders preserve detail.
    from PIL import Image,ImageOps,ImageDraw
    for start in range(0,len(doc),12):
        sheet=Image.new('RGB',(4*255,3*350),'#cccccc')
        draw=ImageDraw.Draw(sheet)
        for offset in range(min(12,len(doc)-start)):
            im=Image.open(qa/f'page-{start+offset+1:02}.png');im.thumbnail((245,325))
            x=(offset%4)*255+5;y=(offset//4)*350+20
            sheet.paste(im,(x,y));draw.text((x,y-16),str(start+offset+1),fill='black')
        sheet.save(qa/f'contact-{start//12+1}.png')
    return {'pages':len(doc),'page_details':pages,'overfull_boxes':log.count('Overfull \\hbox')}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-pdf',action='store_true')
    parser.add_argument('--paper-only',action='store_true');args=parser.parse_args()
    (ROOT/'output').mkdir(exist_ok=True)
    start=time.time()
    record={'data':verify_data(),'environment':{}}
    for package in ['numpy','scipy','pandas','matplotlib','pyarrow','PyMuPDF']:
        record['environment'][package]=importlib.metadata.version(package)
    if not args.paper_only:
        import checks,empirical,experiments,tables
        checks.run();empirical.run();experiments.run();tables.run()
        results=json.loads((ROOT/'output/model_results.json').read_text())
        for key in ['reference','long_policy','empirical_bridge']:
            for result in list(results[key]['cases'].values())+[results[key]['planner']]:
                assert result['doom'] <= result['escape']+1e-8
                assert result['boundary_probability']<1e-9
                assert result['diagnostics']['max_deviation_gain']<1e-6
        assert results['sweep_max_boundary']<1e-9
        record['model_checks']='passed'
    if not args.no_pdf:record['pdf']=compile_pdf()
    record['seconds']=round(time.time()-start,2)
    (ROOT/'output/validation.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
