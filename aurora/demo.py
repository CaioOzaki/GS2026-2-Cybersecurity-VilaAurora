import argparse,json,subprocess,sys,time,threading
from .common import ROOT,RUNTIME,SITES,KINDS,save_json
from .pki import setup
from .edge import start_edges
from .mqtt import publish
from .web import start_server
from .defense import SIEM

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--vulnerable',action='store_true');args=parser.parse_args()
    setup();edges=start_edges();web=start_server(8080,edges)
    cloud=subprocess.Popen([sys.executable,'-m','aurora.cloud'],cwd=ROOT)
    legacy=start_server(8081,legacy=True) if args.vulnerable else None
    siem=SIEM();siem.start();count=0
    print('Painel: http://127.0.0.1:8080 | credenciais privadas: .runtime/credentials.json',flush=True)
    print('Ctrl+C encerra. Nunca envie .runtime ao GitHub.',flush=True)
    try:
        while True:
            for edge in edges:
                for kind in KINDS:
                    value={'temperatura':12 if count%8==0 else 5,'nivel':60,'energia':75,'acesso':0}[kind]
                    publish(edge.site,edge.site+'-'+kind,{'value':value},edge.port)
            save_json(RUNTIME/'demo-state.json',[e.state() for e in edges]);count+=1;time.sleep(5)
    except KeyboardInterrupt:pass
    finally:
        siem.stop.set();web.shutdown()
        if legacy:legacy.shutdown()
        for e in edges:e.close()
        cloud.terminate();cloud.wait(timeout=10)

if __name__=='__main__':main()
