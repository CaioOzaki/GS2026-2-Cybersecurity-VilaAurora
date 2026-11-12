import json, sqlite3, ssl, threading, uuid, urllib.request, os
from .common import RUNTIME, SITES, KINDS, audit, utc
from .mqtt import Broker
from .pki import client_context

class Edge:
    def __init__(self,site,port):
        self.site=site; self.port=port; self.lock=threading.RLock(); self.stop=threading.Event()
        self.db=sqlite3.connect(RUNTIME/(site+'.db'),check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL);'
          'CREATE TABLE IF NOT EXISTS readings(id TEXT PRIMARY KEY,payload TEXT NOT NULL);')
        self.broker=Broker(site,port,self.receive); self.ctx=client_context('edge-'+site)
        self.last={}; self.alerts=[]; self.bytes_in=0; self.bytes_out=0; self.sync_ok=0; self.sync_errors=0
    def receive(self,device,data,wirebytes):
        kind=device[len(self.site)+1:]
        if kind not in KINDS or set(data) != {'value'} or isinstance(data['value'],bool): raise ValueError('Entrada inválida')
        value=float(data['value'])
        limits={'temperatura':(-30,60),'nivel':(0,100),'energia':(0,100),'acesso':(0,1)}
        lo,hi=limits[kind]
        if not lo<=value<=hi: raise ValueError('Valor fora da faixa')
        event=dict(id=str(uuid.uuid4()),site=self.site,device=device,kind=kind,value=value,utc=utc())
        payload=json.dumps(event)
        with self.lock:
            self.db.execute('INSERT INTO readings VALUES(?,?)',(event['id'],payload))
            self.db.execute('INSERT INTO outbox VALUES(?,?)',(event['id'],payload)); self.db.commit()
            self.last[kind]=value; self.bytes_in+=wirebytes
            alarm = (kind=='temperatura' and not 2<=value<=8) or (kind=='nivel' and value<15) or (kind=='energia' and value<20)
            if alarm:
                detection=audit('edge','alarme_local',site=self.site,kind=kind,value=value,source_utc=event['utc'])
                self.alerts.append(detection); self.alerts=self.alerts[-30:]
        audit('device','telemetria_aceita',site=self.site,device=device,event_id=event['id'])
    def start(self):
        self.broker.start(); threading.Thread(target=self.loop,daemon=True).start()
    def loop(self):
        while not self.stop.is_set():
            self.sync_once(); self.stop.wait(2)
    def sync_once(self):
        with self.lock: rows=self.db.execute('SELECT id,payload FROM outbox ORDER BY rowid LIMIT 100').fetchall()
        if not rows:return
        body=json.dumps([json.loads(r[1]) for r in rows]).encode()
        req=urllib.request.Request(os.environ.get('AURORA_CLOUD','https://localhost:9443/ingest'),data=body,
            headers={'Content-Type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,context=self.ctx,timeout=2) as r: ack=json.load(r)
            accepted=set(ack['accepted'])
            with self.lock:
                self.db.executemany('DELETE FROM outbox WHERE id=?',[(i,) for i,_ in rows if i in accepted]); self.db.commit()
                self.sync_ok+=1; self.bytes_out+=len(body)
        except (OSError,ValueError,KeyError): self.sync_errors+=1
    def state(self):
        with self.lock:
            return dict(site=self.site,readings=self.db.execute('SELECT count(*) FROM readings').fetchone()[0],
                pending=self.db.execute('SELECT count(*) FROM outbox').fetchone()[0],last=self.last,
                alerts=len(self.alerts),bytes_mqtt_payload=self.bytes_in,bytes_https_payload=self.bytes_out,
                sync_batches_ok=self.sync_ok,sync_errors=self.sync_errors)
    def close(self): self.stop.set(); self.broker.close()

def start_edges():
    edges=[Edge(site,8883+i) for i,site in enumerate(SITES)]
    for e in edges:e.start()
    return edges
