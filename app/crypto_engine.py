import base64, hashlib, json, time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519

HASHES = ['SHA-256', 'SHA-3-256', 'BLAKE2b-256']
SCHEMES = ['ECDSA-P256', 'Ed25519']
ROLE_POLICIES = {
    'Physician': {'Clinical Record', 'Prescription'},
    'Laboratory': {'Laboratory Report'},
    'Insurer': {'Claim Summary'},
    'Administrator': {'Audit Record'},
}


def canonicalize(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def hash_record(data: bytes, algorithm: str) -> str:
    if algorithm == 'SHA-256': h = hashlib.sha256()
    elif algorithm == 'SHA-3-256': h = hashlib.sha3_256()
    elif algorithm == 'BLAKE2b-256': h = hashlib.blake2b(digest_size=32)
    else: raise ValueError('Unsupported hash algorithm')
    h.update(data)
    return h.hexdigest()


def gen_keys(scheme='ECDSA-P256'):
    if scheme == 'ECDSA-P256':
        priv = ec.generate_private_key(ec.SECP256R1())
    elif scheme == 'Ed25519':
        priv = ed25519.Ed25519PrivateKey.generate()
    else:
        raise ValueError('Unsupported signature scheme')
    pub = priv.public_key()
    priv_pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    pub_pem = pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv_pem, pub_pem


def fingerprint(public_pem: str) -> str:
    key = serialization.load_pem_public_key(public_pem.encode())
    der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return ':'.join(hashlib.sha256(der).hexdigest()[i:i+4].upper() for i in range(0, 32, 4))


def sign_digest_hex(digest_hex: str, private_pem: str, scheme='ECDSA-P256') -> str:
    payload = bytes.fromhex(digest_hex)
    key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    if scheme == 'ECDSA-P256':
        sig = key.sign(payload, ec.ECDSA(hashes.SHA256()))
    elif scheme == 'Ed25519':
        sig = key.sign(payload)
    else:
        raise ValueError('Unsupported signature scheme')
    return base64.b64encode(sig).decode()


def verify_digest_hex(digest_hex: str, signature_b64: str, public_pem: str, scheme='ECDSA-P256') -> bool:
    payload = bytes.fromhex(digest_hex)
    try:
        sig = base64.b64decode(signature_b64)
        key = serialization.load_pem_public_key(public_pem.encode())
        if scheme == 'ECDSA-P256': key.verify(sig, payload, ec.ECDSA(hashes.SHA256()))
        elif scheme == 'Ed25519': key.verify(sig, payload)
        else: return False
        return True
    except Exception:
        return False


def benchmark(data: bytes, rounds=500):
    out=[]
    for alg in HASHES:
        t0=time.perf_counter(); digest=''
        for _ in range(rounds): digest=hash_record(data,alg)
        elapsed=time.perf_counter()-t0
        out.append({'algorithm':alg,'rounds':rounds,'elapsed_ms':round(elapsed*1000,3),'avg_ms':round(elapsed*1000/rounds,5),'digest_length_bits':len(digest)*4})
    return out


def tamper(record: dict, field='diagnosis'):
    x=json.loads(json.dumps(record))
    x[field] = str(x.get(field,'')) + ' [ALTERED]'
    return x


def policy_check(role: str, document_type: str):
    allowed = document_type in ROLE_POLICIES.get(role, set())
    return {'allowed': allowed, 'role': role, 'document_type': document_type, 'policy': 'ALLOW' if allowed else 'DENY'}
