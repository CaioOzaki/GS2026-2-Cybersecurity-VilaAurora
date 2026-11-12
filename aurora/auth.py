import base64,hashlib,hmac,secrets,struct,time,threading
from .common import RUNTIME,read_json,save_json,audit

def totp(secret,when=None):
    counter=int((time.time() if when is None else when)//30)
    raw=hmac.new(base64.b32decode(secret),struct.pack('!Q',counter),hashlib.sha1).digest()
    off=raw[-1]&15
    return str((struct.unpack('!I',raw[off:off+4])[0]&0x7fffffff)%1000000).zfill(6)

def setup():
    path=RUNTIME/'credentials.json'
    if path.exists():return
    users={}; private={}
    for role in ['operador','tecnico','coordenacao','auditor']:
        password=secrets.token_urlsafe(18);salt=secrets.token_hex(16)
        secret=base64.b32encode(secrets.token_bytes(20)).decode()
        users[role]=dict(role=role,salt=salt,hash=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex(),totp=secret)
        private[role]=dict(password=password,totp_secret=secret)
    save_json(RUNTIME/'users.json',users);save_json(path,private)

class Auth:
    def __init__(self):
        setup();self.users=read_json(RUNTIME/'users.json');self.sessions={};self.failures={};self.used={};self.lock=threading.Lock()
    def login(self,username,password,otp):
        with self.lock:
            now=time.time();self.failures.setdefault(username,[])
            self.failures[username]=[t for t in self.failures[username] if t>now-300]
            if len(self.failures[username])>=5:return None
            u=self.users.get(username)
            good=False
            if u and isinstance(password,str) and isinstance(otp,str):
                digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(u['salt']),600000).hex()
                good=hmac.compare_digest(u['hash'],digest) and any(hmac.compare_digest(totp(u['totp'],now+i*30),otp) for i in [-1,0,1])
                good=good and (username,otp) not in self.used
            if not good:
                self.failures[username].append(now);audit('web','login_negado',actor=username if username in self.users else 'desconhecido');return None
            self.used[(username,otp)]=now
            self.used={k:v for k,v in self.used.items() if v>now-120}
            token=secrets.token_urlsafe(32);key=hashlib.sha256(token.encode()).hexdigest()
            self.sessions[key]=dict(role=u['role'],expires=now+900,csrf=secrets.token_urlsafe(24))
            self.failures[username]=[];audit('web','login_mfa_aceito',actor=username)
            return token,self.sessions[key]
    def session(self,token):
        key=hashlib.sha256(token.encode()).hexdigest();s=self.sessions.get(key)
        if s and s['expires']>time.time():return s
        self.sessions.pop(key,None);return None
