from native_lib import *
import hashlib,subprocess,sys,re
BASE=NIGHT/'output/Dota2_All_Cases_v2.pptx'; FILE=NIGHT/'output/Dota2_All_Cases_v2_images.pptx'; QA=NIGHT/'qa/images'
TOOLS=Path('C:/Users/Роман/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11217/skills/presentations/container_tools')
result={}
for name,tool,args in [('package','inspect_presentation_package_integrity.py',[]),('geometry','inspect_presentation_layout_geometry.py',['--expected-slide-size-emu','12192000,6858000','--expected-slide-count','22','--validate-heading-fit','--fail-on-findings'])]:
    p=subprocess.run([sys.executable,str(TOOLS/tool),str(FILE)]+args,capture_output=True,text=True,encoding='utf-8'); data=json.loads(p.stdout); result[name]=p.returncode==0 and data.get('finding_count',0)==0; (QA/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(BASE) as old,zipfile.ZipFile(FILE) as z:
    result['main_15_slide_texts_preserved']=all([n.text for n in E.fromstring(old.read(f'ppt/slides/slide{i}.xml')).findall('.//'+q(A,'t'))]==[n.text for n in E.fromstring(z.read(f'ppt/slides/slide{i}.xml')).findall('.//'+q(A,'t'))] for i in range(1,16))
    sourcehash={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'night/image').glob('*.png')}
    userimgs=[n for n in z.namelist() if n.startswith('ppt/media/user_image_')]; result['user_images_original_bytes']=all(hashlib.sha256(z.read(n)).hexdigest() in sourcehash for n in userimgs)
    result['notes_22']=all(f'ppt/notesSlides/notesSlide{i}.xml' in z.namelist() for i in range(1,23))
result['png_22']=len(list(QA.glob('*.PNG')))==22
result['pdf_22']=len(re.findall(rb'/Type\s*/Page\b',(QA/'presentation.pdf').read_bytes()))==22
data={'passed':all(result.values()),'checks':result,'slide_count':22,'main_slides':15,'appendix_slides':7,'sha256':hashlib.sha256(FILE.read_bytes()).hexdigest()}
(QA/'validation_summary.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(data,ensure_ascii=False,indent=2)); assert data['passed']
