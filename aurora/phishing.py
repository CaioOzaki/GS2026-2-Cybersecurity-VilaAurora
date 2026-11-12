"""Campanha somente em loopback; cinco agentes automáticos fictícios, não pessoas."""
import base64,json,threading,urllib.request
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import dkim
from .common import ROOT,RUNTIME,save_json,audit

def run():
    events=[];allowed={f'voluntario{i:03}' for i in range(1,6)}
    class H(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            parts=self.path.strip('/').split('/')
            if len(parts)!=3 or parts[0]!='campanha' or parts[1] not in ['abertura','clique','submissao','reporte'] or parts[2] not in allowed:
                self.send_error(404);return
            events.append((parts[1],parts[2]));audit('phishing','acao_campanha',event=parts[1],account=parts[2]+'@example.test',automated=True)
            self.send_response(200);self.send_header('Content-Type','text/plain; charset=utf-8');self.end_headers();self.wfile.write(b'LABORATORIO - evento ficticio registrado. Nenhuma senha coletada.')
    server=ThreadingHTTPServer(('127.0.0.1',8091),H);threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        for event,n in [('abertura',4),('clique',3),('submissao',2),('reporte',2)]:
            for i in range(1,n+1):
                with urllib.request.urlopen(f'http://127.0.0.1:8091/campanha/{event}/voluntario{i:03}') as response:response.read()
    finally:server.shutdown();server.server_close()
    counts={event:len({i for e,i in events if e==event}) for event in ['abertura','clique','submissao','reporte']}
    result=dict(accounts=5,campaign_mode='Agentes HTTP fictícios; sem envio SMTP ou participação humana.',counts=counts,
        rates_percent={k:v/5*100 for k,v in counts.items()},passwords_collected=0,
        limitation='Valida instrumentação; não mede conscientização de voluntários reais.')
    save_json(ROOT/'evidence/phishing.json',result)
    message=b'From: coordenacao@vila-aurora.test\r\nTo: voluntario001@example.test\r\nSubject: [LABORATORIO] Teste de assinatura\r\nDate: Wed, 11 Nov 2026 12:00:00 +0000\r\n\r\nConteudo sintetico do laboratorio Vila Aurora.\r\n'
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.TraditionalOpenSSL,serialization.NoEncryption())
    (RUNTIME/'dkim.key').write_bytes(pem)
    pub=base64.b64encode(key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
    record=('v=DKIM1; k=rsa; p='+pub).encode()
    sig=dkim.sign(message,b'lab2026',b'vila-aurora.test',pem,include_headers=[b'from',b'to',b'subject',b'date'])
    signed=sig+message
    resolver=lambda name,timeout=5:record if name.rstrip(b'.')==b'lab2026._domainkey.vila-aurora.test' else None
    good=dkim.verify(signed,dnsfunc=resolver);bad=dkim.verify(signed.replace(b'Conteudo',b'Alterado'),dnsfunc=resolver)
    dns=dict(domain='vila-aurora.test',spf='v=spf1 ip4:192.0.2.25 -all',
        dkim_selector='lab2026',dkim_txt=record.decode(),dmarc='v=DMARC1; p=quarantine; adkim=s; aspf=s; pct=100',
        dkim_signature_valid=bool(good),tampered_message_valid=bool(bad),
        dns_publication='Zona de laboratório offline; .test não é domínio público.',
        spf_check_scope='Registro documentado; sem avaliador SPF completo ou entrega de e-mail.',
        dmarc_check_scope='Política e alinhamento especificados; sem receptor SMTP/relatórios DMARC reais.')
    assert good and not bad
    save_json(ROOT/'evidence/email-auth.json',dns)
    (ROOT/'evidence/signed-message.eml').write_bytes(signed)
    (ROOT/'evidence/phishing-template.eml').write_text('From: prefeitura@municipio.example.test\nTo: voluntario001@example.test\nSubject: [SIMULACAO AUTORIZADA - CONTAS FICTICIAS] Atualizacao urgente\n\nMensagem de laboratorio. Verifique por outro canal antes de agir.\nhttp://127.0.0.1:8091/campanha/clique/voluntario001\n',encoding='utf-8')
    return result,dns

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=True))
