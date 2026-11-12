import hashlib, json, os, threading, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('AURORA_RUNTIME', ROOT / '.runtime')).resolve()
RUNTIME.mkdir(parents=True, exist_ok=True,mode=0o700)
SITES = ['centro', 'escola', 'ubs', 'horta', 'abrigo']
KINDS = ['temperatura', 'nivel', 'energia', 'acesso']
LOCK = threading.RLock()

@contextmanager
def process_lock():
    """Serializa logs de múltiplos processos Windows e Linux."""
    path=RUNTIME/'audit.lock'
    with path.open('a+b') as f:
        if path.stat().st_size==0: f.write(b'0'); f.flush()
        f.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX)
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f,fcntl.LOCK_UN)

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

def save_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)

def audit(component, action, **fields):
    """Centralização didática no host; cadeia detecta alteração se ancorada externamente."""
    with LOCK,process_lock():
        path = RUNTIME / 'central.jsonl'
        previous = RUNTIME / 'last_hash.txt'
        prev = previous.read_text() if previous.exists() else '0' * 64
        row = dict(utc=utc(), monotonic_ns=time.monotonic_ns(), component=component,
                   action=action, previous_sha256=prev, **fields)
        raw = json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        row['sha256'] = hashlib.sha256(raw.encode()).hexdigest()
        with path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
        previous.write_text(row['sha256'])
        return row

def read_json(path, default=None):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError): return default
