import json,time
import paho.mqtt.client as mqtt
from .common import KINDS
from .pki import client_context

def main():
    count=0
    while True:
        for kind in KINDS:
            name='ubs-'+kind
            client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=name)
            client.tls_set_context(client_context(name))
            try:
                client.connect('broker-ubs',8883);client.loop_start()
                for _ in range(30):
                    if client.is_connected():break
                    time.sleep(.1)
                value={'temperatura':12 if count%8==0 else 5,'nivel':60,'energia':75,'acesso':0}[kind]
                info=client.publish(f'sites/ubs/devices/{name}/telemetry',json.dumps({'value':value}),qos=1)
                info.wait_for_publish(timeout=5)
            except (OSError,RuntimeError,ValueError):time.sleep(2)
            finally:client.disconnect();client.loop_stop()
        count+=1;time.sleep(5)

if __name__=='__main__':main()
