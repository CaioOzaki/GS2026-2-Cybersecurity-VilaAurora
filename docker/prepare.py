"""Gera segredos privados por função, localmente, sem versioná-los."""
import base64,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization
from aurora.pki import setup,PKI
from aurora.common import RUNTIME

def keypair():
    k=X25519PrivateKey.generate()
    a=base64.b64encode(k.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())).decode()
    b=base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
    return a,b

def main():
    setup();out=RUNTIME/'docker'
    from aurora.pki import issue
    if not (PKI/'ubs-probe.crt').exists():issue('ubs-probe')
    for role,names in [('cloud',['cloud']),('edge',['broker-ubs','edge-ubs']),('field',['ubs-temperatura','ubs-nivel','ubs-energia','ubs-acesso']),('probe',['ubs-probe','intruso'])]:
        d=out/role/'pki';d.mkdir(parents=True,exist_ok=True,mode=0o700)
        shutil.copy2(PKI/'ca.crt',d/'ca.crt')
        shutil.copy2(PKI/'ca.crl',d/'ca.crl')
        for name in names:
            for suffix in ['.crt','.key']:shutil.copy2(PKI/(name+suffix),d/(name+suffix))
        (d/'revoked.json').write_text('[]')
    ck,cp=keypair();ek,ep=keypair()
    (out/'cloud/wg0.conf').write_text(f'[Interface]\nAddress = 10.77.0.1/24\nListenPort = 51820\nPrivateKey = {ck}\n\n[Peer]\nPublicKey = {ep}\nAllowedIPs = 10.77.0.2/32\nEndpoint = 172.29.0.3:51820\nPersistentKeepalive = 15\n')
    (out/'edge/wg0.conf').write_text(f'[Interface]\nAddress = 10.77.0.2/24\nListenPort = 51820\nPrivateKey = {ek}\n\n[Peer]\nPublicKey = {cp}\nAllowedIPs = 10.77.0.1/32\nEndpoint = 172.29.0.2:51820\nPersistentKeepalive = 15\n')
    (out/'edge/mosquitto.conf').write_text('listener 8883 0.0.0.0\nprotocol mqtt\nallow_anonymous false\nrequire_certificate true\nuse_identity_as_username true\ncafile /state/pki/ca.crt\ncrlfile /state/pki/ca.crl\ncertfile /state/pki/broker-ubs.crt\nkeyfile /state/pki/broker-ubs.key\nacl_file /state/acl\nuser aurora\nlog_dest stdout\n')
    acl='user edge-ubs\ntopic read sites/ubs/devices/+/telemetry\nuser ubs-probe\ntopic write tests/ubs/probe\n'
    for kind in ['temperatura','nivel','energia','acesso']:
        name='ubs-'+kind;acl+=f'user {name}\ntopic write sites/ubs/devices/{name}/telemetry\n'
    (out/'edge/acl').write_text(acl)
    print('Configuração privada Docker gerada em .runtime/docker. Não publicar esta pasta.')

if __name__=='__main__':main()
