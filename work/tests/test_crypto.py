from app.crypto_engine import *

def test_hashes_are_256_bits_and_different():
    data=canonicalize({'a':1,'b':'EHR'})
    ds=[hash_record(data,x) for x in HASHES]
    assert all(len(x)==64 for x in ds) and len(set(ds))==3

def test_ecdsa_round_trip_and_tamper_failure():
    d=hash_record(canonicalize({'diagnosis':'stable'}),'SHA-256'); priv,pub=gen_keys('ECDSA-P256'); sig=sign_digest_hex(d,priv,'ECDSA-P256')
    assert verify_digest_hex(d,sig,pub,'ECDSA-P256')
    d2=hash_record(canonicalize({'diagnosis':'changed'}),'SHA-256'); assert not verify_digest_hex(d2,sig,pub,'ECDSA-P256')

def test_ed25519_round_trip():
    d=hash_record(b'prescription','SHA-3-256'); priv,pub=gen_keys('Ed25519'); sig=sign_digest_hex(d,priv,'Ed25519'); assert verify_digest_hex(d,sig,pub,'Ed25519')

def test_avalanche():
    r={'diagnosis':'Acute infection'}; out=avalanche_test(r); assert all(x['changed_bits']>0 for x in out)
