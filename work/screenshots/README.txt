Execution evidence

Run:
python -m pytest tests\\test_crypto.py -v

Expected current validation:
4 passed

Then:
uvicorn app.main:app --reload --port 8000

Open:
http://127.0.0.1:8000

Capture your own browser screenshots after running the final version. Recommended evidence:
01_dashboard.png
02_signed_document.png
03_tamper_rejected.png
04_benchmark.png
05_audit_trail.png
06_key_revocation.png
