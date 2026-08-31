# EHR CryptoGuard — Assignment 5

Academic prototype for evaluating cryptographic hash functions and digital signatures for Electronic Health Record (EHR) integrity and origin authentication.

## Features
- SHA-256, SHA-3-256 and BLAKE2b-256 comparison
- ECDSA P-256 and Ed25519 digital signatures
- Canonical JSON serialization to make hashing deterministic
- Signature generation and verification
- Two-layer verification: digest equality + signature validity
- Tamper simulation for diagnosis/prescription fields
- Runtime performance benchmark
- Append-style audit trail
- Security requirement-to-primitive mapping
- Synthetic data only

## Run
```bash
python -m venv .venv
.venv\\Scripts\\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Suggested demonstration
1. Load demo EHR.
2. Select SHA-256 + ECDSA-P256.
3. Click Hash + Sign.
4. Verify current record — expected PASS.
5. Click Simulate tampering — expected REJECTED.
6. Restore demo and compare SHA-3-256 / BLAKE2b-256.
7. Run benchmark and record the runtime displayed by your machine.
8. Open Audit Trail for evidence.

## Security note
This is an academic prototype, not a clinical deployment. It intentionally uses synthetic records and does not store real patient identifiers. Production systems need certificate/PKI lifecycle management, HSM-backed keys, secure identity proofing, role/attribute-based authorization, secure transport, key rotation/revocation, protected audit storage, privacy controls and regulatory validation.

## Vercel deployment
This project includes `api/index.py` as the Vercel Python entry point. It imports and exports the FastAPI instance from `app.main`. `vercel.json` routes all requests to that entry point.
