import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
print("--- raw_payload by source/kind ---")
for r in conn.execute("select source, remote_kind, count(*) from raw_payload group by source, remote_kind order by source"):
    print(f"  {r[0]:12s} {r[1]:14s} {r[2]}")
print("--- checkpoint tail ---")
for r in conn.execute("select key, value from checkpoint order by updated_at"):
    print(f"  {r[0]} = {r[1]}")
print("--- run_log tail ---")
for r in conn.execute("select ts, phase, message from run_log order by ts desc limit 6"):
    print(f"  {r[0]} [{r[1]}] {r[2]}")