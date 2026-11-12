"""Operação da estação emissora: revogar probe e emitir novo serial do mesmo dispositivo."""
from pathlib import Path
import sys,json,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aurora.pki import PKI,revoke,issue
from aurora.common import RUNTIME,ROOT
from cryptography import x509

old=x509.load_pem_x509_certificate((PKI/'ubs-probe.crt').read_bytes())
old_serial=format(old.serial_number,'x')
target=RUNTIME/'docker/probe/pki'
for suffix in ['.crt','.key']:shutil.copy2(PKI/('ubs-probe'+suffix),target/('ubs-probe-old'+suffix))
revoke(old_serial);new_serial=issue('ubs-probe')
for suffix in ['.crt','.key']:shutil.copy2(PKI/('ubs-probe'+suffix),target/('ubs-probe'+suffix))
shutil.copy2(PKI/'ca.crl',RUNTIME/'docker/edge/pki/ca.crl')
result={'device':'ubs-probe','old_serial':old_serial,'new_serial':new_serial,'CRL_signed_by':'CA do laboratório; chave privada permanece na estação emissora'}
p=ROOT/'evidence/docker/certificate-rotation.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('CRL atualizada. Reiniciar o broker para recarregar contexto TLS e testar o serial antigo e o novo.')
