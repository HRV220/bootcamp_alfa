from pathlib import Path
import zipfile, xml.etree.ElementTree as ET, json, re
root=Path(__file__).resolve().parents[2]
out=root/'night'/'research'
out.mkdir(parents=True,exist_ok=True)
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
for f in (root/'requirements').glob('*.pptx'):
    lines=['# '+f.name]
    with zipfile.ZipFile(f) as z:
        pr=ET.fromstring(z.read('ppt/presentation.xml'))
        lines += [str(pr.find('p:sldSz',ns).attrib)]
        for name in sorted([n for n in z.namelist() if re.match(r'ppt/slides/slide\d+.xml$',n)],key=lambda n:int(re.search(r'slide(\d+)',n).group(1))):
            el=ET.fromstring(z.read(name));lines+=['\n## '+name]
            for shp in el.findall('.//p:sp',ns):
                tx=[''.join(p.itertext()) for p in shp.findall('.//a:t',ns)]
                if tx: lines+=[' / '.join(tx)]
        lines+=['\n## Fonts/colors']
        vals={}
        for name in z.namelist():
            if name.startswith(('ppt/slides/','ppt/theme/')) and name.endswith('.xml'):
                el=ET.fromstring(z.read(name))
                for tag,attr in [('rPr','sz'),('defRPr','sz'),('latin','typeface'),('srgbClr','val')]:
                    for item in el.findall('.//a:'+tag,ns):
                        if attr in item.attrib:vals[tag+':'+item.attrib[attr]]=vals.get(tag+':'+item.attrib[attr],0)+1
        lines += [str(sorted(vals.items(),key=lambda x:-x[1]))]
    (out/(f.stem+'_extracted.md')).write_text('\n'.join(lines),encoding='utf-8')
for f in (root/'requirements'/'examples').glob('*.ipynb'):
    nb=json.loads(f.read_text(encoding='utf-8'))
    lines=['# '+f.name]
    for c in nb['cells']:
        lines+=['\n## '+c['cell_type'],''.join(c['source'])]
        if c.get('outputs'): lines+=['OUTPUTS '+str(c['outputs'])[:1500]]
    (out/(f.stem+'_extracted.md')).write_text('\n'.join(lines),encoding='utf-8')
print('Extracted',len(list(out.glob('*_extracted.md'))),'documents')
