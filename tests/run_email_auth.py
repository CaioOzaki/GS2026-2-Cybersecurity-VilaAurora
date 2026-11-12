"""SPF real (pyspf), DKIM real e alinhamento DMARC estrito em DNS fictício offline."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import spf,dkim
ROOT=Path(__file__).resolve().parents[1]
def main():
    settings=json.loads((ROOT/'evidence/email-auth.json').read_text(encoding='utf-8'))
    domain=settings['domain'];zone={domain:settings['spf'],'estrangeiro.test':settings['spf']};queries=[]
    def dns(name,qtype,tcpfallback=True,timeout=30):
        host=str(name).rstrip('.').lower();queries.append(dict(name=host,type=qtype))
        return [((name,qtype),(zone[host].encode(),))] if qtype in ['TXT','SPF'] and host in zone else []
    original=spf.DNSLookup;spf.DNSLookup=dns
    try:
        approved=spf.check2('192.0.2.25','coordenacao@'+domain,'mail.'+domain)[0]
        forged=spf.check2('198.51.100.99','coordenacao@'+domain,'mail.'+domain)[0]
        foreign=spf.check2('192.0.2.25','remetente@estrangeiro.test','mail.estrangeiro.test')[0]
    finally:spf.DNSLookup=original
    message=(ROOT/'evidence/signed-message.eml').read_bytes()
    record=settings['dkim_txt'].encode();selector=(settings['dkim_selector']+'._domainkey.'+domain).encode()
    resolver=lambda name,timeout=5:record if name.rstrip(b'.')==selector else None
    valid=bool(dkim.verify(message,dnsfunc=resolver));tampered=bool(dkim.verify(message.replace(b'Conteudo',b'Alterado'),dnsfunc=resolver))
    policy=dict(part.strip().split('=',1) for part in settings['dmarc'].split(';') if '=' in part)
    assert policy['p']=='quarantine' and policy['adkim']=='s' and policy['aspf']=='s'
    def dmarc_result(header_from,envelope_from,spf_result,dkim_valid,dkim_domain):
        aligned_spf=spf_result=='pass' and header_from==envelope_from
        aligned_dkim=dkim_valid and header_from==dkim_domain
        return 'pass' if aligned_spf or aligned_dkim else policy['p']
    checks=[dict(name='SPF: IP autorizado',actual=approved,expected='pass'),dict(name='SPF: IP indevido',actual=forged,expected='fail'),
      dict(name='DKIM: mensagem íntegra',actual=valid,expected=True),dict(name='DKIM: corpo adulterado',actual=tampered,expected=False),
      dict(name='DMARC: SPF alinhado basta',actual=dmarc_result(domain,domain,approved,False,domain),expected='pass'),
      dict(name='DMARC: DKIM alinhado basta',actual=dmarc_result(domain,domain,forged,valid,domain),expected='pass'),
      dict(name='DMARC: ambas autenticações falham',actual=dmarc_result(domain,domain,forged,tampered,domain),expected='quarantine'),
      dict(name='DMARC: SPF válido de domínio não alinhado',actual=dmarc_result(domain,'estrangeiro.test',foreign,False,domain),expected='quarantine'),
      dict(name='DMARC: assinatura válida sem alinhamento ao From',actual=dmarc_result('outro.test',domain,approved,valid,domain),expected='quarantine')]
    for c in checks:c['passed']=c['actual']==c['expected']
    result=dict(scope='DNS fictício resolvido em memória; nenhum envio SMTP, DNS público ou pessoa real. DMARC avalia o alinhamento estrito configurado, não é um receptor SMTP completo.',
        libraries=dict(pyspf='2.0.14',dkimpy='1.1.8'),policy=settings['dmarc'],tests=checks,dns_queries=queries,passed=sum(c['passed'] for c in checks),total=len(checks))
    (ROOT/'evidence/email-policy-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],total=result['total']),ensure_ascii=True))
    if result['passed']!=result['total']:raise SystemExit(1)
if __name__=='__main__':main()
