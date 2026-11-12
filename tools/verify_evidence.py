import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'evidence/forensics/manifest.json').read_text(encoding='utf-8'))
failures=[]
for r in manifest['files']:
    p=ROOT/r['file']
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:failures.append(r['file'])
for p in (ROOT/'evidence/forensics').glob('*events.jsonl'):
    previous='0'*64
    for i,line in enumerate(p.read_text(encoding='utf-8').splitlines()):
        row=json.loads(line);digest=row.pop('sha256')
        expected=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        if digest!=expected or row['previous_sha256']!=previous:failures.append(f'{p.name}:linha{i+1}')
        previous=digest
print(json.dumps({'files_checked':len(manifest['files']),'failures':failures,'valid':not failures},indent=2))
sys.exit(bool(failures))
