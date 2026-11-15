from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
import json,re
root=Path(__file__).resolve().parents[2]
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
result=[]
with ZipFile(root/'requirements/Шаблон презентации.pptx') as z:
    for n in sorted([n for n in z.namelist() if re.fullmatch('ppt/slides/slide[0-9]+.xml',n)],key=lambda n:int(re.search(r'slide(\d+)',n).group(1))):
        el=E.fromstring(z.read(n));shapes=[]
        for s in el.findall('.//p:sp',ns):
            x=s.find('p:spPr/a:xfrm',ns)
            vals={}
            if x is not None:
                for e in x:vals[e.tag.split('}')[-1]]={k:round(int(v)/914400,4) for k,v in e.attrib.items()}
            p=[]
            for par in s.findall('.//a:p',ns):
                runs=[]
                for r in par.findall('a:r',ns):
                    rp=r.find('a:rPr',ns);t=r.find('a:t',ns)
                    obj={'text':t.text if t is not None else ''}
                    if rp is not None:
                        obj['rPr']=rp.attrib
                        font=rp.find('a:latin',ns)
                        if font is not None:obj['font']=font.attrib
                        col=rp.find('a:solidFill/a:srgbClr',ns)
                        if col is not None:obj['color']=col.attrib
                    runs.append(obj)
                p.append({'pPr':par.find('a:pPr',ns).attrib if par.find('a:pPr',ns) is not None else {},'runs':runs})
            shapes.append({'name':s.find('p:nvSpPr/p:cNvPr',ns).attrib,'geometry_inches':vals,'paragraphs':p})
        result.append({'slide':n,'shapes':shapes})
(root/'night/research/template_geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for slide in result:
    print(slide['slide'])
    for s in slide['shapes']:
        tx=''.join(r['text'] for p in s['paragraphs'] for r in p['runs'])
        fonts=sorted(set((r.get('font',{}).get('typeface',''),r.get('rPr',{}).get('sz',''),r.get('color',{}).get('val','')) for p in s['paragraphs'] for r in p['runs']))
        print(s['name'].get('name'),s['geometry_inches'],fonts,tx[:80])
