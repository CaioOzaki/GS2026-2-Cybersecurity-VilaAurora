"""Queda real do serviço coletor por >=1800 s; NÃO é corte de WAN física/VPN.
Não acelerar relógio. Testa cinco bordas lógicas e mTLS em loopback.
"""
import json,math,subprocess,sys,time,sqlite3,statistics,threading
from pathlib import Path
import psutil
from .common import ROOT,RUNTIME,SITES,KINDS,audit,save_json,utc
from .pki import setup
from .edge import start_edges
from .mqtt import publish

def cloud():
    return subprocess.Popen([sys.executable,'-m','aurora.cloud'],cwd=ROOT,
        stdout=subprocess.DEVNULL,stderr=(RUNTIME/'cloud-stderr.log').open('a'))

def run(seconds=1802):
    if seconds<1800:raise ValueError('O teste de entrega requer pelo menos 1800 segundos')
    setup();edges=start_edges();p=cloud();time.sleep(2)
    proc=psutil.Process();proc.cpu_percent();measures=[];rounds=0;errors=0;attempts=0
    for e in edges:publish(e.site,e.site+'-temperatura',{'value':5},e.port)
    time.sleep(3);p.terminate();p.wait(timeout=10)
    start=time.monotonic();start_utc=utc();audit('chaos','coletor_desligado',seconds_required=seconds)
    save_json(RUNTIME/'chaos-progress.json',dict(status='em_execucao',start_utc=start_utc,required_seconds=seconds))
    try:
        while time.monotonic()-start<seconds:
            for e in edges:
                for kind in KINDS:
                    attempts+=1
                    # Falha de temperatura periódica gera alarme exclusivamente local.
                    value={'temperatura':12 if rounds%12==0 else 5,'nivel':60,'energia':75,'acesso':0}[kind]
                    try:publish(e.site,e.site+'-'+kind,{'value':value},e.port)
                    except Exception as ex:
                        errors+=1;audit('chaos','falha_publicacao',exception=type(ex).__name__)
            measures.append(dict(t=round(time.monotonic()-start,3),cpu=proc.cpu_percent(),rss=proc.memory_info().rss))
            rounds+=1
            state=[e.state() for e in edges]
            save_json(RUNTIME/'chaos-progress.json',dict(status='em_execucao',start_utc=start_utc,
                elapsed_seconds=round(time.monotonic()-start,3),rounds=rounds,edges=state))
            time.sleep(min(10,max(0,seconds-(time.monotonic()-start))))
        outage=time.monotonic()-start;before=[e.state() for e in edges]
        recover=time.monotonic();p=cloud()
        while time.monotonic()-recover<90:
            if all(e.state()['pending']==0 for e in edges):break
            time.sleep(1)
        recovery=time.monotonic()-recover;after=[e.state() for e in edges]
        with sqlite3.connect(RUNTIME/'cloud.db') as db:
            remote=db.execute('SELECT count(*) FROM events').fetchone()[0]
        local=sum(e['readings'] for e in after)
        result=dict(status='concluido',scope='Falha de serviço HTTPS local; sem WAN física, VPN ou isolamento de hardware',
            start_utc=start_utc,end_utc=utc(),outage_seconds=outage,recovery_seconds=recovery,
            rounds=rounds,publications=attempts,failed_publications=errors,
            local_ingest_availability_percent=100*(attempts-errors)/attempts,
            local_events=local,cloud_unique_events=remote,missing_after_reconciliation=local-remote,
            before_recovery=before,after_recovery=after,cpu_percent_mean=statistics.mean(m['cpu'] for m in measures),
            rss_peak_bytes=max(m['rss'] for m in measures),samples=measures,
            energy='Não medida: requer wattímetro no hardware de borda.',
            network_bytes_scope='Payload MQTT e HTTPS; exclui TLS, TCP/IP e retransmissões de rede.')
        save_json(ROOT/'evidence/chaos.json',result)
        audit('chaos','reconciliacao_concluida',outage_seconds=outage,loss=local-remote)
        save_json(RUNTIME/'chaos-progress.json',dict(status='concluido',result='evidence/chaos.json'))
        print(json.dumps({k:v for k,v in result.items() if k not in ['samples','before_recovery','after_recovery']},ensure_ascii=True),flush=True)
    finally:
        for e in edges:e.close()
        p.terminate();p.wait(timeout=10)

if __name__=='__main__':run()
