import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from typing import Optional, Iterable
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def read_issues_csv(csv_file):
    df = pd.read_csv(csv_file)
    for col in ["CREATED_AT", "UPDATED_AT", "CLOSED_AT"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["LABELS"] = df["LABELS"].fillna("").apply(lambda x: [lbl.strip() for lbl in str(x).split(";") if lbl.strip()])
    df["ASSIGNEES"] = df["ASSIGNEES"].fillna("").apply(lambda x: [a.strip() for a in str(x).split(";") if a.strip()])
    return df


def is_sqlite(conn) -> bool:
    return isinstance(conn, sqlite3.Connection)

def execute_sql(conn, query: str, params=None):
    if is_sqlite(conn):
        cur = conn.cursor()
        cur.execute(query, params or [])
        return cur
    else:
        cur = conn.cursor()
        cur.execute(query, params or [])
        return cur

def ensure_schema(conn):

    if is_sqlite(conn):
        filename = "schema_sqlite.sql"
    else:
        filename = "schema_postgres.sql"

    with open(filename, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    if is_sqlite(conn):
        conn.executescript(schema_sql)
    else:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()

def upsert_user(conn, name: Optional[str]) -> Optional[int]:
    if not name:
        return None

    if is_sqlite(conn):
        execute_sql(conn, "INSERT OR IGNORE INTO users(name) VALUES (?)", (name,))
        row = execute_sql(conn, "SELECT id FROM users WHERE name = ?", (name,)).fetchone()
    else:
        execute_sql(conn, "INSERT INTO users(name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (name,))
        row = execute_sql(conn, "SELECT id FROM users WHERE name = %s", (name,)).fetchone()

    return row[0] if row else None


def upsert_label(conn, name: str) -> int:
    if is_sqlite(conn):
        execute_sql(conn, "INSERT OR IGNORE INTO labels(name) VALUES (?)", (name,))
        row = execute_sql(conn, "SELECT id FROM labels WHERE name = ?", (name,)).fetchone()
    else:
        execute_sql(conn, "INSERT INTO labels(name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (name,))
        row = execute_sql(conn, "SELECT id FROM labels WHERE name = %s", (name,)).fetchone()

    return row[0]

def insert_issue(conn,
                 issue_id: int,
                 number: Optional[int],
                 title: str,
                 state: Optional[str],
                 author_id: Optional[int],
                 created_at_iso: Optional[str],
                 updated_at_iso: Optional[str],
                 closed_at_iso: Optional[str],
                 comments_count: Optional[int],
                 url: Optional[str]):
    
    if is_sqlite(conn):
        execute_sql(
            conn,
            """
            INSERT OR REPLACE INTO issues(
                id, number, title, state, author_id,
                created_at, updated_at, closed_at, comments_count, url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (issue_id, number, title, state, author_id,
             created_at_iso, updated_at_iso, closed_at_iso,
             comments_count, url)
        )
    else:
        execute_sql(
            conn,
            """
            INSERT INTO issues(
                id, number, title, state, author_id,
                created_at, updated_at, closed_at, comments_count, url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                number = EXCLUDED.number,
                title = EXCLUDED.title,
                state = EXCLUDED.state,
                author_id = EXCLUDED.author_id,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                closed_at = EXCLUDED.closed_at,
                comments_count = EXCLUDED.comments_count,
                url = EXCLUDED.url
            """,
            (issue_id, number, title, state, author_id,
             created_at_iso, updated_at_iso, closed_at_iso,
             comments_count, url)
        )

def link_many_to_many(conn, issue_id: int, labels: Iterable[str], assignees: Iterable[str]):
    for lbl in labels or []:
        lbl_id = upsert_label(conn, lbl)
        if is_sqlite(conn):
            execute_sql(conn, "INSERT OR IGNORE INTO issue_labels(issue_id, label_id) VALUES (?, ?)", (issue_id, lbl_id))
        else:
            execute_sql(conn, "INSERT INTO issue_labels(issue_id, label_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (issue_id, lbl_id))

    for ass in assignees or []:
        uid = upsert_user(conn, ass)
        if uid is not None:
            if is_sqlite(conn):
                execute_sql(conn, "INSERT OR IGNORE INTO issue_assignees(issue_id, user_id) VALUES (?, ?)", (issue_id, uid))
            else:
                execute_sql(conn, "INSERT INTO issue_assignees(issue_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (issue_id, uid))

def load_csv_to_db(csv_path: str, db_url_or_path: str, use_postgres: bool = False):
    df = read_issues_csv(csv_path)

    def iso(x):
        return None if pd.isna(x) else pd.to_datetime(x).isoformat()

    # Conecta
    if use_postgres:
        print("🔗 Conectando ao PostgreSQL...")
        conn = psycopg2.connect(db_url_or_path)
    else:
        print("🔗 Conectando ao SQLite...")
        conn = sqlite3.connect(db_url_or_path)

    ensure_schema(conn)

    # Pré-insere autores únicos
    unique_authors = sorted(set(a for a in df["AUTHOR"].fillna("") if a))
    if use_postgres:
        with conn.cursor() as cur:
            execute_values(cur, "INSERT INTO users(name) VALUES %s ON CONFLICT DO NOTHING", [(a,) for a in unique_authors])
        conn.commit()
    else:
        conn.executemany("INSERT OR IGNORE INTO users(name) VALUES (?)", [(a,) for a in unique_authors])

    # Processa issues
    for i, row in df.iterrows():
        issue_id = int(row["NUMBER"])
        number = row.get("NUMBER")
        title = str(row.get("TITLE") or "").strip() or f"Issue {issue_id}"
        state = (row.get("STATE") or "").strip() or None
        author_name = (row.get("AUTHOR") or "").strip() or None
        created_at_iso = iso(row.get("CREATED_AT"))
        updated_at_iso = iso(row.get("UPDATED_AT"))
        closed_at_iso = iso(row.get("CLOSED_AT"))
        comments_count = row.get("COMMENTS")
        url = (row.get("URL") or "").strip() or None

        author_id = upsert_user(conn, author_name) if author_name else None
        insert_issue(conn, issue_id, number, title, state, author_id,
                     created_at_iso, updated_at_iso, closed_at_iso,
                     comments_count, url)
        link_many_to_many(conn, issue_id, row.get("LABELS") or [], row.get("ASSIGNEES") or [])

        if use_postgres and (i + 1) % 100 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    print(f"✅ {len(df)} issues carregadas com sucesso!")

if __name__ == "__main__":
    # SQLite
    # load_csv_to_db("jabref.csv", "issues.sqlite", use_postgres=False)

    # PostgreSQL
    # load_csv_to_db("jabref.csv", os.getenv("DATABASE_URL"), use_postgres=True)
    pass
