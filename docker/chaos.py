"""Ensaio real do túnel virtual por >=1800 s; sem acelerar o relógio.
Executar no host Ubuntu: python3 docker/chaos.py
"""
import json,subprocess,time,statistics
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/docker'
def utc():return datetime.now(timezone.utc).isoformat(timespec='milliseconds')
def cmd(args,timeout=25):
    r=subprocess.run(['docker','compose']+args,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError(' '.join(args[:5])+': '+r.stderr[-1000:])
    return r.stdout
def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/name;temp=p.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(p)
def snapshot(service,ids=False):
    if service=='edge':
        source="from pathlib import Path;import sqlite3,json;d=sqlite3.connect('/state/ubs.db');rows=d.execute('select id from readings').fetchall();logs=Path('/state/central.jsonl').read_text().splitlines();print(json.dumps(dict(readings=len(rows),pending=d.execute('select count(*) from outbox').fetchone()[0],alarms=sum(json.loads(x).get('action')=='alarme_local' for x in logs),ids=[r[0] for r in rows])))"
    else:source="import sqlite3,json;d=sqlite3.connect('/state/cloud.db');rows=d.execute(\"select id from events where site='ubs'\").fetchall();print(json.dumps(dict(events=len(rows),ids=[r[0] for r in rows])))"
    value=json.loads(cmd(['exec','-T',service,'python','-c',source]))
    if not ids:value.pop('ids',None)
    return value
def resource():
    # docker compose não fornece stats; obter o ID deste serviço evita selecionar outro laboratório.
    container=cmd(['ps','-q','edge']).strip()
    r=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}',container],capture_output=True,text=True,check=True,timeout=15)
    return json.loads(r.stdout)
def main():
    before=snapshot('edge');remote_before=snapshot('cloud');samples=[]
    wg_before=cmd(['exec','-T','edge','wg','show','wg0','transfer']).strip()
    paused=False;down=False
    cmd(['exec','-T','edge','ip','link','set','wg0','down']);down=True
    start=time.monotonic();start_utc=utc();deadline=start+1802
    print('Túnel desligado. Iniciando 1802 segundos reais.',flush=True)
    try:
        previous=before['readings']
        while time.monotonic()<deadline:
            sample=snapshot('edge');sample['elapsed_seconds']=round(time.monotonic()-start,3)
            sample['progress_since_previous']=sample['readings']>previous;previous=sample['readings']
            sample['resources']=resource();samples.append(sample)
            save('chaos-progress.json',dict(status='em_execucao',start_utc_host=start_utc,elapsed_seconds=sample['elapsed_seconds'],edge=sample))
            wait=min(20,max(0,deadline-time.monotonic()))
            if wait:time.sleep(wait)
        elapsed=time.monotonic()-start
        offline=snapshot('edge');remote_offline=snapshot('cloud')
        # Congelar apenas os emissores para tornar comparáveis os conjuntos de IDs após o período exigido.
        cmd(['pause','field']);paused=True
        restore=time.monotonic();cmd(['exec','-T','edge','ip','link','set','wg0','up']);down=False
        while time.monotonic()-restore<120:
            if snapshot('edge')['pending']==0:break
            time.sleep(1)
        recovery=time.monotonic()-restore
        after=snapshot('edge',True);remote_after=snapshot('cloud',True)
        local_ids=set(after.pop('ids'));cloud_ids=set(remote_after.pop('ids'))
        missing=sorted(local_ids-cloud_ids);unexpected=sorted(cloud_ids-local_ids)
        result=dict(status='concluido',scope='Piloto UBS em containers Linux. Interface WireGuard desligada; WAN virtual, não corte de fibra física.',
            start_utc_host=start_utc,end_utc_host=utc(),duration_monotonic_seconds=elapsed,recovery_seconds=recovery,
            before=before,offline=offline,after=after,cloud_before=remote_before,cloud_offline=remote_offline,cloud_after=remote_after,
            new_local_events_offline=offline['readings']-before['readings'],new_local_alarms_offline=offline['alarms']-before['alarms'],
            missing_events=len(missing),unexpected_events=len(unexpected),pending_after=after['pending'],
            continuous_progress_percent=100*sum(s['progress_since_previous'] for s in samples[1:])/max(1,len(samples)-1),
            samples=samples,wireguard_transfer_before=wg_before,wireguard_transfer_after=cmd(['exec','-T','edge','wg','show','wg0','transfer']).strip(),
            telemetry_frozen_for_final_snapshot=True,physical_energy='Não medida; requer wattímetro.',
            clock='Consultar clock-linux.txt; UTC do host e duração monotônica são grandezas distintas.')
        result['passed']=elapsed>=1800 and result['new_local_events_offline']>0 and result['new_local_alarms_offline']>0 and remote_offline['events']==remote_before['events'] and not missing and not unexpected and after['pending']==0
        save('chaos-tunnel.json',result)
        save('chaos-progress.json',dict(status='concluido',passed=result['passed'],result='chaos-tunnel.json'))
        print(json.dumps({k:result[k] for k in ['passed','duration_monotonic_seconds','recovery_seconds','new_local_events_offline','new_local_alarms_offline','missing_events','pending_after']}),flush=True)
        if not result['passed']:raise SystemExit(1)
    finally:
        if down:cmd(['exec','-T','edge','ip','link','set','wg0','up'])
        if paused:cmd(['unpause','field'])

if __name__=='__main__':main()
