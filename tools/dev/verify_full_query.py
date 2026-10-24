import json
import re
import sys

sys.path.insert(0, r"C:\Users\Umar\anime-text-dataset")
import requests

src_text = open(r"C:\Users\Umar\anime-text-dataset\src\sources\anilist.py", encoding="utf-8").read()
m = re.search(r'FULL_QUERY = """(.*?)"""', src_text, re.S)
query = m.group(1)

r = requests.post(
    "https://graphql.anilist.co",
    json={"query": query, "variables": {"ids": [1]}},
    headers={"Accept": "application/json"},
    timeout=60,
)
print("status:", r.status_code)
if r.status_code == 200:
    m0 = r.json()["data"]["Page"]["media"]
    print("media returned:", len(m0))
    if m0:
        s = m0[0].get("studios", {}).get("edges")[:2]
        print("studio edges sample:", json.dumps(s, ensure_ascii=False)[:200] if s else None)
        print("relations ok:", bool(m0[0].get("relations")) and "edges" in m0[0]["relations"])
        print("characters ok:", bool(m0[0].get("characters")) and "edges" in m0[0]["characters"])
else:
    print(r.text[:500])