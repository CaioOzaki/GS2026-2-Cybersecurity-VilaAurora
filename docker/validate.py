"""Validação estruturada dos caminhos permitidos/proibidos do próprio laboratório."""
import subprocess,json,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/docker'
def command(args):
    r=subprocess.run(['docker','compose']+args,cwd=ROOT,capture_output=True,text=True,timeout=20)
    if r.returncode:raise RuntimeError(r.stderr[-1000:])
    return r.stdout
def main():
    OUT.mkdir(parents=True,exist_ok=True);checks=[]
    probes=[('operator','172.29.20.2',8080,True,'Operador alcança painel'),
            ('admin','172.29.30.2',8080,True,'Administração alcança painel'),
            ('field','172.29.10.2',8883,True,'IoT alcança listener MQTT TLS'),
            ('operator','172.29.20.2',8883,False,'Operador não alcança MQTT'),
            ('field','172.29.10.2',8080,False,'IoT não alcança painel'),
            ('edge','172.29.0.2',9443,False,'Coletor bloqueado fora do túnel')]
    for service,host,port,expected,label in probes:
        source=f"import socket,json\ntry:\n s=socket.create_connection(('{host}',{port}),timeout=2);s.close();print(json.dumps(dict(reachable=True)))\nexcept OSError as e:print(json.dumps(dict(reachable=False,error=type(e).__name__)))"
        result=json.loads(command(['exec','-T',service,'python','-c',source]))
        checks.append(dict(test=label,source=service,destination=host,port=port,expected_reachable=expected,**result,passed=result['reachable']==expected))
    source="import urllib.request;from aurora.pki import client_context;r=urllib.request.Request('https://cloud:9443/ingest',data=b'[]',headers={'Content-Type':'application/json'});s=urllib.request.urlopen(r,context=client_context('edge-ubs'),timeout=4);print(s.status)"
    status=int(command(['exec','-T','edge','python','-c',source]))
    checks.append(dict(test='HTTPS mTLS pelo WireGuard',status=status,passed=status==200))
    uid={}
    for service in ['cloud','edge','field','operator','admin']:
        value=int(command(['exec','-T',service,'python','-c',"from pathlib import Path;print(next(l.split()[1] for l in Path('/proc/1/status').read_text().splitlines() if l.startswith('Uid:')))" ]))
        uid[service]=value
    checks.append(dict(test='Processos principais sem root',uids=uid,passed=all(v==1000 for v in uid.values())))
    wg=command(['exec','-T','edge','wg','show'])+'\n'+command(['exec','-T','cloud','wg','show'])
    (OUT/'wireguard.txt').write_text(wg,encoding='utf-8')
    (OUT/'firewall-edge.txt').write_text(command(['exec','-T','edge','iptables','-S']),encoding='utf-8')
    (OUT/'firewall-cloud.txt').write_text(command(['exec','-T','cloud','iptables','-S']),encoding='utf-8')
    (OUT/'routes.txt').write_text(command(['exec','-T','edge','ip','route']),encoding='utf-8')
    bindings={}
    for service in ['cloud','edge','field','operator','admin']:
        cid=command(['ps','-q',service]).strip()
        r=subprocess.run(['docker','inspect',cid,'--format','{{json .NetworkSettings.Ports}}'],capture_output=True,text=True,check=True,timeout=15)
        bindings[service]=json.loads(r.stdout)
    localhost_only=all(entry['HostIp']=='127.0.0.1' for ports in bindings.values() for group in (ports or {}).values() if group for entry in group)
    viewer_published=bool(bindings['operator'].get('8088/tcp'))
    viewer_firewall=command(['exec','-T','operator','iptables','-S'])
    (OUT/'firewall-viewer.txt').write_text(viewer_firewall,encoding='utf-8')
    checks.append(dict(test='Visualizador publicado em loopback com saída geral bloqueada',bindings=bindings,viewer_published=viewer_published,passed=localhost_only and viewer_published and '-P OUTPUT DROP' in viewer_firewall))
    result=dict(utc_host=datetime.now(timezone.utc).isoformat(),scope='UBS em cinco containers Linux; redes virtuais reais no Docker Desktop/WSL2',
        tests=checks,passed=sum(x['passed'] for x in checks),total=len(checks),note='TLS do MQTT é validado separadamente por probe_mqtt.py. Administração remota SSH/RDP não é oferecida.')
    (OUT/'network.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for c in [['timedatectl','status'],['timedatectl','show-timesync','--all']]:
        r=subprocess.run(c,capture_output=True,text=True,timeout=10)
        with (OUT/'clock-linux.txt').open('a',encoding='utf-8') as f:f.write(' '.join(c)+'\n'+r.stdout+r.stderr+'\n')
    print(json.dumps({'passed':result['passed'],'total':result['total']},ensure_ascii=True))
    if result['passed']!=result['total']:raise SystemExit(1)
if __name__=='__main__':main()
