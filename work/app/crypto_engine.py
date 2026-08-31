import base64, hashlib, json, time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519

HASHES = ['SHA-256','SHA-3-256','BLAKE2b-256']
SCHEMES = ['ECDSA-P256','Ed25519']


def canonicalize(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def hash_record(data: bytes, algorithm: str) -> str:
    if algorithm == 'SHA-256': h = hashlib.sha256()
    elif algorithm == 'SHA-3-256': h = hashlib.sha3_256()
    elif algorithm == 'BLAKE2b-256': h = hashlib.blake2b(digest_size=32)
    else: raise ValueError('Unsupported hash algorithm')
    h.update(data); return h.hexdigest()


def gen_keys(scheme='ECDSA-P256'):
    if scheme == 'ECDSA-P256':
        priv = ec.generate_private_key(ec.SECP256R1()); pub = priv.public_key()
    elif scheme == 'Ed25519':
        priv = ed25519.Ed25519PrivateKey.generate(); pub = priv.public_key()
    else: raise ValueError('Unsupported signature scheme')
    priv_pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    pub_pem = pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv_pem, pub_pem


def key_fingerprint(public_pem: str) -> str:
    key = serialization.load_pem_public_key(public_pem.encode())
    der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest().upper()


def sign_digest_hex(digest_hex: str, private_pem: str, scheme='ECDSA-P256') -> str:
    payload = bytes.fromhex(digest_hex)
    key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    sig = key.sign(payload, ec.ECDSA(hashes.SHA256())) if scheme == 'ECDSA-P256' else key.sign(payload)
    return base64.b64encode(sig).decode()


def verify_digest_hex(digest_hex: str, signature_b64: str, public_pem: str, scheme='ECDSA-P256') -> bool:
    try:
        payload = bytes.fromhex(digest_hex); sig = base64.b64decode(signature_b64)
        key = serialization.load_pem_public_key(public_pem.encode())
        if scheme == 'ECDSA-P256': key.verify(sig, payload, ec.ECDSA(hashes.SHA256()))
        else: key.verify(sig, payload)
        return True
    except Exception:
        return False


def benchmark_hash(data: bytes, rounds=500):
    results=[]
    for alg in HASHES:
        t0=time.perf_counter(); digest=''
        for _ in range(rounds): digest=hash_record(data, alg)
        elapsed=time.perf_counter()-t0
        results.append({'algorithm':alg,'rounds':rounds,'elapsed_ms':round(elapsed*1000,3),'avg_ms':round(elapsed*1000/rounds,6),'throughput_kops':round(rounds/elapsed/1000,3),'digest_length_bits':len(digest)*4})
    return results


def benchmark_signatures(digest_hex, rounds=100):
    results=[]
    for scheme in SCHEMES:
        priv,pub=gen_keys(scheme)
        t0=time.perf_counter(); sig=''
        for _ in range(rounds): sig=sign_digest_hex(digest_hex,priv,scheme)
        sign_elapsed=time.perf_counter()-t0
        t0=time.perf_counter(); ok=False
        for _ in range(rounds): ok=verify_digest_hex(digest_hex,sig,pub,scheme)
        verify_elapsed=time.perf_counter()-t0
        results.append({'scheme':scheme,'rounds':rounds,'sign_avg_ms':round(sign_elapsed*1000/rounds,5),'verify_avg_ms':round(verify_elapsed*1000/rounds,5),'signature_bytes':len(base64.b64decode(sig)),'public_key_bytes':len(serialization.load_pem_public_key(pub.encode()).public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)),'verified':ok})
    return results


def tamper(record: dict, field='diagnosis'):
    x=dict(record); x[field] = str(x.get(field,'')) + ' [ALTERED]'; return x


def hamming_hex(a: str, b: str) -> int:
    return sum(bin(x ^ y).count('1') for x,y in zip(bytes.fromhex(a), bytes.fromhex(b)))


def avalanche_test(record: dict, field='diagnosis'):
    raw=canonicalize(record); modified=tamper(record,field)
    out=[]
    for alg in HASHES:
        a=hash_record(raw,alg); b=hash_record(canonicalize(modified),alg)
        out.append({'algorithm':alg,'changed_bits':hamming_hex(a,b),'digest_bits':len(a)*4,'percentage':round(hamming_hex(a,b)/(len(a)*4)*100,2)})
    return out
