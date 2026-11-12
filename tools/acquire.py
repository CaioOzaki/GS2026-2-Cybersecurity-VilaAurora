"""Aquisição lógica de novas execuções próprias. Não coleta chaves ou senhas."""
import argparse,hashlib,json,shutil,subprocess,platform
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
def now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--security',type=Path,required=True);parser.add_argument('--continuity',type=Path,required=True);args=parser.parse_args()
    out=ROOT/'evidence/forensics';out.mkdir(parents=True,exist_ok=True);acquired=now()
    for source,name in [(args.security,'security-events.jsonl'),(args.continuity,'continuity-events.jsonl')]:
        src=source/'central.jsonl'
        if not src.exists():raise FileNotFoundError(src)
        shutil.copy2(src,out/name)
    command=['w32tm','/query','/status'] if platform.system()=='Windows' else ['timedatectl','status']
    try:
        r=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=10)
        clock={'command':command,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except (OSError,subprocess.TimeoutExpired):clock={'command':command,'status':'não consultado; sincronismo não comprovado'}
    (out/'clock-status.json').write_text(json.dumps(clock,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[]
    for name in ['security-events.jsonl','continuity-events.jsonl']:
        for line in (out/name).read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            rows.append({k:row[k] for k in ['utc','monotonic_ns','component','action','sha256']})
    (out/'timeline.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=[]
    for p in sorted((ROOT/'evidence').rglob('*')):
        if p.is_file() and p.name not in ['manifest.json','manifest.sha256','custody.json']:
            manifest.append({'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (out/'manifest.json').write_text(json.dumps({'acquired_utc_host':acquired,'files':manifest},indent=2),encoding='utf-8')
    (out/'manifest.sha256').write_text('\n'.join(r['sha256']+'  '+r['file'] for r in manifest)+'\n',encoding='ascii')
    (out/'custody.json').write_text(json.dumps({'case':'INC-VA-0712-LAB','acquisition_by':'operador do script','acquired_utc_host':acquired,'method':'Cópia lógica e SHA-256; sem imagem de disco/memória','scope':'Somente execuções próprias sintéticas','clock':'Consultar clock-status.json; não assumir sincronismo externo'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Aquisição lógica concluída. Execute tools/verify_evidence.py e preserve uma cópia independente.')
if __name__=='__main__':main()
