"""Testes MQTT5 contra o broker próprio no segmento IoT. Sem destinos externos."""
import json,time,sys
import paho.mqtt.client as mqtt
from aurora.pki import client_context

def attempt(identity,topic='tests/ubs/probe'):
    status={'connected':False,'ack_code':None,'error':None}
    c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='probe-'+str(time.monotonic_ns()),protocol=mqtt.MQTTv5)
    def connected(client,data,flags,reason,properties):status['connected']=not reason.is_failure
    def published(client,data,mid,reason,properties):status['ack_code']=reason.value
    c.on_connect=connected;c.on_publish=published
    c.tls_set_context(client_context(identity))
    try:
        c.connect('broker-ubs',8883,keepalive=5);c.loop_start()
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and not status['connected']:time.sleep(.05)
        if status['connected']:
            c.publish(topic,json.dumps({'laboratorio':'somente teste de autorização'}),qos=1)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline and status['ack_code'] is None:time.sleep(.05)
    except Exception as e:status['error']=type(e).__name__
    finally:c.disconnect();c.loop_stop()
    # MQTT5 também considera 0x10 sucesso: publicação aceita sem assinante desse tópico.
    status['accepted']=status['connected'] and status['ack_code'] in (0,16)
    return status

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'before'
    if mode=='before':
        tests={'valid':attempt('ubs-probe'),'without_certificate':attempt(None),'untrusted_CA':attempt('intruso'),
               'wrong_topic':attempt('ubs-probe','sites/ubs/devices/ubs-nivel/telemetry')}
        passed=tests['valid']['accepted'] and not tests['without_certificate']['accepted'] and not tests['untrusted_CA']['accepted'] and tests['wrong_topic']['ack_code']==135
    else:
        tests={'revoked_old_serial':attempt('ubs-probe-old'),'rotated_new_serial':attempt('ubs-probe')}
        passed=not tests['revoked_old_serial']['accepted'] and tests['rotated_new_serial']['accepted']
    print(json.dumps({'phase':mode,'passed':passed,'tests':tests,'protocol':'MQTT 5, QoS1, Mosquitto real'},ensure_ascii=True))
    raise SystemExit(not passed)
