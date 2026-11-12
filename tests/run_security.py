"""Execução somente no laboratório local. Não aceita URL de terceiros."""
import hashlib,json,os,sqlite3,subprocess,sys,time,urllib.request,urllib.error,urllib.parse,platform
from pathlib import Path
from aurora.common import ROOT,RUNTIME,save_json,read_json,audit,utc
from aurora.pki import setup,PKI,client_context,revoke,issue
from aurora.edge import Edge
from aurora.mqtt import publish
from aurora.web import start_server
from aurora.auth import totp
from aurora.defense import SIEM

os.environ['AURORA_CLOUD']='https://localhost:9463/ingest'
os.environ['AURORA_CLOUD_PORT']='9463'
RESULT=[]

def check(name,condition,details):
    RESULT.append(dict(test=name,passed=bool(condition),details=details,utc=utc()))
    print(('PASS ' if condition else 'FAIL ')+name,flush=True)

def request(path,data=None,cookie='',csrf='',port=8082):
    req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':csrf})
    try:
        with urllib.request.urlopen(req,timeout=4) as r:return r.status,json.load(r),r.headers
    except urllib.error.HTTPError as e:return e.code,json.load(e),e.headers

def main():
    setup();edge=Edge('escola',8893);edge.start()
    cloud=subprocess.Popen([sys.executable,'-m','aurora.cloud'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=(RUNTIME/'cloud.log').open('w'))
    web=start_server(8082,[edge]);legacy=start_server(8083,legacy=True);siem=SIEM();siem.start()
    try:
        time.sleep(1)
        publish('escola','escola-temperatura',{'value':12},8893)
        check('MQTT mTLS com identidade própria',edge.state()['readings']==1,edge.state())
        check('Alarme local sem decisão da nuvem',edge.state()['alerts']==1,{'alarm_count':edge.state()['alerts']})
        for name,context,topic in [('Sem certificado',client_context(),None),('CA não confiável',client_context('intruso'),None),
              ('ACL: certificado não publica por outro sensor',None,'sites/escola/devices/escola-nivel/telemetry')]:
            before=edge.state()['readings'];denied=False
            try:publish('escola','escola-temperatura',{'value':5},8893,topic=topic,context=context)
            except Exception:denied=True
            check(name,denied and edge.state()['readings']==before,{'denied':denied,'readings_unchanged':edge.state()['readings']==before})
        publish('escola','escola-acesso',{'value':0},8893)
        from cryptography import x509
        old=x509.load_pem_x509_certificate((PKI/'escola-acesso.crt').read_bytes())
        serial=format(old.serial_number,'x');revoke(serial);denied=False
        try:publish('escola','escola-acesso',{'value':0},8893)
        except Exception:denied=True
        new=issue('escola-acesso');publish('escola','escola-acesso',{'value':0},8893)
        check('Revogação e rotação X.509',denied and new!=serial,{'old_serial':serial,'new_serial':new,'old_blocked':denied})
        import paho.mqtt.client as mqtt
        client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='interoperabilidade-paho')
        client.tls_set_context(client_context('escola-nivel'));client.connect('localhost',8893);client.loop_start()
        for _ in range(30):
            if client.is_connected():break
            time.sleep(.1)
        info=client.publish('sites/escola/devices/escola-nivel/telemetry',json.dumps({'value':62}),qos=1)
        info.wait_for_publish(timeout=4);ok=info.is_published();client.disconnect();client.loop_stop()
        check('Cliente independente Paho MQTT QoS1',ok,{'puback_received':ok})
        for _ in range(20):
            edge.sync_once()
            if edge.state()['pending']==0:break
            time.sleep(.2)
        with sqlite3.connect(RUNTIME/'cloud.db') as db:count=db.execute('SELECT count(*) FROM events').fetchone()[0]
        check('Sincronização HTTPS mTLS',edge.state()['pending']==0 and count==edge.state()['readings'],{'local':edge.state()['readings'],'cloud':count})
        # Reenvio deliberado: nuvem deve manter uma linha para o mesmo UUID.
        row=edge.db.execute('SELECT payload FROM readings LIMIT 1').fetchone()[0]
        req=urllib.request.Request('https://localhost:9463/ingest',data=('['+row+']').encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,context=client_context('edge-escola')) as r:r.read()
        with sqlite3.connect(RUNTIME/'cloud.db') as db:count_after=db.execute('SELECT count(*) FROM events').fetchone()[0]
        check('Reconciliação idempotente UUID',count_after==count,{'before':count,'after_duplicate':count_after})
        payload="' OR 1=1 --";query=urllib.parse.urlencode({'q':payload})
        vulnerable=request('/legacy/search?'+query,port=8083);fixed=request('/fixed/search?'+query,port=8083)
        check('SQLi antes/depois - tautologia',len(vulnerable[1]['rows'])==3 and len(fixed[1]['rows'])==0,
              {'payload':payload,'vulnerable':vulnerable[1],'fixed':fixed[1]})
        union="' UNION SELECT id,name,role FROM users --"
        a=request('/legacy/search?'+urllib.parse.urlencode({'q':union}),port=8083)
        b=request('/fixed/search?'+urllib.parse.urlencode({'q':union}),port=8083)
        check('SQLi antes/depois - extração sintética',len(a[1]['rows'])==2 and b[1]['rows']==[],{'vulnerable':a[1],'fixed':b[1]})
        injection="escola'; UPDATE schedule SET hour=2 WHERE pump='escola'; --"
        request('/legacy/schedule',{'pump':injection},port=8083)
        with sqlite3.connect(RUNTIME/'vulnerable.db') as db:legacy_hour=db.execute('SELECT hour FROM schedule').fetchone()[0]
        with sqlite3.connect(RUNTIME/'history.db') as db:safe_hour=db.execute('SELECT hour FROM schedule').fetchone()[0]
        check('Reprodução do agendamento alterado',legacy_hour==2 and safe_hour==8,{'legacy_hour':legacy_hour,'safe_hour':safe_hour,'scope':'Somente bancos descartáveis locais; sem bomba real.'})
        bad=request('/fixed/search?'+urllib.parse.urlencode({'q':'x'*81}),port=8083)
        check('Validação e erro genérico',bad[0]==400 and 'sqlite' not in str(bad[1]).lower(),{'status':bad[0],'body':bad[1]})
        credentials=read_json(RUNTIME/'credentials.json');sessions={}
        denied=request('/api/login',dict(username='operador',password=credentials['operador']['password'],otp='000000'))
        check('Senha sem segundo fator recusada',denied[0]==401,{'status':denied[0]})
        for role in credentials:
            cred=credentials[role];otp=totp(cred['totp_secret']);login=dict(username=role,password=cred['password'],otp=otp)
            code,data,headers=request('/api/login',login)
            sessions[role]=(headers.get('Set-Cookie','').split(';')[0],data.get('csrf',''))
            check('MFA '+role,code==200,{'status':code,'role':data.get('role')})
            if role=='operador':
                replay=request('/api/login',login);check('TOTP não reutilizável',replay[0]==401,{'status':replay[0]})
        op,csrf=sessions['operador'];aud,ac=sessions['auditor'];coord,cc=sessions['coordenacao']
        noauth=request('/api/status');check('Painel restrito sem autenticação',noauth[0]==401,{'status':noauth[0]})
        nocsrf=request('/api/command',{'action':'parar_bomba'},op)
        check('Proteção CSRF',nocsrf[0]==403,{'status':nocsrf[0]})
        denied=request('/api/command',{'action':'parar_bomba'},aud,ac)
        check('RBAC auditor não comanda',denied[0]==403,{'status':denied[0]})
        code,pending,_=request('/api/command',{'action':'parar_bomba'},op,csrf)
        before_approval=read_json(RUNTIME/'actuators.json')['pump_running']
        reject=request('/api/approve',{'id':pending['id']},op,csrf)
        approved=request('/api/approve',{'id':pending['id']},coord,cc)
        after_approval=read_json(RUNTIME/'actuators.json')['pump_running']
        check('Ação crítica exige coordenação',code==202 and reject[0]==403 and approved[0]==200 and before_approval and not after_approval,
              {'pending_status':code,'operator_approval':reject[0],'coordination_approval':approved[0],
               'pump_before_approval':before_approval,'pump_after_approval':after_approval,
               'approval_test':'Requisições automatizadas testam permissões; na operação a coordenação decide no painel.'})
        audit('vpn','replay_vpn_login',source='synthetic_replay',hour=2,external_ip='198.51.100.23',mfa=False)
        time.sleep(.8);siem.poll();alerts=read_json(RUNTIME/'siem-alerts.json',[])
        codes=sorted({r['rule'] for r in alerts});check('Quatro regras SIEM',codes==['D01','D02','D03','D04'],{'rules':codes,'VPN':'Evento sintético, sem túnel VPN nesta execução.'})
        revoked=read_json(PKI/'revoked.json',[])
        temp_serial=format(x509.load_pem_x509_certificate((PKI/'escola-temperatura.crt').read_bytes()).serial_number,'x')
        check('SOAR isola certificado após violação da ACL',temp_serial in revoked,{'identity':'escola-temperatura','revoked':temp_serial in revoked})
        save_json(ROOT/'evidence/detections.json',alerts)
        # Salva somente dados de teste públicos, sem cookies, senhas ou sementes TOTP.
        result=dict(scope='Testes próprios loopback '+platform.system()+'. Não validam VPN/segmentação.',platform=platform.platform(),utc=utc(),
            passed=sum(r['passed'] for r in RESULT),total=len(RESULT),tests=RESULT)
        save_json(ROOT/'evidence/security.json',result)
        print(json.dumps({'passed':result['passed'],'total':result['total']}),flush=True)
        if result['passed']!=result['total']:sys.exit(1)
    finally:
        siem.stop.set();web.shutdown();web.server_close();legacy.shutdown();legacy.server_close();edge.close();cloud.terminate();cloud.wait(timeout=10)

if __name__=='__main__':main()
