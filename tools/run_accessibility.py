"""Entrega as credenciais locais por stdin ao teste, sem gravar ou imprimir segredos."""
import argparse,json,subprocess,time,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--credentials',required=True,type=Path);p.add_argument('--browser');p.add_argument('--node',default='node');a=p.parse_args()
root=Path(__file__).resolve().parents[1]
users=json.loads(a.credentials.read_text(encoding='utf-8'))
env=os.environ.copy()
if a.browser:env['AURORA_BROWSER']=a.browser
result=subprocess.run([a.node,str(root/'tests/accessibility.cjs')],cwd=root,env=env,
    input=json.dumps(dict(user=users['auditor'],epoch=time.time())),text=True)
raise SystemExit(result.returncode)
