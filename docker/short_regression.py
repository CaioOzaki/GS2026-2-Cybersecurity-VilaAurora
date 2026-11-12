"""Regressão curta após endurecimento, complementar ao ensaio anterior de 30 minutos."""
import subprocess,json,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/docker'
def run(args):
    r=subprocess.run(['docker','compose']+args,cwd=ROOT,capture_output=True,text=True,timeout=25)
    if r.returncode:raise RuntimeError(r.stderr)
    return r.stdout
def state(service):
    code=("import sqlite3,json;d=sqlite3.connect('/state/ubs.db');print(json.dumps(dict(n=d.execute('select count(*) from readings').fetchone()[0],pending=d.execute('select count(*) from outbox').fetchone()[0])))" if service=='edge' else "import sqlite3,json;d=sqlite3.connect('/state/cloud.db');print(json.dumps(dict(n=d.execute('select count(*) from events').fetchone()[0])))")
    return json.loads(run(['exec','-T',service,'python','-c',code]))
before=state('edge');cloud_before=state('cloud');start_utc=datetime.now(timezone.utc).isoformat();paused=False;down=False
try:
    run(['exec','-T','edge','ip','link','set','wg0','down']);down=True;start=time.monotonic()
    time.sleep(45)
    offline=state('edge');cloud_offline=state('cloud');duration=time.monotonic()-start
    run(['pause','field']);paused=True
    recover=time.monotonic();run(['exec','-T','edge','ip','link','set','wg0','up']);down=False
    while time.monotonic()-recover<60:
        if state('edge')['pending']==0:break
        time.sleep(1)
    after=state('edge');cloud_after=state('cloud')
    result=dict(start_utc_host=start_utc,scope='Regressão curta da versão revisada; NÃO substitui o ensaio de 30 minutos',duration_seconds=duration,recovery_seconds=time.monotonic()-recover,before=before,cloud_before=cloud_before,offline=offline,cloud_offline=cloud_offline,after=after,cloud_after=cloud_after)
    result['passed']=offline['n']>before['n'] and cloud_offline['n']==cloud_before['n'] and after['pending']==0 and after['n']==cloud_after['n']
    (OUT/'short-regression.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))
    if not result['passed']:raise SystemExit(1)
finally:
    if down:run(['exec','-T','edge','ip','link','set','wg0','up'])
    if paused:run(['unpause','field'])
