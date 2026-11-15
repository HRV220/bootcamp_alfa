import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as E

base = Path(__file__).resolve().parents[1]
root = base.parents[1]
ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
with zipfile.ZipFile(base/'output/Dota2_All_Cases_v2_simple.pptx') as source, zipfile.ZipFile(base/'output/Dota2_All_Cases_v2_llm_flow.pptx') as target:
    preserved = []
    for old in list(range(1, 11)) + list(range(12, 16)):
        new = old if old < 11 else old + 1
        left = E.fromstring(source.read(f'ppt/slides/slide{old}.xml'))
        right = E.fromstring(target.read(f'ppt/slides/slide{new}.xml'))
        for text in right.findall('.//a:t', ns):
            if text.text == f'{new:02}':
                text.text = f'{old:02}'
        assert E.tostring(left) == E.tostring(right), (old, new)
        preserved.append([old, new])
    originals = {}
    for index in [1, 2, 3]:
        data = (root/f'task/case3/{index}.png').read_bytes()
        matches = [name for name in target.namelist() if name.startswith('ppt/media/') and target.read(name) == data]
        assert matches, index
        originals[str(index)] = matches
    for num in [11, 12]:
        slide = E.fromstring(target.read(f'ppt/slides/slide{num}.xml'))
        assert not slide.findall('.//a:srcRect', ns), num
    flow = E.fromstring(target.read('ppt/slides/slide11.xml'))
    assert len(flow.findall('.//p:cxnSp', ns)) == 3
    report = {'status': 'pass', 'preserved_slides_old_new': preserved,
              'original_screenshots_embedded_byte_identical': originals,
              'diagram_native_connectors': 3,
              'pptx_sha256': hashlib.sha256((base/'output/Dota2_All_Cases_v2_llm_flow.pptx').read_bytes()).hexdigest()}
    (base/'qa/llm_flow/content_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
