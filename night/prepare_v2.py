from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent.parent
out=root/'night/v2'
for d in ['build','output','qa','research','assets']: (out/d).mkdir(parents=True,exist_ok=True)
files=[p for d in ['requirements','task'] for p in (root/d).rglob('*') if p.is_file() and not any(x in p.parts for x in ['.venv','__pycache__'])]
data={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(out/'qa/input_hashes_before.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
old=(root/'night/build/build_deck.py').read_text(encoding='utf-8')
lib=old[:old.index('slides=[]')]+old[old.index('def make_chart():'):old.index('with zipfile.ZipFile(ROOT/')]
lib=lib.replace("NIGHT=ROOT/'night'","NIGHT=ROOT/'night/v2'").replace('parents[2]','parents[3]')
(out/'build/native_lib.py').write_text(lib,encoding='utf-8')
print('source files',len(files))
