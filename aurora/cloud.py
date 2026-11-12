import json, sqlite3, threading, os
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from .pki import server_context,peer_identity,revoked
from .common import RUNTIME,SITES,audit

class Server(ThreadingHTTPServer):
    daemon_threads=True; allow_reuse_address=True
    def get_request(self):
        raw,addr=self.socket.accept();raw.settimeout(5)
        try:return self.tls.wrap_socket(raw,server_side=True),addr
        except Exception:
            audit('cloud','certificado_invalido');raw.close();raise

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        name,serial=peer_identity(self.connection)
        if self.path!='/ingest' or revoked(serial) or name not in ['edge-'+s for s in SITES]:
            self.send_error(403);return
        size=int(self.headers.get('Content-Length','0'))
        if not 0<size<=300000:self.send_error(413);return
        try:
            rows=json.loads(self.rfile.read(size));site=name.removeprefix('edge-')
            if not isinstance(rows,list) or len(rows)>100:raise ValueError()
            if any(r['site']!=site or r['device']!=site+'-'+r['kind'] for r in rows):raise ValueError()
            with sqlite3.connect(RUNTIME/'cloud.db',timeout=10) as db:
                db.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,site TEXT,payload TEXT)')
                db.executemany('INSERT OR IGNORE INTO events VALUES(?,?,?)',[(r['id'],site,json.dumps(r)) for r in rows])
            result=json.dumps({'accepted':[r['id'] for r in rows]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(result)));self.end_headers();self.wfile.write(result)
            audit('cloud','lote_reconciliado',site=site,received=len(rows))
        except (KeyError,ValueError,TypeError):self.send_error(400)

def main():
    s=Server((os.environ.get('AURORA_BIND','127.0.0.1'),int(os.environ.get('AURORA_CLOUD_PORT','9443'))),Handler);s.tls=server_context('cloud')
    audit('os','servico_nuvem_iniciado');s.serve_forever(poll_interval=.3)

if __name__=='__main__':main()
