from app.crypto_engine import *

RECORD={'record_id':'T1','patient_alias':'PT-1','document_type':'Clinical Record','diagnosis':'stable','prescription':'none'}

def test_hashes_are_256_bits_and_different():
    raw=canonicalize(RECORD)
    vals=[hash_record(raw,a) for a in HASHES]
    assert all(len(x)==64 for x in vals)
    assert len(set(vals))==3

def test_ecdsa_round_trip_and_tamper_failure():
    raw=canonicalize(RECORD); d=hash_record(raw,'SHA-256'); priv,pub=gen_keys('ECDSA-P256'); sig=sign_digest_hex(d,priv,'ECDSA-P256')
    assert verify_digest_hex(d,sig,pub,'ECDSA-P256')
    altered=RECORD.copy(); altered['diagnosis']='tampered'; d2=hash_record(canonicalize(altered),'SHA-256')
    assert d2!=d
    assert not verify_digest_hex(d2,sig,pub,'ECDSA-P256')

def test_ed25519_round_trip():
    raw=canonicalize(RECORD); d=hash_record(raw,'SHA-3-256'); priv,pub=gen_keys('Ed25519'); sig=sign_digest_hex(d,priv,'Ed25519')
    assert verify_digest_hex(d,sig,pub,'Ed25519')

def test_role_policy():
    assert policy_check('Physician','Prescription')['allowed']
    assert not policy_check('Insurer','Prescription')['allowed']
