"""Check API response with exact E2E sample."""
import base64, json
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

# Exact E2E sample from app.js
csv = "\n".join([
    "id,nombre,ciudad,edad,horas_sueno,litros_agua,completo_reto",
    "1,Ana,Bogota,28,7,2.1,si",
    "2,Juan,bogota,31,6,1.8,no",
    "3,Ana,Bogota,28,7,2.1,si",
    "4,Maria,Medellin,,8,2.4,si",
    "5,Luis,Medellin,450,2,,no",
])
b64 = base64.b64encode(csv.encode("utf-8")).decode("ascii")

resp = client.post("/api/diagnose", json={"filename": "moveup_sample.csv", "content_base64": b64})
data = resp.json()
diag = data["diagnostic"]
total = sum(len(c.get("issues", [])) for c in diag["columns"])
print(f"Total issues: {total}")
for col in diag["columns"]:
    for iss in col.get("issues", []):
        sig = iss.get("signal", "MISSING")
        conf = iss.get("confidence", "MISSING")
        print(f"  {col['column']:12s} {iss['category_code']:25s} signal={sig} confidence={conf}")
