import sqlite3
from pathlib import Path
from typing import Optional, Iterable
import pandas as pd

# --- your existing reader ---
def read_issues_csv(csv_file):
    df = pd.read_csv(csv_file)

    # Convert date columns to datetime (nullable)
    for col in ["CREATED_AT", "UPDATED_AT", "CLOSED_AT"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Lists split on ';'
    df["LABELS"] = df["LABELS"].fillna("").apply(lambda x: [lbl.strip() for lbl in str(x).split(";") if lbl.strip()])
    df["ASSIGNEES"] = df["ASSIGNEES"].fillna("").apply(lambda x: [a.strip() for a in str(x).split(";") if a.strip()])

    return df

with open("schema.sql", "r", encoding="utf-8") as f:
    SCHEMA_SQL = f.read()

def ensure_schema(conn: sqlite3.Connection):
    conn.executescript(SCHEMA_SQL)

def upsert_user(conn: sqlite3.Connection, name: Optional[str]) -> Optional[int]:
    if not name:
        return None
    conn.execute("INSERT OR IGNORE INTO users(name) VALUES (?)", (name,))
    row = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None

def upsert_label(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO labels(name) VALUES (?)", (name,))
    row = conn.execute("SELECT id FROM labels WHERE name = ?", (name,)).fetchone()
    return row[0]

def insert_issue(conn: sqlite3.Connection,
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
    conn.execute(
        """
        INSERT OR REPLACE INTO issues(
            id, number, title, state, author_id,
            created_at, updated_at, closed_at, comments_count, url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(issue_id) if issue_id is not None else None,
            int(number) if pd.notna(number) else None,
            title,
            state if state else None,
            author_id,
            created_at_iso,
            updated_at_iso,
            closed_at_iso,
            int(comments_count) if pd.notna(comments_count) else None,
            url if url else None,
        ),
    )

def link_many_to_many(conn: sqlite3.Connection,
                      issue_id: int,
                      labels: Iterable[str],
                      assignees: Iterable[str]):
    # Labels
    for lbl in labels or []:
        lbl_id = upsert_label(conn, lbl)
        conn.execute(
            "INSERT OR IGNORE INTO issue_labels(issue_id, label_id) VALUES (?, ?)",
            (issue_id, lbl_id),
        )
    # Assignees
    for ass in assignees or []:
        uid = upsert_user(conn, ass)
        if uid is not None:
            conn.execute(
                "INSERT OR IGNORE INTO issue_assignees(issue_id, user_id) VALUES (?, ?)",
                (issue_id, uid),
            )

def load_csv_to_sqlite(csv_path: str, sqlite_path: str = "issues.sqlite"):
    df = read_issues_csv(csv_path)

    # Convert timestamps to ISO strings (SQLite stores TEXT)
    def iso(x):
        if pd.isna(x):
            return None
        # ensure UTC-naive ISO 8601 string (or keep timezone if present)
        return pd.to_datetime(x).isoformat()

    sqlite_file = Path(sqlite_path)
    with sqlite3.connect(sqlite_file) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        ensure_schema(conn)

        with conn:  # transaction
            # Pre-insert unique authors for a small speedup (optional)
            unique_authors = sorted(set(a for a in df["AUTHOR"].fillna("") if a))
            conn.executemany(
                "INSERT OR IGNORE INTO users(name) VALUES (?)",
                [(a,) for a in unique_authors]
            )

            for _, row in df.iterrows():
                issue_id = int(row["ID"])
                number = row.get("NUMBER")
                title = str(row.get("TITLE") or "").strip()
                state = (row.get("STATE") or "").strip() or None
                author_name = (row.get("AUTHOR") or "").strip() or None
                created_at_iso = iso(row.get("CREATED_AT"))
                updated_at_iso = iso(row.get("UPDATED_AT"))
                closed_at_iso  = iso(row.get("CLOSED_AT"))
                comments_count = row.get("COMMENTS")
                url = (row.get("URL") or "").strip() or None

                # Author → users table
                author_id = upsert_user(conn, author_name) if author_name else None

                # Insert/replace issue
                insert_issue(
                    conn,
                    issue_id=issue_id,
                    number=number,
                    title=title or f"Issue {issue_id}",
                    state=state,
                    author_id=author_id,
                    created_at_iso=created_at_iso,
                    updated_at_iso=updated_at_iso,
                    closed_at_iso=closed_at_iso,
                    comments_count=comments_count,
                    url=url,
                )

                # Link labels & assignees
                labels = row.get("LABELS") or []
                assignees = row.get("ASSIGNEES") or []
                link_many_to_many(conn, issue_id, labels, assignees)

    print(f"Loaded {len(df)} issues into {sqlite_file.resolve()}")

if __name__ == "__main__":
    # Example usage:
    # load_csv_to_sqlite("jabref.csv", "issues.sqlite")
    pass
