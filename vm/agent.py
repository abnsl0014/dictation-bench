"""Test-only remote agent for a GitHub-hosted Windows runner (dictation app benchmark).

Polls origin/main for command files vm/cmd/NNNN.(ps1|py|enc) and runs each once,
in name order:
  .ps1  PowerShell script
  .py   Python script (helpers in vm/lib.py)
  .enc  secrets encrypted to this runner's RSA key (out/pubkey.pem); decrypted to
        a file outside the repo, never pushed
A file vm/cmd/STOP ends the run.

This repository is public, so results are never pushed in plain text. Commands
write into a private folder on the runner (WISPR_VM_OUT); after each command the
agent encrypts every file in it to vm/outkey.pem (RSA-OAEP-SHA256 + AES-256-GCM)
and pushes only the .enc copies to the orphan branch `results`. Only the holder of
the matching private key can read them. out/pubkey.pem (a public key) and
out/status.txt (start/stop times) are the only plain files.
"""
import base64, json, os, subprocess, sys, time, traceback
from pathlib import Path

CTRL = 'main'
RES = 'results'
ROOT = Path(__file__).resolve().parent.parent
TMP = Path(os.environ.get('RUNNER_TEMP', 'C:/t'))
WORK = TMP / 'vmres'          # git repo of the results branch (only .enc + public files)
PLAIN = TMP / 'vmplain'       # private, never pushed
SECRETS = TMP / 'secrets.json'
OUTKEY = ROOT / 'vm' / 'outkey.pem'
DEADLINE = time.time() + 320 * 60


def sh(args, cwd=None, check=False, timeout=120):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
    if check and p.returncode:
        raise RuntimeError(f'{args}: {p.returncode}\n{p.stdout}\n{p.stderr}')
    return p


def setup_results():
    WORK.mkdir(parents=True, exist_ok=True)
    PLAIN.mkdir(parents=True, exist_ok=True)
    sh(['git', 'init', '-q', '-b', RES], cwd=WORK, check=True)
    url = sh(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, check=True).stdout.strip()
    sh(['git', 'remote', 'add', 'origin', url], cwd=WORK)
    # The checkout action stores the token as an extraheader on the workspace repo.
    hdr = sh(['git', 'config', '--get', 'http.https://github.com/.extraheader'], cwd=ROOT).stdout.strip()
    if hdr:
        sh(['git', 'config', 'http.https://github.com/.extraheader', hdr], cwd=WORK, check=True)
    sh(['git', 'config', 'user.name', 'bench-vm'], cwd=WORK)
    sh(['git', 'config', 'user.email', 'bench-vm@users.noreply.github.com'], cwd=WORK)
    (WORK / 'out').mkdir(exist_ok=True)


def seal(data):
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    pub = serialization.load_pem_public_key(OUTKEY.read_bytes())
    k = AESGCM.generate_key(bit_length=256)
    n = os.urandom(12)
    c = AESGCM(k).encrypt(n, data, None)
    ek = pub.encrypt(k, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    b = lambda x: base64.b64encode(x).decode()
    return json.dumps({'k': b(ek), 'n': b(n), 'c': b(c)})


def sync_sealed():
    """Encrypt every private result file into the results repo (overwriting)."""
    for f in PLAIN.rglob('*'):
        if f.is_file():
            dst = WORK / 'out' / (f.relative_to(PLAIN).as_posix().replace('/', '__') + '.enc')
            dst.write_text(seal(f.read_bytes()), encoding='utf-8')


def push_results(msg):
    sync_sealed()
    sh(['git', 'add', '-A'], cwd=WORK)
    sh(['git', 'commit', '-q', '-m', msg], cwd=WORK)
    for i in range(5):
        p = sh(['git', 'push', '-q', '-f', 'origin', f'HEAD:{RES}'], cwd=WORK, timeout=180)
        if p.returncode == 0:
            return
        time.sleep(3 * (i + 1))


def screenshot(path):
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        w, h = img.size
        if w > 1600:
            img = img.resize((1600, int(h * 1600 / w)))
        img.save(path, optimize=True)
        return f'{w}x{h}'
    except Exception as e:  # no desktop yet, etc.
        return f'screenshot failed: {e}'


def make_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    (WORK / 'out' / 'pubkey.pem').write_bytes(pub)
    return key


def decrypt(key, blob):
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    d = json.loads(blob)
    aes = key.decrypt(base64.b64decode(d['k']), padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return AESGCM(aes).decrypt(base64.b64decode(d['n']), base64.b64decode(d['c']), None)


def run_cmd(name, content, key):
    env = dict(os.environ)
    if SECRETS.exists():
        env['WISPR_VM_SECRETS'] = str(SECRETS)
    env['WISPR_VM_OUT'] = str(PLAIN)
    env['PYTHONPATH'] = str(ROOT / 'vm')
    tmp = TMP / name
    if name.endswith('.enc'):
        SECRETS.write_bytes(decrypt(key, content))
        return 'secrets received (%d bytes, not shown)' % SECRETS.stat().st_size
    tmp.write_bytes(content)
    timeout = 900
    first = content.splitlines()[0].decode('utf-8', 'replace') if content else ''
    if 'timeout=' in first:
        try: timeout = int(first.split('timeout=')[1].split()[0])
        except Exception: pass
    if name.endswith('.ps1'):
        args = ['pwsh', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(tmp)]
    else:
        args = [sys.executable, str(tmp)]
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout, env=env, cwd=str(ROOT))
        out = p.stdout.decode('utf-8', 'replace') + ('\n[stderr]\n' + p.stderr.decode('utf-8', 'replace') if p.stderr else '')
        return f'[exit {p.returncode}]\n' + out
    except subprocess.TimeoutExpired as e:
        return f'[timeout after {timeout}s]\n' + ((e.stdout or b'').decode('utf-8', 'replace'))


def main():
    if not OUTKEY.exists():
        raise SystemExit('vm/outkey.pem missing: refusing to run (results would be public)')
    setup_results()
    key = make_key()
    shot = screenshot(PLAIN / 'start.png')
    (WORK / 'out' / 'status.txt').write_text(f'started {time.ctime()}\n')
    (PLAIN / 'start.txt').write_text(f'screen {shot}\n')
    push_results('start')
    done = set()
    idle = 0
    while time.time() < DEADLINE:
        sh(['git', 'fetch', '-q', 'origin', CTRL], cwd=ROOT, timeout=120)
        ls = sh(['git', 'ls-tree', '--name-only', f'origin/{CTRL}', 'vm/cmd/'], cwd=ROOT).stdout.split()
        names = sorted(Path(x).name for x in ls)
        if 'STOP' in names:
            break
        new = [n for n in names if n not in done and n.split('.')[-1] in ('ps1', 'py', 'enc')]
        if not new:
            idle += 1
            time.sleep(8 if idle < 60 else 20)
            continue
        idle = 0
        for n in new:
            done.add(n)
            raw = subprocess.run(['git', 'show', f'origin/{CTRL}:vm/cmd/{n}'], cwd=ROOT, capture_output=True).stdout
            sh(['git', 'checkout', '-q', f'origin/{CTRL}', '--', 'vm/'], cwd=ROOT)
            t0 = time.time()
            try:
                out = run_cmd(n, raw, key)
            except Exception:
                out = traceback.format_exc()
            stem = n.rsplit('.', 1)[0]
            shot = screenshot(PLAIN / f'{stem}.png')
            (PLAIN / f'{stem}.txt').write_text(f'# {n} took {time.time() - t0:.1f}s; screen {shot}\n' + out[-60000:], encoding='utf-8')
            push_results(f'result {n}')
    (WORK / 'out' / 'status.txt').write_text(f'stopped {time.ctime()}\n')
    push_results('stop')


if __name__ == '__main__':
    main()
