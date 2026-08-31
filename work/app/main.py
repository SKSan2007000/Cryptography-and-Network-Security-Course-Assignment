from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from pathlib import Path
from .crypto_engine import *
import time, uuid, copy

app=FastAPI(title='EHR CryptoGuard', version='3.0')
ROOT=Path(__file__).resolve().parent.parent
INDEX=(ROOT/'static'/'index.html').read_text(encoding='utf-8')
KEYS={}; DOCS={}; AUDIT=[]
DEMO={'patient_id':'EHR-DEMO-001','patient_name':'Asha Raman','date':'2026-08-31','provider':'Dr. Meera Iyer','facility':'Sentinel Telehealth Centre','diagnosis':'Acute respiratory infection','prescription':'Amoxicillin 500 mg — as prescribed','lab_summary':'CRP mildly elevated; oxygen saturation 97%','sensitivity':'RESTRICTED'}
ROLE_POLICY={
 'Physician':{'clinical':True,'prescription':True,'lab':True,'claim':False},
 'Laboratory':{'clinical':False,'prescription':False,'lab':True,'claim':False},
 'Insurer':{'clinical':False,'prescription':False,'lab':True,'claim':True},
 'Administrator':{'clinical':True,'prescription':True,'lab':True,'claim':True},
}
class SignReq(BaseModel): record:dict; hash_algorithm:str='SHA-256'; scheme:str='ECDSA-P256'; signer:str='Dr. Meera Iyer'; role:str='Physician'; purpose:str='Clinical documentation'
class VerifyReq(BaseModel): record:dict; digest:str; signature:str; public_key:str; scheme:str='ECDSA-P256'; hash_algorithm:str='SHA-256'; key_id:str|None=None; role:str='Physician'
class AccessReq(BaseModel): role:str; resource:str
class KeyReq(BaseModel): scheme:str='ECDSA-P256'; owner:str='Dr. Meera Iyer'; role:str='Physician'
class AttackReq(BaseModel): record:dict; attack:str


def now(): return time.strftime('%Y-%m-%d %H:%M:%S')
def event(name,**kw):
    AUDIT.append({'event_id':'EV-'+uuid.uuid4().hex[:10].upper(),'event':name,'timestamp':now(),**kw})
    return AUDIT[-1]

def role_allowed(role,resource): return bool(ROLE_POLICY.get(role,{}).get(resource,False))

def register_key(scheme,owner,role):
    priv,pub=gen_keys(scheme); kid='KEY-'+uuid.uuid4().hex[:8].upper(); fp=key_fingerprint(pub)
    KEYS[kid]={'private':priv,'public':pub,'scheme':scheme,'owner':owner,'role':role,'fingerprint':fp,'created':now(),'status':'ACTIVE'}
    event('KEY_GENERATED',key_id=kid,scheme=scheme,owner=owner,role=role,fingerprint=fp)
    return kid

@app.get('/',response_class=HTMLResponse)
def home(): return INDEX
@app.get('/api/demo')
def demo(): return {'record':DEMO}
@app.get('/api/dashboard')
def dashboard():
    return {'documents':len(DOCS),'active_keys':sum(k['status']=='ACTIVE' for k in KEYS.values()),'revoked_keys':sum(k['status']=='REVOKED' for k in KEYS.values()),'verified':sum(e.get('result')=='VALID' for e in AUDIT),'rejected':sum(e.get('result')=='REJECTED' for e in AUDIT),'tampered':sum(e['event']=='TAMPER_DETECTED' for e in AUDIT),'events':len(AUDIT)}
@app.post('/api/keys')
def keys(req:KeyReq):
    kid=register_key(req.scheme,req.owner,req.role); k=KEYS[kid]
    return {'key_id':kid,'public_key':k['public'],'fingerprint':k['fingerprint'],'scheme':k['scheme'],'owner':k['owner'],'role':k['role'],'status':k['status'],'created':k['created']}
@app.get('/api/keys')
def list_keys():
    return {'keys':[{k:x for k,x in v.items() if k not in ('private',)}|{'key_id':kid} for kid,v in KEYS.items()]}
@app.post('/api/keys/{key_id}/revoke')
def revoke_key(key_id:str):
    if key_id not in KEYS: raise HTTPException(404,'Unknown key')
    KEYS[key_id]['status']='REVOKED'; event('KEY_REVOKED',key_id=key_id,fingerprint=KEYS[key_id]['fingerprint']); return {'revoked':True,'key_id':key_id}
@app.post('/api/sign')
def sign(req:SignReq):
    if not role_allowed(req.role,'clinical') and req.role!='Administrator': raise HTTPException(403,'Role is not permitted to sign clinical records')
    kid=register_key(req.scheme,req.signer,req.role); k=KEYS[kid]
    raw=canonicalize(req.record); digest=hash_record(raw,req.hash_algorithm); sig=sign_digest_hex(digest,k['private'],req.scheme)
    sid='SIG-'+uuid.uuid4().hex[:10].upper(); docid='DOC-'+uuid.uuid4().hex[:8].upper()
    DOCS[docid]={'record':copy.deepcopy(req.record),'digest':digest,'signature':sig,'key_id':kid,'scheme':req.scheme,'hash_algorithm':req.hash_algorithm,'signer':req.signer,'role':req.role,'purpose':req.purpose,'created':now(),'status':'SIGNED'}
    event('DOCUMENT_SIGNED',document_id=docid,signature_id=sid,key_id=kid,signer=req.signer,role=req.role,hash=req.hash_algorithm,scheme=req.scheme,digest=digest)
    return {'document_id':docid,'signature_id':sid,'digest':digest,'signature':sig,'public_key':k['public'],'key_id':kid,'fingerprint':k['fingerprint'],'scheme':req.scheme,'hash_algorithm':req.hash_algorithm,'canonical_bytes':len(raw)}
@app.post('/api/verify')
def verify(req:VerifyReq):
    raw=canonicalize(req.record); current=hash_record(raw,req.hash_algorithm); match=current==req.digest
    key_status='UNKNOWN'; trusted=False; owner=None
    if req.key_id and req.key_id in KEYS:
        k=KEYS[req.key_id]; key_status=k['status']; trusted=(k['status']=='ACTIVE' and k['public'].strip()==req.public_key.strip()); owner=k['owner']
    sig_ok=verify_digest_hex(current,req.signature,req.public_key,req.scheme); valid=match and sig_ok and (trusted if req.key_id else True)
    event('VERIFICATION',result='VALID' if valid else 'REJECTED',hash_match=match,signature_valid=sig_ok,key_trusted=trusted,key_status=key_status,key_id=req.key_id)
    return {'valid':valid,'hash_match':match,'signature_valid':sig_ok,'key_trusted':trusted,'key_status':key_status,'key_owner':owner,'current_digest':current,'expected_digest':req.digest}
@app.post('/api/tamper')
def tamper_api(req:AttackReq):
    r=copy.deepcopy(req.record); attacks={'diagnosis':'diagnosis','prescription':'prescription','lab':'lab_summary','provider':'provider','patient':'patient_name','date':'date'}
    field=attacks.get(req.attack); 
    if req.attack=='multiple':
        for f in ['diagnosis','prescription','lab_summary']: r[f]=str(r.get(f,''))+' [ALTERED]'
    elif field: r[field]=str(r.get(field,''))+' [ALTERED]'
    else: raise HTTPException(400,'Unknown attack')
    event('TAMPER_DETECTED',attack=req.attack,field=field or 'multiple'); return {'tampered_record':r,'attack':req.attack}
@app.post('/api/benchmark')
def bench(record:dict):
    raw=canonicalize(record); digest=hash_record(raw,'SHA-256'); return {'bytes':len(raw),'hash_results':benchmark_hash(raw,500),'signature_results':benchmark_signatures(digest,100)}
@app.post('/api/avalanche')
def avalanche(record:dict): return {'results':avalanche_test(record)}
@app.post('/api/access')
def access(req:AccessReq):
    allowed=role_allowed(req.role,req.resource); event('ACCESS_CHECK',role=req.role,resource=req.resource,result='ALLOWED' if allowed else 'DENIED'); return {'allowed':allowed,'role':req.role,'resource':req.resource}
@app.get('/api/audit')
def audit(): return {'events':AUDIT[-100:]}
@app.get('/api/documents')
def documents(): return {'documents':[{k:v for k,v in d.items() if k not in ('record','signature')}|{'document_id':i} for i,d in DOCS.items()]}
@app.get('/api/documents/{doc_id}')
def document(doc_id:str):
    if doc_id not in DOCS: raise HTTPException(404,'Unknown document')
    return {'document_id':doc_id,**DOCS[doc_id]}
@app.get('/api/policies')
def policies(): return {'policies':ROLE_POLICY}
@app.get('/api/health')
def health(): return {'status':'ok','service':'EHR CryptoGuard','version':'3.0'}
