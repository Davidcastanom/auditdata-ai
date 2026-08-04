"""Check if diagnostic API returns signal field."""
from data_engine.diagnostic import diagnose_dataset
from data_engine.analyzer import load_dataset

csv = 'id,nombre,ciudad,edad,horas_sueno,litros_agua,completo_reto\n1,Ana,Bogota,28,7,2.1,si\n2,Juan,bogota,31,6,1.8,no\n1,Ana,Bogota,28,7,2.1,si\n4,Maria,Medellin,,8,2.4,si\n5,Luis,Medellin,450,2,,no'
headers, rows, hri = load_dataset("test.csv", csv.encode("utf-8"))
diag = diagnose_dataset(headers, rows, hri)
d = diag.to_dict()
for col in d["columns"]:
    for iss in col.get("issues", []):
        sig = iss.get("signal", "MISSING")
        conf = iss.get("confidence", "MISSING")
        print(f"{col['column']:12s} {iss['category_code']:25s} signal={sig} confidence={conf}")
