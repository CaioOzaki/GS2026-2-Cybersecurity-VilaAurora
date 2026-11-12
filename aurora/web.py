import argparse,html,json,re,sqlite3,threading,time,uuid,secrets,urllib.parse,os
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from .common import RUNTIME,ROOT,SITES,audit,read_json,save_json,utc
from .auth import Auth

PAGE='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vila Aurora | Supervisão local</title><style>
body{font:18px/1.5 system-ui,sans-serif;background:#101c29;color:#f2f6fb;margin:0}main{max-width:1120px;margin:auto;padding:32px}
a{color:#8fe6da}h1{font-size:40px;line-height:1.1}h2{font-size:24px}small{color:#c1d3e1}section{background:#1d3043;padding:24px;border:1px solid #55738b;border-radius:12px;margin:22px 0}
input,button,select{font:inherit;padding:12px;margin:6px;border-radius:6px;border:1px solid #9eb9cf}input,select{background:#fff;color:#111}button{background:#96f2dd;color:#102125;cursor:pointer;font-weight:700}
:focus-visible{outline:4px solid #ffd76b;outline-offset:3px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #55738b}label{display:block}.tag{color:#ffd76b;font-weight:700}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}.card{padding:15px;background:#263e54;border-radius:8px}.big{font-size:30px;font-weight:bold}pre{white-space:pre-wrap;overflow-wrap:anywhere}.error{color:#ffd5d5}.skip{position:absolute;left:-9999px}.skip:focus{left:20px}
</style><a class="skip" href="#conteudo">Pular para o conteúdo</a><main id="conteudo"><small>REDE COMUNITÁRIA VILA AURORA • LABORATÓRIO LOCAL</small>
<h1>Continuidade com segurança.</h1><p>Telemetria, alertas e decisões humanas para os cinco espaços comunitários.</p>
<nav><a href="#acesso">Acesso</a> | <a href="#borda">Bordas</a> | <a href="#teste">Testes</a> | <a href="#atuadores">Intervenção</a></nav>
<section id="acesso"><h2>Acesso com dois fatores</h2><form id="login"><label>Perfil <select name="username"><option>operador</option><option>tecnico</option><option>coordenacao</option><option>auditor</option></select></label>
<label>Senha <input name="password" type="password" required autocomplete="current-password"></label><label>Código do autenticador <input name="otp" inputmode="numeric" pattern="[0-9]{6}" required autocomplete="one-time-code"></label><button>Entrar</button></form><p id="authstate" role="status">Credenciais de laboratório ficam somente na pasta privada .runtime.</p></section>
<section id="borda"><h2>Operação local</h2><p id="scope">Carregando estado...</p><div class="cards" id="cards"></div><p id="totals" aria-live="polite"></p><button id="refresh">Atualizar leituras</button></section>
<section id="teste"><h2>Evidências dos testes</h2><pre id="results">Entre para consultar os resultados.</pre><p><a href="http://127.0.0.1:8081/" target="_blank" rel="noopener">Abrir comparação SQL Injection no laboratório isolado</a></p><small>A porta 8081 só funciona quando a demonstração vulnerável é iniciada explicitamente.</small></section>
<section id="atuadores"><h2>Intervenção com aprovação</h2><p>Comandos de alto impacto ficam pendentes até a aprovação da coordenação.</p><button id="request">Solicitar parada da bomba</button><p id="commandstate" role="status"></p><label>ID da solicitação <input id="requestid"></label><button id="approve">Aprovar como coordenação</button></section>
<section><h2>Limites desta execução</h2><p>As bordas são processos lógicos no mesmo computador. VPN WireGuard, VLANs e corte real de WAN precisam do laboratório Linux/Docker. Nenhum equipamento físico está conectado.</p></section><small>Caio Yudi Ozaki Godinho • RM 552505 • 4ECA</small></main><script src="/app.js"></script></html>'''

JS='''let csrf='';async function call(p,data){let r=await fetch(p,{method:data?'POST':'GET',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data?JSON.stringify(data):undefined});let j=await r.json();if(!r.ok)throw Error(j.error||'Acesso negado');return j;}
async function refresh(){try{let j=await call('/api/status');document.querySelector('#scope').textContent=j.scope;let c=document.querySelector('#cards');c.replaceChildren();for(let e of j.edges){let d=document.createElement('div');d.className='card';let h=document.createElement('h3');h.textContent=e.site.toUpperCase();d.append(h);let p=document.createElement('p');p.textContent=e.readings+' leituras | '+e.pending+' na fila | '+e.alerts+' alertas locais';d.append(p);let small=document.createElement('small');small.textContent='Temperatura: '+(e.last.temperatura??'-')+' °C';d.append(small);c.append(d);}document.querySelector('#totals').textContent='Atualização: '+j.utc;let ev=j.evidence;document.querySelector('#results').textContent=JSON.stringify({testes:ev['security.json']?.passed+'/'+ev['security.json']?.total,IA:ev['ai.json'],campanha:ev['phishing.json']},null,2);}catch(e){document.querySelector('#scope').textContent=e.message;}}
document.querySelector('#login').onsubmit=async(e)=>{e.preventDefault();try{let j=await call('/api/login',Object.fromEntries(new FormData(e.target)));csrf=j.csrf;document.querySelector('#authstate').textContent='Conectado como '+j.role;e.target.password.value='';e.target.otp.value='';e.target.hidden=true;refresh();}catch(x){document.querySelector('#authstate').textContent=x.message;}};
document.querySelector('#refresh').onclick=refresh;document.querySelector('#request').onclick=async()=>{try{let j=await call('/api/command',{action:'parar_bomba'});document.querySelector('#commandstate').textContent='Solicitação '+j.id+': '+j.status;document.querySelector('#requestid').value=j.id;}catch(e){document.querySelector('#commandstate').textContent=e.message;}};
document.querySelector('#approve').onclick=async()=>{try{let j=await call('/api/approve',{id:document.querySelector('#requestid').value});document.querySelector('#commandstate').textContent=j.status;}catch(e){document.querySelector('#commandstate').textContent=e.message;}};
setInterval(refresh,5000);'''

def init_db():
    if not (RUNTIME/'actuators.json').exists():save_json(RUNTIME/'actuators.json',{'pump_running':True})
    for name in ['history.db','vulnerable.db']:
        with sqlite3.connect(RUNTIME/name) as db:
            db.executescript('CREATE TABLE IF NOT EXISTS history(id INTEGER,person TEXT,event TEXT); CREATE TABLE IF NOT EXISTS users(id INTEGER,name TEXT,role TEXT); CREATE TABLE IF NOT EXISTS schedule(pump TEXT,hour INTEGER);')
            if not db.execute('SELECT count(*) FROM history').fetchone()[0]:
                db.executemany('INSERT INTO history VALUES(?,?,?)',[(1,'p001','entrada'),(2,'p002','saída'),(3,'p003','entrada')])
                db.executemany('INSERT INTO users VALUES(?,?,?)',[(1,'voluntario001','operador'),(2,'voluntario002','tecnico')]);db.execute('INSERT INTO schedule VALUES(?,?)',('escola',8))

def search(query,safe=True):
    if safe:
        if not isinstance(query,str) or len(query)>80:raise ValueError('Entrada inválida')
        db=sqlite3.connect((RUNTIME/'history.db').as_uri()+'?mode=ro',uri=True)
        def authorizer(action,a,b,c,d):
            if action==sqlite3.SQLITE_READ and a!='history':return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION) else sqlite3.SQLITE_DENY
        db.set_authorizer(authorizer)
        try:return db.execute('SELECT id,person,event FROM history WHERE person=?',(query,)).fetchall()
        finally:db.close()
    with sqlite3.connect(RUNTIME/'vulnerable.db') as db:
        return db.execute("SELECT id,person,event FROM history WHERE person='"+query+"'").fetchall()

def legacy_schedule(payload):
    # Laboratório inseguro proposital e separado; nunca chamado pelo painel seguro.
    with sqlite3.connect(RUNTIME/'vulnerable.db') as db:
        db.executescript("UPDATE schedule SET hour=8 WHERE pump='"+payload+"';")

def make_handler(edges=None,legacy=False):
    auth=Auth() if not legacy else None
    linux_mode=os.environ.get('AURORA_DEPLOYMENT')=='linux-ubs'
    def display_page():
        if not linux_mode:return PAGE
        return (PAGE.replace('Telemetria, alertas e decisões humanas para os cinco espaços comunitários.',
                 'Piloto UBS: telemetria e alertas locais da Rede Vila Aurora.')
            .replace('As bordas são processos lógicos no mesmo computador. VPN WireGuard, VLANs e corte real de WAN precisam do laboratório Linux/Docker. Nenhum equipamento físico está conectado.',
                 'Esta tela mostra a UBS em containers Linux, com Mosquitto, túnel WireGuard e redes separadas. O estado do túnel aparece acima. Os dispositivos são geradores de telemetria; nenhum equipamento físico está conectado.')
            .replace('Abrir comparação SQL Injection no laboratório isolado','Comparação SQL Injection - laboratório nativo separado'))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,value,ctype='application/json',cookie=None):
            raw=(json.dumps(value,ensure_ascii=False) if ctype=='application/json' else value).encode()
            self.send_response(status);self.send_header('Content-Type',ctype+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
            if cookie:self.send_header('Set-Cookie',cookie)
            self.end_headers();self.wfile.write(raw)
        def session(self):
            c=SimpleCookie()
            try:c.load(self.headers.get('Cookie',''))
            except Exception:return None
            return auth.session(c['session'].value) if 'session' in c else None
        def do_GET(self):
            p=urllib.parse.urlsplit(self.path);args=urllib.parse.parse_qs(p.query,keep_blank_values=True)
            if legacy:
                if p.path=='/':
                    self.reply(200,'<html lang="pt-BR"><meta charset="utf-8"><title>SQLi | laboratório</title><h1>Comparação SQL Injection</h1><p>Banco fictício descartável, acesso somente local.</p><form action="/legacy/search"><label>Busca vulnerável <input name="q" value="p001"></label><button>Consultar</button></form><form action="/fixed/search"><label>Busca parametrizada <input name="q" value="p001"></label><button>Consultar</button></form></html>','text/html');return
                q=args.get('q',[''])[0]
                if p.path in ['/legacy/search','/fixed/search']:
                    safe=p.path.startswith('/fixed');suspect=bool(re.search(r"(?i)(--|union|\bor\b|;)",q))
                    if suspect:audit('web','sqli_detectada',version='corrigida' if safe else 'legada',payload=q)
                    try:
                        rows=search(q,safe);audit('database','consulta_historico',version='corrigida' if safe else 'legada',rows=len(rows))
                        self.reply(200,{'rows':rows});return
                    except (sqlite3.Error,ValueError):self.reply(400,{'error':'Consulta inválida.'});return
                self.reply(404,{'error':'Recurso não encontrado.'});return
            if p.path=='/':self.reply(200,display_page(),'text/html');return
            if p.path=='/app.js':self.reply(200,JS,'application/javascript');return
            s=self.session()
            if not s:self.reply(401,{'error':'Entre com senha e autenticador.'});return
            if p.path=='/api/status':
                ev={name:read_json(ROOT/'evidence'/name,{}) for name in ['security.json','ai.json','phishing.json']}
                tunnel=None
                if linux_mode:
                    try:
                        from pathlib import Path
                        tunnel=bool(int(Path('/sys/class/net/wg0/flags').read_text().strip(),16)&1)
                    except (OSError,ValueError):tunnel=False
                scope=('Piloto UBS Linux | Mosquitto | '+('VPN ligada' if tunnel else 'VPN desligada: operação local')) if linux_mode else 'Cinco bordas lógicas no host local; ensaio nativo em loopback.'
                self.reply(200,dict(scope=scope,tunnel_up=tunnel,utc=utc(),edges=[e.state() for e in edges] if edges else read_json(RUNTIME/'demo-state.json',[]),evidence=ev));return
            if p.path=='/api/history':
                try:self.reply(200,{'rows':search(args.get('q',[''])[0])})
                except (sqlite3.Error,ValueError):self.reply(400,{'error':'Consulta inválida.'})
                return
            self.reply(404,{'error':'Recurso não encontrado.'})
        def do_POST(self):
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=8192:raise ValueError()
                body=json.loads(self.rfile.read(n))
                if not isinstance(body,dict):raise ValueError()
            except (ValueError,TypeError):self.reply(400,{'error':'Requisição inválida.'});return
            if legacy:
                if self.path=='/legacy/schedule' and isinstance(body.get('pump'),str) and len(body['pump'])<500:
                    try:legacy_schedule(body['pump']);audit('database','agendamento_alterado_lab',source='SQL concatenado');self.reply(200,{'status':'alterado no banco descartável'})
                    except sqlite3.Error:self.reply(400,{'error':'Comando inválido.'})
                    return
                self.reply(404,{'error':'Recurso não encontrado.'});return
            if self.path=='/api/login':
                if not all(isinstance(body.get(k),str) and len(body[k])<=100 for k in ['username','password','otp']):self.reply(400,{'error':'Requisição inválida.'});return
                result=auth.login(body['username'],body['password'],body['otp'])
                if not result:self.reply(401,{'error':'Credenciais inválidas ou limite de tentativas atingido.'});return
                token,s=result;self.reply(200,dict(role=s['role'],csrf=s['csrf']),cookie='session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=900');return
            s=self.session()
            if not s:self.reply(401,{'error':'Autenticação necessária.'});return
            if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):self.reply(403,{'error':'Requisição não autorizada.'});return
            if self.path=='/api/command':
                if s['role'] not in ['operador','tecnico','coordenacao']:
                    audit('web','atuador_negado',role=s['role'],reason='perfil');self.reply(403,{'error':'Perfil não autorizado.'});return
                if body.get('action')!='parar_bomba':self.reply(400,{'error':'Ação inválida.'});return
                key=str(uuid.uuid4());pending=read_json(RUNTIME/'approvals.json',{})
                pending[key]=dict(action='parar_bomba',status='pendente',requester=s['role'],utc=utc());save_json(RUNTIME/'approvals.json',pending)
                audit('web','alto_impacto_pendente',request_id=key,role=s['role']);self.reply(202,{'id':key,'status':'pendente de aprovação humana'});return
            if self.path=='/api/approve':
                if s['role']!='coordenacao':
                    audit('web','atuador_negado',role=s['role'],reason='aprovação');self.reply(403,{'error':'Apenas coordenação pode aprovar.'});return
                pending=read_json(RUNTIME/'approvals.json',{});key=body.get('id','')
                if key not in pending or pending[key]['status']!='pendente':self.reply(409,{'error':'Solicitação indisponível.'});return
                pending[key]['status']='aprovado';save_json(RUNTIME/'approvals.json',pending)
                save_json(RUNTIME/'actuators.json',{'pump_running':False,'approved_request':key,'utc':utc()})
                audit('web','atuador_aprovado',request_id=key,role=s['role'],physical_actuator=False)
                self.reply(200,{'status':'Aprovado. Estado lógico da bomba parado; sem atuador físico.'});return
            self.reply(404,{'error':'Recurso não encontrado.'})
    return Handler

def start_server(port,edges=None,legacy=False):
    init_db();server=ThreadingHTTPServer(('127.0.0.1',port),make_handler(edges,legacy))
    threading.Thread(target=server.serve_forever,daemon=True).start();return server

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--vulnerable',action='store_true');a=parser.parse_args()
    server=start_server(8081 if a.vulnerable else 8080,legacy=a.vulnerable)
    print('Painel local em http://127.0.0.1:'+str(server.server_port),flush=True)
    try:
        while True:time.sleep(1)
    finally:server.shutdown()
