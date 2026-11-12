import ipaddress, ssl
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from .common import RUNTIME, SITES, KINDS, save_json, read_json, audit

PKI = RUNTIME / 'pki'

def _key(): return rsa.generate_private_key(public_exponent=65537, key_size=2048)

def _store(name, key, cert):
    PKI.mkdir(exist_ok=True)
    (PKI / (name+'.key')).write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (PKI / (name+'.crt')).write_bytes(cert.public_bytes(serialization.Encoding.PEM))

def issue(name, server=False, ca_name='ca'):
    key = _key()
    ca_key = serialization.load_pem_private_key((PKI/(ca_name+'.key')).read_bytes(), None)
    ca = x509.load_pem_x509_certificate((PKI/(ca_name+'.crt')).read_bytes())
    now = datetime.now(timezone.utc)
    builder = x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
    builder = builder.issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
    builder = builder.not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=90))
    builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
    builder = builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]), False)
    if server:
        builder = builder.add_extension(x509.SubjectAlternativeName([
            x509.DNSName('localhost'), x509.DNSName(name), x509.DNSName('cloud'),
            x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), False)
    cert = builder.sign(ca_key, hashes.SHA256()); _store(name, key, cert)
    return format(cert.serial_number, 'x')

def create_ca(name='ca'):
    key = _key(); now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Vila Aurora laboratório '+name)])
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False), True)
        .sign(key, hashes.SHA256()))
    _store(name,key,cert)

def setup():
    if (PKI/'ca.crt').exists(): return
    create_ca(); create_ca('rogue-ca')
    issue('cloud', True)
    identities = {}
    for site in SITES:
        issue('broker-'+site, True)
        identities['edge-'+site] = issue('edge-'+site)
        for kind in KINDS:
            name = site+'-'+kind; identities[name] = issue(name)
    identities['teste-revogacao'] = issue('teste-revogacao')
    issue('intruso', ca_name='rogue-ca')
    save_json(PKI/'identities.json', identities)
    save_json(PKI/'revoked.json', [])

def server_context(name):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(PKI/(name+'.crt'), PKI/(name+'.key')); ctx.load_verify_locations(PKI/'ca.crt')
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx

def client_context(name=None):
    ctx = ssl.create_default_context(cafile=str(PKI/'ca.crt')); ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    if name: ctx.load_cert_chain(PKI/(name+'.crt'), PKI/(name+'.key'))
    return ctx

def peer_identity(sock):
    cert = x509.load_der_x509_certificate(sock.getpeercert(binary_form=True))
    name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    return name, format(cert.serial_number, 'x')

def revoked(serial): return serial in read_json(PKI/'revoked.json', [])

def revoke(serial):
    values = read_json(PKI/'revoked.json', [])
    if serial not in values: values.append(serial)
    save_json(PKI/'revoked.json', values)
    audit('pki','certificado_revogado', serial=serial)

if __name__ == '__main__':
    setup(); print('PKI criada localmente. Chaves privadas em .runtime; nunca publicar.')
