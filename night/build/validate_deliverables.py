"""Repeatable local checks. Writes evidence only under night/qa."""
from pathlib import Path
import subprocess, sys, json, zipfile, xml.etree.ElementTree as E, hashlib, io, re, csv
ROOT=Path(__file__).resolve().parents[2]; N=ROOT/'night'; QA=N/'qa'
SKILL=Path('C:/Users/Роман/.codex/plugins/cache/openai-primary-runtime/presentations/26.1110.11613/skills/presentations/container_tools')
PPT=N/'output/Dota2_SQL_ML.pptx'
def run(name,args):
    r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
    try: result=json.loads(r.stdout)
    except Exception: result={'stdout':r.stdout,'stderr':r.stderr}
    result['process_exit_code']=r.returncode
    (QA/name).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
checks={}
checks['package']=run('package_integrity.json',[sys.executable,str(SKILL/'inspect_presentation_package_integrity.py'),str(PPT)])
args=[sys.executable,str(SKILL/'inspect_presentation_layout_geometry.py'),str(PPT),'--expected-slide-size-emu','12192000,6858000','--expected-slide-count','11','--validate-heading-fit','--validate-bullet-geometry','--fail-on-findings']
for i in [3,5,6,7,10,11]: args+=['--require-native-table-slide',str(i)]
checks['geometry']=run('layout_geometry.json',args)
checks['chart']=run('native_chart.json',[sys.executable,str(SKILL/'native_quantitative_chart_gate.py'),str(PPT),'--expected-chart-slides','8','--require-embedded-workbook-slide','8','--target-application','portable'])
run('input_integrity.json',[sys.executable,str(N/'build/input_manifest.py')])
A='http://schemas.openxmlformats.org/drawingml/2006/main'; P='http://schemas.openxmlformats.org/presentationml/2006/main'; C='http://schemas.openxmlformats.org/drawingml/2006/chart'; S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
with zipfile.ZipFile(PPT) as z:
    native_tables=[]; note_lengths=[]; bounds=[]
    for i in range(1,12):
        r=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
        native_tables.append(len(r.findall('.//{'+A+'}tbl')))
        nr=E.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml')); note_lengths.append(len(''.join(nr.itertext())))
        for xf in r.findall('.//{'+A+'}xfrm')+r.findall('.//{'+P+'}xfrm'):
            off=xf.find('{'+A+'}off'); ext=xf.find('{'+A+'}ext')
            if off is not None and ext is not None:
                x,y,cx,cy=[int(v) for v in (off.get('x'),off.get('y'),ext.get('cx'),ext.get('cy'))]
                if min(x,y,cx,cy)<0 or x+cx>12192000 or y+cy>6858000: bounds.append({'slide':i,'x':x,'y':y,'cx':cx,'cy':cy})
    chart=E.fromstring(z.read('ppt/charts/chart1.xml'))
    chart_counts=[int(p.find('{'+C+'}v').text) for p in chart.findall('.//{'+C+'}numCache/{'+C+'}pt')]
    with zipfile.ZipFile(io.BytesIO(z.read('ppt/embeddings/chart-data.xlsx'))) as wb:
        sheet=E.fromstring(wb.read('xl/worksheets/sheet1.xml'))
        workbook_counts=[int(c.find('{'+S+'}v').text) for row in sheet.findall('.//{'+S+'}row')[1:] for c in row if c.get('r','').startswith('B')]
with (N/'analysis/smurf_account_summary.csv').open(encoding='utf-8-sig',newline='') as f:
    summary_rows=list(csv.DictReader(f))
print('CSV columns:',list(summary_rows[0]))
source_rows=list(csv.DictReader((ROOT/'task/case2/smurf_players.csv').open(encoding='utf-8-sig',newline='')))
account_counts={k:sum(r['account_id']==k for r in source_rows) for k in sorted({r['account_id'] for r in source_rows},key=int)}
semantic={
 'slide_count':11, 'native_table_count':sum(native_tables),'native_table_slides':[i+1 for i,v in enumerate(native_tables) if v],
 'speaker_notes_complete':all(n>100 for n in note_lengths), 'out_of_canvas_objects':bounds,
 'chart_counts':chart_counts,'embedded_workbook_counts':workbook_counts,
 'chart_source_consistent':chart_counts==workbook_counts==list(account_counts.values()),
 'source_account_counts':account_counts,
 'chart_count_sum':sum(chart_counts), 'rendered_slide_count':len(list((QA/'final').glob('*.PNG'))),
 'pdf_page_count':len(re.findall(rb'/Type\s*/Page\b',(QA/'final/presentation.pdf').read_bytes())),
 'pptx_sha256':hashlib.sha256(PPT.read_bytes()).hexdigest(),
 'limits':['Geometry does not prove factual correctness. Independent visual review required.','No cluster execution, live SLA or ML model validation.']}
(QA/'semantic_checks.json').write_text(json.dumps(semantic,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':{k:v.get('status',v.get('process_exit_code')) for k,v in checks.items()},'semantic':semantic},ensure_ascii=False,indent=2))
assert semantic['speaker_notes_complete'] and not bounds and semantic['chart_source_consistent']
assert semantic['rendered_slide_count']==11 and semantic['pdf_page_count']==11
assert checks['package'].get('status')=='pass' and checks['geometry']['process_exit_code']==0 and checks['chart']['process_exit_code']==0
