import datetime
import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "anime.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoint (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_payload (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,
  remote_kind TEXT NOT NULL,
  remote_id TEXT NOT NULL,
  url TEXT,
  retrieved_at TEXT NOT NULL,
  http_status INTEGER DEFAULT 200,
  license_note TEXT,
  payload TEXT NOT NULL,
  UNIQUE(source, remote_kind, remote_id)
);
CREATE INDEX IF NOT EXISTS idx_raw_source_kind ON raw_payload(source, remote_kind);

CREATE TABLE IF NOT EXISTS anime (
  anime_id INTEGER PRIMARY KEY,
  type TEXT,
  status TEXT,
  episodes INTEGER,
  duration_min INTEGER,
  aired_from TEXT,
  aired_to TEXT,
  season TEXT,
  year INTEGER,
  title_canonical TEXT,
  title_english TEXT,
  title_japanese TEXT,
  synopsis TEXT,
  synopsis_source TEXT,
  mean_score REAL,
  popularity INTEGER,
  favourites INTEGER,
  source_material TEXT,
  age_rating TEXT,
  quality_tier TEXT,
  confidence TEXT
);

CREATE TABLE IF NOT EXISTS anime_source (
  source TEXT NOT NULL,
  remote_id TEXT NOT NULL,
  anime_id INTEGER NOT NULL,
  url TEXT,
  link_method TEXT NOT NULL,
  confidence REAL NOT NULL,
  PRIMARY KEY (source, remote_id)
);
CREATE INDEX IF NOT EXISTS idx_anime_source_anime ON anime_source(anime_id);

CREATE TABLE IF NOT EXISTS alt_titles (
  anime_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  lang TEXT,
  kind TEXT,
  title TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alt_titles_anime ON alt_titles(anime_id);

CREATE TABLE IF NOT EXISTS anime_genres (anime_id INTEGER NOT NULL, genre TEXT NOT NULL, PRIMARY KEY (anime_id, genre));
CREATE TABLE IF NOT EXISTS anime_themes (anime_id INTEGER NOT NULL, theme TEXT NOT NULL, PRIMARY KEY (anime_id, theme));
CREATE TABLE IF NOT EXISTS anime_studios (
  anime_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  studio_name TEXT NOT NULL,
  source_studio_id TEXT,
  is_main INTEGER DEFAULT 0,
  PRIMARY KEY (anime_id, source, studio_name)
);
CREATE TABLE IF NOT EXISTS genres (genre TEXT PRIMARY KEY, description TEXT);
CREATE TABLE IF NOT EXISTS themes (theme TEXT PRIMARY KEY, description TEXT);
CREATE TABLE IF NOT EXISTS studios (studio_name TEXT PRIMARY KEY, source_studio_id TEXT, url TEXT);

CREATE TABLE IF NOT EXISTS characters (
  id INTEGER PRIMARY KEY,
  anime_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  remote_id TEXT,
  name TEXT NOT NULL,
  name_native TEXT,
  role TEXT,
  description TEXT,
  voice_actors TEXT,
  UNIQUE(source, anime_id, remote_id)
);
CREATE INDEX IF NOT EXISTS idx_characters_anime ON characters(anime_id);
CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(name);

CREATE TABLE IF NOT EXISTS staff (
  id INTEGER PRIMARY KEY,
  anime_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  remote_id TEXT,
  name TEXT NOT NULL,
  name_native TEXT,
  roles TEXT,
  UNIQUE(source, anime_id, remote_id)
);
CREATE INDEX IF NOT EXISTS idx_staff_anime ON staff(anime_id);

CREATE TABLE IF NOT EXISTS episodes (
  id INTEGER PRIMARY KEY,
  anime_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  remote_id TEXT,
  number INTEGER,
  title TEXT,
  title_native TEXT,
  synopsis TEXT,
  aired TEXT,
  length_min INTEGER,
  UNIQUE(source, anime_id, number)
);
CREATE INDEX IF NOT EXISTS idx_episodes_anime ON episodes(anime_id);

CREATE TABLE IF NOT EXISTS relationships (
  anime_id INTEGER NOT NULL,
  other_anime_id INTEGER,
  other_source TEXT,
  other_remote_id TEXT,
  relation TEXT NOT NULL,
  source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rel_anime ON relationships(anime_id);

CREATE TABLE IF NOT EXISTS descriptions (
  anime_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  text TEXT NOT NULL,
  synthetic INTEGER NOT NULL DEFAULT 0,
  provenance TEXT,
  PRIMARY KEY (anime_id, kind)
);

CREATE TABLE IF NOT EXISTS qa_pairs (
  id INTEGER PRIMARY KEY,
  anime_id INTEGER NOT NULL,
  qtype TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  template TEXT NOT NULL,
  grounded_fields TEXT
);
CREATE INDEX IF NOT EXISTS idx_qa_anime ON qa_pairs(anime_id);

CREATE TABLE IF NOT EXISTS instructions (
  id INTEGER PRIMARY KEY,
  anime_id INTEGER NOT NULL,
  itype TEXT NOT NULL,
  instruction TEXT NOT NULL,
  input TEXT,
  output TEXT NOT NULL,
  synthetic INTEGER NOT NULL DEFAULT 1,
  source_record_ids TEXT,
  purpose TEXT,
  validation TEXT
);
CREATE INDEX IF NOT EXISTS idx_instructions_anime ON instructions(anime_id);

CREATE TABLE IF NOT EXISTS franchises (
  anime_id INTEGER PRIMARY KEY,
  franchise_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_franchise_id ON franchises(franchise_id);

CREATE TABLE IF NOT EXISTS dedup_log (
  id INTEGER PRIMARY KEY,
  cluster_id INTEGER NOT NULL,
  canonical_anime_id INTEGER NOT NULL,
  method TEXT NOT NULL,
  members TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_chunks (
  id INTEGER PRIMARY KEY,
  anime_id INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  kind TEXT,
  text TEXT NOT NULL,
  source_refs TEXT
);
CREATE INDEX IF NOT EXISTS idx_rag_anime ON rag_chunks(anime_id);

CREATE TABLE IF NOT EXISTS license_tiers (
  anime_id INTEGER PRIMARY KEY,
  tier TEXT NOT NULL,
  sources TEXT,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS provenance (
  id INTEGER PRIMARY KEY,
  entity TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  source TEXT NOT NULL,
  url TEXT,
  retrieved_at TEXT NOT NULL,
  license_note TEXT,
  confidence REAL
);
CREATE INDEX IF NOT EXISTS idx_prov_entity ON provenance(entity, entity_id);

CREATE TABLE IF NOT EXISTS quality_validation (
  id INTEGER PRIMARY KEY,
  check_name TEXT NOT NULL,
  target TEXT,
  status TEXT NOT NULL,
  detail TEXT
);

CREATE TABLE IF NOT EXISTS splits (
  anime_id INTEGER PRIMARY KEY,
  split TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_log (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  phase TEXT NOT NULL,
  message TEXT
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(anime)")}
    if "quality_tier" not in cols:
        conn.execute("ALTER TABLE anime ADD COLUMN quality_tier TEXT")
    if "confidence" not in cols:
        conn.execute("ALTER TABLE anime ADD COLUMN confidence TEXT")


def connect(path: pathlib.Path | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=60, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def cp_get(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM checkpoint WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    return json.loads(row["value"])


def cp_set(conn: sqlite3.Connection, key: str, value) -> None:
    conn.execute(
        "INSERT INTO checkpoint(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, json.dumps(value), now()),
    )
    conn.commit()


def log(conn: sqlite3.Connection, phase: str, message: str) -> None:
    conn.execute("INSERT INTO run_log(ts,phase,message) VALUES(?,?,?)", (now(), phase, message))
    conn.commit()


def upsert_raw(
    conn: sqlite3.Connection,
    source: str,
    kind: str,
    remote_id,
    payload,
    url: str | None = None,
    license_note: str | None = None,
    http_status: int = 200,
) -> None:
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    conn.execute(
        "INSERT INTO raw_payload(source,remote_kind,remote_id,url,retrieved_at,http_status,license_note,payload) "
        "VALUES(?,?,?,?,?,?,?,?) "
        "ON CONFLICT(source,remote_kind,remote_id) DO UPDATE SET "
        "payload=excluded.payload, retrieved_at=excluded.retrieved_at, http_status=excluded.http_status, url=excluded.url",
        (source, kind, str(remote_id), url, now(), http_status, license_note, body),
    )


def bulk_commit(conn: sqlite3.Connection, every: int = 500, counter: list | None = None) -> None:
    if counter is not None:
        counter[0] += 1
        if counter[0] % every:
            return
    conn.commit()
