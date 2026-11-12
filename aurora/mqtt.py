"""Broker mínimo MQTT 3.1.1 didático: CONNECT, PUBLISH QoS0/1, PING e DISCONNECT.
Não substitui Mosquitto. Sem SUBSCRIBE/retained/will. Consumo local por callback.
Paho é utilizado como cliente independente nos testes de interoperabilidade.
"""
import json, socket, ssl, struct, threading
from .common import audit
from .pki import server_context, peer_identity, revoked

def recv_exact(sock, n):
    data = b''
    while len(data) < n:
        part = sock.recv(n-len(data))
        if not part: raise EOFError()
        data += part
    return data

def packet(sock):
    flag = recv_exact(sock,1)[0]; length = 0; factor = 1
    for _ in range(4):
        byte = recv_exact(sock,1)[0]; length += (byte & 127)*factor
        if byte < 128: break
        factor *= 128
    else: raise ValueError('MQTT malformed length')
    if length > 16384: raise ValueError('MQTT packet too large')
    return flag, recv_exact(sock,length)

class Broker:
    def __init__(self, site, port, receive):
        self.site, self.port, self.receive = site,port,receive
        self.ctx = server_context('broker-'+site); self.stop_event = threading.Event()
    def start(self):
        self.sock = socket.socket(); self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.sock.bind(('127.0.0.1',self.port)); self.sock.listen(32); self.sock.settimeout(.3)
        threading.Thread(target=self.run,daemon=True).start()
    def run(self):
        while not self.stop_event.is_set():
            try: raw,_ = self.sock.accept()
            except socket.timeout: continue
            except OSError: break
            threading.Thread(target=self.handle,args=(raw,),daemon=True).start()
    def handle(self, raw):
        raw.settimeout(5)
        try:
            with self.ctx.wrap_socket(raw,server_side=True) as sock:
                name,serial = peer_identity(sock)
                if revoked(serial):
                    audit('broker','certificado_bloqueado',site=self.site,device=name); return
                flag,body = packet(sock)
                if flag != 0x10 or body[:8] != b'\x00\x04MQTT\x04\x02':
                    # Paho can send clean-session only; other CONNECT features out of scope.
                    raise ValueError('CONNECT não suportado neste broker didático')
                sock.sendall(b'\x20\x02\x00\x00')
                while True:
                    flag,body = packet(sock)
                    if flag >> 4 == 3:
                        if revoked(serial):
                            audit('broker','certificado_bloqueado',device=name,site=self.site); return
                        n = struct.unpack('!H',body[:2])[0]; topic = body[2:2+n].decode()
                        qos = (flag >> 1) & 3; offset=2+n
                        if qos not in (0,1): raise ValueError('QoS não suportado')
                        pid = body[offset:offset+2] if qos else b''; offset += 2 if qos else 0
                        allowed = f'sites/{self.site}/devices/{name}/telemetry'
                        if topic != allowed or not name.startswith(self.site+'-'):
                            audit('broker','acl_negada',device=name,topic=topic,site=self.site,serial=serial); return
                        self.receive(name,json.loads(body[offset:]),len(body)+2)
                        if qos: sock.sendall(b'\x40\x02'+pid)
                    elif flag == 0xc0: sock.sendall(b'\xd0\x00')
                    elif flag == 0xe0: return
                    else: raise ValueError('Operação MQTT não suportada')
        except ssl.SSLError:
            audit('broker','certificado_invalido',site=self.site)
        except (EOFError,ConnectionError,TimeoutError,OSError,ValueError,json.JSONDecodeError): pass
        finally: raw.close()
    def close(self): self.stop_event.set(); self.sock.close()

def encode_packet(header,body):
    size=len(body); encoded=b''
    while True:
        b=size%128; size//=128; encoded+=bytes([b|128 if size else b])
        if not size: break
    return bytes([header])+encoded+body

def publish(site, name, value, port=8883, topic=None, context=None):
    from .pki import client_context
    ctx=context or client_context(name)
    with socket.create_connection(('127.0.0.1',port),timeout=3) as raw:
        with ctx.wrap_socket(raw,server_hostname='localhost') as sock:
            client_id=name.encode()
            sock.sendall(encode_packet(0x10,b'\x00\x04MQTT\x04\x02\x00\x05'+struct.pack('!H',len(client_id))+client_id))
            if packet(sock) != (0x20,b'\x00\x00'): raise ValueError('CONNACK')
            topic=(topic or f'sites/{site}/devices/{name}/telemetry').encode()
            body=struct.pack('!H',len(topic))+topic+b'\x00\x01'+json.dumps(value).encode()
            sock.sendall(encode_packet(0x32,body))
            if packet(sock) != (0x40,b'\x00\x01'): raise ValueError('PUBACK')
            sock.sendall(b'\xe0\x00')
