from native_lib import *
import re,hashlib
FILE=NIGHT/'output/Dota2_All_Cases_v2_simple.pptx'; QA=NIGHT/'qa/simple'
with zipfile.ZipFile(FILE) as z:
    p=E.fromstring(z.read('ppt/presentation.xml')); count=len(p.find(q(P,'sldIdLst')))
    russian={i:not re.search('[A-Za-z]',' '.join(t.text or '' for t in E.fromstring(z.read(f'ppt/slides/slide{i}.xml')).findall('.//'+q(A,'t')))) for i in [3,13]}
    root=E.fromstring(z.read('ppt/slides/slide5.xml')); pics=root.findall('.//'+q(P,'pic')); er=[p for p in pics if '203234' in p.find('./'+q(P,'nvPicPr')+'/'+q(P,'cNvPr')).get('name','')]
    er_no_crop=len(er)==1 and er[0].find('.//'+q(A,'srcRect')) is None
    # The previous seven appendix slides no longer exist in the package.
    no_appendix=not any(f'ppt/slides/slide{i}.xml' in z.namelist() for i in range(16,23))
data={'slide_count':count,'plain_russian_tables':russian,'single_uncropped_common_er':er_no_crop,'old_appendix_removed':no_appendix,'rendered_png_count':len(list(QA.glob('*.PNG'))),'pdf_page_count':len(re.findall(rb'/Type\s*/Page\b',(QA/'presentation.pdf').read_bytes())),'sha256':hashlib.sha256(FILE.read_bytes()).hexdigest()}
data['passed']=count==15 and all(russian.values()) and er_no_crop and no_appendix and data['rendered_png_count']==15 and data['pdf_page_count']==15
(QA/'validation_summary.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(data,ensure_ascii=False,indent=2)); assert data['passed']
