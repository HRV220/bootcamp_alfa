import zipfile, xml.etree.ElementTree as E
from pathlib import Path
root=Path(__file__).resolve().parents[1]
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
with zipfile.ZipFile(root/'output/Dota2_SQL_ML.pptx') as z: parts={n:z.read(n) for n in z.namelist()}
for variant in ['nochart','nonotes','bare']:
    d=parts.copy()
    if variant in ['nochart','bare']:
        for i in range(1,12):
            r=E.fromstring(d[f'ppt/slides/slide{i}.xml'])
            for tree in r.iter('{'+P+'}spTree'):
                for f in list(tree):
                    if f.tag=='{'+P+'}graphicFrame' and f.find('.//{http://schemas.openxmlformats.org/drawingml/2006/chart}chart') is not None: tree.remove(f)
            d[f'ppt/slides/slide{i}.xml']=E.tostring(r,encoding='utf-8',xml_declaration=True)
    if variant in ['nonotes','bare']:
        for key in list(d):
            if 'notesSlides/' in key: del d[key]
        t=E.fromstring(d['[Content_Types].xml'])
        for e in list(t):
            if '/notesSlides/' in e.get('PartName',''): t.remove(e)
        E.register_namespace('',CT); d['[Content_Types].xml']=E.tostring(t,encoding='utf-8',xml_declaration=True)
    for i in range(1,12):
        key=f'ppt/slides/_rels/slide{i}.xml.rels'; t=E.fromstring(d[key])
        for e in list(t):
            if (variant in ['nonotes','bare'] and e.get('Type','').endswith('/notesSlide')) or (variant in ['nochart','bare'] and e.get('Type','').endswith('/chart')): t.remove(e)
        E.register_namespace('',REL); d[key]=E.tostring(t,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(root/f'build/debug_{variant}.pptx','w',zipfile.ZIP_DEFLATED) as z:
        for k,v in d.items(): z.writestr(k,v)
