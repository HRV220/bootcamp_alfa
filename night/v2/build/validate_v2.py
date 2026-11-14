from pathlib import Path
import hashlib,json,subprocess,sys,zipfile,xml.etree.ElementTree as E,re
ROOT=Path(__file__).resolve().parents[3]; N=ROOT/'night/v2'; PPT=N/'output/Dota2_All_Cases_v2.pptx'
TOOLS=Path('C:/Users/Роман/.codex/plugins/cache/openai-primary-runtime/presentations/26.1110.11613/skills/presentations/container_tools')
results={}
for name,args in [('package',['inspect_presentation_package_integrity.py']),('geometry',['inspect_presentation_layout_geometry.py'])]:
    cmd=[sys.executable,str(TOOLS/args[0]),str(PPT)]
    if name=='geometry':
        cmd+=['--expected-slide-size-emu','12192000,6858000','--expected-slide-count','15','--validate-heading-fit','--fail-on-findings']
        for i in [3,4,5,6,8,11,12,14,15]: cmd+=['--require-native-table-slide',str(i)]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8'); d=json.loads(r.stdout); d['exit_code']=r.returncode
    (N/f'qa/{name}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8'); results[name]=r.returncode==0 and d.get('finding_count',0)==0
baseline=json.loads((N/'qa/input_hashes_before.json').read_text(encoding='utf-8'))
diff=[p for p,h in baseline.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
results['source_materials_unchanged']=not diff
P='http://schemas.openxmlformats.org/presentationml/2006/main'; A='http://schemas.openxmlformats.org/drawingml/2006/main'
with zipfile.ZipFile(PPT) as z:
    tables=[]; note_count=0
    for i in range(1,16):
        r=E.fromstring(z.read(f'ppt/slides/slide{i}.xml')); tables.append(len(r.findall('.//{'+A+'}tbl')))
        nr=E.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml')); note_count+=len(''.join(nr.itertext()))>100
    images=[n for n in z.namelist() if n.startswith('ppt/media/image_')]
    source_hashes={hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['task/case1/lineage2.png','task/case1/1.1.png','task/case2/2.4.png','task/case2/2.1.png']}
    results['embedded_original_images']=all(hashlib.sha256(z.read(n)).hexdigest() in source_hashes for n in images) and len(images)==4
results['notes_complete']=note_count==15
results['pdf_15_pages']=len(re.findall(rb'/Type\s*/Page\b',(N/'qa/final/presentation.pdf').read_bytes()))==15
results['png_15_slides']=len(list((N/'qa/final').glob('*.PNG')))==15
receipt={'checks':results,'passed':all(results.values()),'source_material_count':len(baseline),'changed_sources':diff,'slide_count':15,'native_table_count':sum(tables),'pptx_sha256':hashlib.sha256(PPT.read_bytes()).hexdigest(),'limits':'File checks and saved-output audit only. No cluster/notebook/API rerun; independent visual review is separate.'}
(N/'qa/validation_summary.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(receipt,ensure_ascii=False,indent=2)); assert receipt['passed']
