from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from .crypto_engine import *
import time, uuid

app=FastAPI(title='EHR CryptoGuard', version='2.0')
ROOT=Path(__file__).resolve().parent.parent
INDEX=(ROOT/'static'/'index.html').read_text(encoding='utf-8')
AUDIT=[]
TRUSTED={}
DEMO={
 'record_id':'EHR-DEMO-001','patient_alias':'PT-1042','document_type':'Clinical Record','date':'2026-08-31',
 'provider':'Dr. Meera Iyer','facility':'Sentinel Telehealth Centre','diagnosis':'Acute respiratory infection',
 'prescription':'Amoxicillin 500 mg — as prescribed','lab_summary':'CRP mildly elevated; oxygen saturation 97%',
 'sensitivity':'RESTRICTED'
}
class SignReq(BaseModel):
    record:dict; hash_algorithm:str='SHA-256'; scheme:str='ECDSA-P256'; signer:str='Dr. Meera Iyer'; role:str='Physician'; document_type:str='Clinical Record'
class VerifyReq(BaseModel):
    record:dict; digest:str; signature:str; public_key:str; scheme:str='ECDSA-P256'; hash_algorithm:str='SHA-256'; signer:str=''; role:str=''; document_type:str='Clinical Record'; key_fingerprint:str=''

@app.get('/',response_class=HTMLResponse)
def home(): return INDEX
@app.get('/api/demo')
def demo(): return {'record':DEMO}
@app.get('/api/health')
def health(): return {'status':'ok','service':'EHR CryptoGuard','version':'2.0'}
@app.get('/api/policies')
def policies(): return ROLE_POLICIES
@app.post('/api/sign')
def sign(req:SignReq):
    policy=policy_check(req.role,req.document_type)
    if not policy['allowed']:
        return {'error':'ROLE_POLICY_DENIED', 'policy':policy}
    raw=canonicalize(req.record); digest=hash_record(raw,req.hash_algorithm)
    priv,pub=gen_keys(req.scheme); sig=sign_digest_hex(digest,priv,req.scheme)
    sid='SIG-'+uuid.uuid4().hex[:10].upper(); fp=fingerprint(pub)
    TRUSTED[fp]={'signer':req.signer,'role':req.role,'public_key':pub,'scheme':req.scheme,'created':time.time()}
    AUDIT.append({'event':'DOCUMENT_SIGNED','signature_id':sid,'signer':req.signer,'role':req.role,'document_type':req.document_type,'hash':req.hash_algorithm,'scheme':req.scheme,'fingerprint':fp,'timestamp':time.strftime('%Y-%m-%d %H:%M:%S')})
    return {'signature_id':sid,'digest':digest,'signature':sig,'public_key':pub,'private_key':priv,'scheme':req.scheme,'hash_algorithm':req.hash_algorithm,'canonical_bytes':len(raw),'key_fingerprint':fp,'policy':policy}

@app.post('/api/verify')
def verify(req:VerifyReq):
    raw=canonicalize(req.record); current=hash_record(raw,req.hash_algorithm); match=(current==req.digest)
    sig_ok=verify_digest_hex(current,req.signature,req.public_key,req.scheme)
    fp=fingerprint(req.public_key)
    trusted=fp in TRUSTED and (not req.key_fingerprint or fp==req.key_fingerprint)
    identity_ok = trusted and (not req.signer or TRUSTED[fp]['signer']==req.signer)
    policy=policy_check(req.role,req.document_type) if req.role else {'allowed':True,'policy':'NOT_CHECKED'}
    valid=match and sig_ok and trusted and identity_ok and policy['allowed']
    AUDIT.append({'event':'VERIFICATION','result':'VALID' if valid else 'REJECTED','hash_match':match,'signature_valid':sig_ok,'trusted_key':trusted,'identity_match':identity_ok,'policy':policy['policy'],'timestamp':time.strftime('%Y-%m-%d %H:%M:%S')})
    return {'valid':valid,'hash_match':match,'signature_valid':sig_ok,'trusted_key':trusted,'identity_match':identity_ok,'policy':policy,'current_digest':current,'expected_digest':req.digest,'key_fingerprint':fp}

@app.post('/api/tamper')
def tamper_api(record:dict): return {'tampered_record':tamper(record)}
@app.post('/api/benchmark')
def bench(record:dict): return {'bytes':len(canonicalize(record)),'results':benchmark(canonicalize(record),500)}
@app.get('/api/audit')
def audit(): return {'events':AUDIT[-50:]}
