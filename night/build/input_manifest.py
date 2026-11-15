import hashlib, json
from pathlib import Path
root = Path(__file__).resolve().parents[2]
data = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ['requirements', 'task'] for p in sorted((root/folder).rglob('*')) if p.is_file()}
out=root/'night/qa/input_hashes_before.json'
if not out.exists(): out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
else:
    baseline=json.loads(out.read_text(encoding='utf-8'))
    result={'unchanged':baseline==data, 'files':len(data), 'differences':[k for k in baseline.keys() | data.keys() if baseline.get(k)!=data.get(k)]}
    (root/'night/qa/input_integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
