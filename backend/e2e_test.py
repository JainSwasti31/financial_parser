"""End-to-end test: upload a fixture, trigger process, poll until done, print result."""
import requests
import time
import os

BASE = "http://localhost:8000/api/v1"
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "test_fixtures")

# Login
r = requests.post(f"{BASE}/auth/login", json={"email": "admin@example.com", "password": "password123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login: OK")

# Upload a test fixture
fixture = os.path.join(FIXTURES_DIR, "bank_statement.pdf")
with open(fixture, "rb") as f:
    r = requests.post(
        f"{BASE}/upload/",
        files={"file": ("bank_statement_test.pdf", f, "application/pdf")},
        headers=headers
    )

if r.status_code == 200:
    doc = r.json()
    doc_id = doc["id"]
    print(f"Uploaded: doc_id={doc_id}")
elif r.status_code == 409:
    # Duplicate — get existing
    r2 = requests.get(f"{BASE}/documents/", headers=headers)
    items = r2.json()["items"]
    doc_id = items[0]["id"]
    print(f"Duplicate — using existing doc_id={doc_id}")
else:
    print(f"Upload failed: {r.status_code} {r.text}")
    exit(1)

# Trigger processing
r = requests.post(f"{BASE}/parser/process/{doc_id}", headers=headers)
print(f"Process trigger: {r.status_code} {r.json()}")

# Poll until done (up to 120 seconds)
print("Polling for result...")
for i in range(48):
    time.sleep(2.5)
    r = requests.get(f"{BASE}/parser/result/{doc_id}", headers=headers)
    data = r.json()
    status = data.get("status")
    print(f"  [{i+1}] Status: {status}")
    if status in ("Parsed", "Review Pending", "Validation Failed"):
        print("\n=== FINAL RESULT ===")
        print(f"Status: {status}")
        if data.get("report"):
            print(f"Document Type: {data['report'].get('document_type')}")
            print(f"Fields: {list(data['report'].get('parsed_fields', {}).keys())}")
        break
else:
    print("Timed out waiting for result")
