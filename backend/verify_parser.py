import requests

BASE = "http://localhost:8000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}
print("Login:", r.status_code)

# Check parser routes exist
r = requests.get(f"{BASE}/parser/result/1", headers=headers)
print("GET /parser/result/1:", r.status_code, r.json())

# List documents
r = requests.get(f"{BASE}/documents/", headers=headers)
data = r.json()
total = data["total"]
print(f"Documents: {total} total")
if data["items"]:
    doc = data["items"][0]
    doc_id = doc["id"]
    print(f"First doc ID: {doc_id}, Status: {doc['status']}")
    # Trigger process
    r2 = requests.post(f"{BASE}/parser/process/{doc_id}", headers=headers)
    print("POST /parser/process:", r2.status_code, r2.json())
