# EHR CryptoGuard v3.0

Academic implementation for Assignment 5: Evaluation of Cryptographic Hash Functions and Digital Signatures in Electronic Health Record Security.

## Features
- Synthetic EHR document manager and canonicalization
- SHA-256, SHA-3-256 and BLAKE2b-256 laboratory
- ECDSA P-256 and Ed25519 digital signatures
- Trusted key registry, fingerprints, key revocation
- Multi-party role-based access control
- Verification centre with digest + signature + trusted-key checks
- Targeted tamper/attack simulator
- Avalanche / Hamming-distance experiment
- Hash and signature performance benchmark
- Audit and compliance event trail
- Security scorecard and post-quantum migration note
- Automated tests

## Run on Windows
```cmd
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest tests\test_crypto.py -v
uvicorn app.main:app --reload --port 8000
```
Open http://127.0.0.1:8000

## GitHub
```cmd
git init
git add .
git commit -m "EHR CryptoGuard v3 academic implementation"
git branch -M main
git remote add origin <YOUR_REPOSITORY_URL>
git push -u origin main
```

## Important
This is an academic prototype using synthetic EHR data. Production deployment would require HSM-backed key custody, certificate/PKI lifecycle management, secure persistence, authenticated sessions, encryption in transit/at rest, regulatory controls and formal security testing.
