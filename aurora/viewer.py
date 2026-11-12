"""Visualizador de demonstração: proxy fixo, publicado somente em loopback no host."""
import http.client,os,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

HOP={'connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','transfer-encoding','upgrade','host','content-length'}
class Proxy(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def relay(self):
        if urllib.parse.urlsplit(self.path).scheme or not self.path.startswith('/'):
            self.send_error(400);return
        n=int(self.headers.get('Content-Length','0'))
        if not 0<=n<=65536:self.send_error(413);return
        target=urllib.parse.urlsplit(os.environ['AURORA_UPSTREAM'])
        conn=http.client.HTTPConnection(target.hostname,target.port,timeout=8)
        try:
            headers={k:v for k,v in self.headers.items() if k.lower() not in HOP}
            conn.request(self.command,self.path,body=self.rfile.read(n) if n else None,headers=headers)
            response=conn.getresponse();body=response.read(1048576)
            self.send_response(response.status)
            for k,v in response.getheaders():
                if k.lower() not in HOP:self.send_header(k,v)
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        except OSError:self.send_error(502,'Borda indisponivel')
        finally:conn.close()
    do_GET=relay
    do_POST=relay
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',8088),Proxy).serve_forever()
