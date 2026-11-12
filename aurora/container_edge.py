"""Adaptador Mosquitto para a mesma regra/fila local no piloto Linux UBS."""
import json,time,threading
import paho.mqtt.client as mqtt
from http.server import ThreadingHTTPServer
from .common import audit
from .pki import client_context
from .edge import Edge
from .web import make_handler,init_db
from .defense import SIEM

def main():
    edge=Edge('ubs',8883)
    threading.Thread(target=edge.loop,daemon=True).start()
    def connected(c,u,f,reason,props):c.subscribe('sites/ubs/devices/+/telemetry',qos=1)
    def message(c,u,msg):
        try:edge.receive(msg.topic.split('/')[3],json.loads(msg.payload),len(msg.payload)+len(msg.topic))
        except Exception:audit('edge','mensagem_invalida_mosquitto')
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='edge-ubs')
    client.tls_set_context(client_context('edge-ubs'));client.on_connect=connected;client.on_message=message
    for _ in range(30):
        try:client.connect('localhost',8883);break
        except OSError:time.sleep(1)
    client.loop_start();init_db();siem=SIEM();siem.start()
    ThreadingHTTPServer(('0.0.0.0',8080),make_handler([edge])).serve_forever()

if __name__=='__main__':main()
