import json,time,threading
from datetime import datetime
from .common import RUNTIME,read_json,save_json,audit

RULES={
 'replay_vpn_login':('D01','Login VPN fora do perfil - evento sintético'),
 'sqli_detectada':('D02','Padrão de SQL Injection no laboratório'),
 'certificado_invalido':('D03','Falha de autenticação mTLS'),
 'atuador_negado':('D04','Comando de atuador fora do perfil'),
}

class SIEM:
    """Correlacionador didático; não se apresenta como Wazuh."""
    def __init__(self):self.stop=threading.Event();self.offset=0;self.lock=threading.Lock()
    def start(self):threading.Thread(target=self.loop,daemon=True).start()
    def poll(self):
        path=RUNTIME/'central.jsonl'
        if not path.exists():return
        with self.lock,path.open(encoding='utf-8') as f:
            f.seek(self.offset);lines=f.readlines();self.offset=f.tell()
            alerts=read_json(RUNTIME/'siem-alerts.json',[])
            for line in lines:
                try:row=json.loads(line)
                except json.JSONDecodeError:continue
                if row['action']=='acl_negada' and row.get('serial'):
                    # Baixo impacto: revoga somente a identidade autenticada que violou ACL.
                    from .pki import revoke
                    revoke(row['serial'])
                    audit('soar','isolamento_logico_sensor',device=row['device'],serial=row['serial'],physical_actuator=False)
                if row['action'] not in RULES:continue
                rid,title=RULES[row['action']]
                d=audit('siem','deteccao',rule=rid,event_hash=row['sha256'],source_utc=row['utc'])
                dt=(datetime.fromisoformat(d['utc'])-datetime.fromisoformat(row['utc'])).total_seconds()
                alerts.append(dict(rule=rid,title=title,event=row['sha256'],source_utc=row['utc'],detected_utc=d['utc'],mttd_seconds=dt,
                    origin='synthetic_replay' if rid=='D01' else 'local_test'))
            save_json(RUNTIME/'siem-alerts.json',alerts)
    def loop(self):
        while not self.stop.is_set():
            self.poll();self.stop.wait(.25)
