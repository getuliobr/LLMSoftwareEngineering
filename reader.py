import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from typing import Optional, Iterable
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

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
        # FIXED: Changed filename to match what you saved
        filename = "msr_challenge.sql"
    else:
        filename = "schema_postgres.sql"

    with open(filename, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    if is_sqlite(conn):
        # Temporarily disable foreign keys during schema creation
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(schema_sql)
        conn.execute("PRAGMA foreign_keys = ON")
    else:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()

def safe_insert_df(conn, df: pd.DataFrame, table_name: str, batch_size: int = 1000):
    """Safely insert dataframe into table with batch processing"""
    if df is None or df.empty:
        print(f"⚠️  No data to insert for {table_name}")
        return 0
    
    # Convert datetime columns to ISO format strings
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda x: None if pd.isna(x) else x.isoformat())
    
    # Replace NaN with None for proper NULL handling
    df = df.where(pd.notnull(df), None)
    
    try:
        total_inserted = 0
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            if is_sqlite(conn):
                batch.to_sql(table_name, conn, if_exists='append', index=False)
            else:
                # FIXED: Correct execute_values usage for PostgreSQL
                cols = ','.join(batch.columns)
                insert_query = f"INSERT INTO {table_name} ({cols}) VALUES %s"
                
                with conn.cursor() as cur:
                    execute_values(cur, insert_query, batch.values.tolist())
            
            total_inserted += len(batch)
            if (i + batch_size) % 5000 == 0:
                print(f"   ... {total_inserted} rows inserted")
                # FIXED: Commit for both SQLite and PostgreSQL periodically
                conn.commit()
        
        # FIXED: Commit for both databases at end of table
        conn.commit()
            
        print(f"✅ Inserted {total_inserted:,} rows into {table_name}")
        return total_inserted
        
    except Exception as e:
        print(f"❌ Error inserting into {table_name}: {e}")
        if not is_sqlite(conn):
            conn.rollback()
        return 0

def print_dataset_columns(dataset_base: str, load_sequence: list):
    """Print columns for each dataset to compare with schema"""
    print("\n" + "="*60)
    print("📋 DATASET COLUMN ANALYSIS")
    print("="*60 + "\n")
    
    for item in load_sequence:
        table_name = item[0]
        parquet_files = item[1:] if len(item) > 2 else [item[1]]
        
        for parquet_file in parquet_files:
            try:
                file_path = f"{dataset_base}/{parquet_file}"
                df = pd.read_parquet(file_path)
                print(f"Table: {table_name} (from {parquet_file})")
                print(f"Columns ({len(df.columns)}): {', '.join(df.columns)}")
                print(f"Row count: {len(df):,}\n")
                break
            except Exception as e:
                if len(parquet_files) > 1:
                    continue
                else:
                    print(f"❌ Could not load {parquet_file}: {e}\n")
                    break
    
    print("="*60 + "\n")

def load_hf_dataset_to_db(db_url_or_path: str, use_postgres: bool = False, debug_columns: bool = False):
    """Load AIDev dataset from HuggingFace into database"""
    
    # Connect to database
    if use_postgres:
        print("🔗 Connecting to PostgreSQL...")
        conn = psycopg2.connect(db_url_or_path)
    else:
        print("🔗 Connecting to SQLite...")
        conn = sqlite3.connect(db_url_or_path)
        # Disable foreign keys during bulk load for SQLite

        # Ensure schema exists
        print("📋 Creating schema...")
        ensure_schema(conn)
        conn.execute("PRAGMA foreign_keys = OFF")

    dataset_base = "hf://datasets/hao-li/AIDev"
    
    # Define load order (respecting foreign key dependencies)
    load_sequence = [
        ("user", "all_user.parquet"),
        ("repository", "all_repository.parquet"),
        ("pull_request", "all_pull_request.parquet"),
        ("pr_task_type", "pr_task_type.parquet"),
        ("pr_reviews", "pr_reviews.parquet"),
        ("pr_review_comments", "pr_review_comments_v2.parquet", "pr_review_comments.parquet"),  # Try v2 first
        ("pr_comments", "pr_comments.parquet"),
        ("issue", "issue.parquet"),
        ("related_issue", "related_issue.parquet"),
        ("pr_commits", "pr_commits.parquet"),
        ("pr_timeline", "pr_timeline.parquet"),
        ("pr_commit_details", "pr_commit_details.parquet"),
    ]

    # If debug mode, print columns and exit
    if debug_columns:
        print_dataset_columns(dataset_base, load_sequence)
        conn.close()
        return

    print("\n📦 Loading datasets from HuggingFace...\n")
    
    stats = {}
    
    for item in load_sequence:
        table_name = item[0]
        parquet_files = item[1:] if len(item) > 2 else [item[1]]
        
        print(f"📥 Loading {table_name}...")
        
        df = None
        for parquet_file in parquet_files:
            try:
                file_path = f"{dataset_base}/{parquet_file}"
                df = pd.read_parquet(file_path)
                print(f"   Found {len(df):,} rows in {parquet_file}")
                break
            except Exception as e:
                if len(parquet_files) > 1:
                    print(f"   ⚠️  Could not load {parquet_file}, trying alternative...")
                    continue
                else:
                    print(f"   ❌ Error loading {parquet_file}: {e}")
                    break
        
        if df is not None:
            count = safe_insert_df(conn, df, table_name)
            stats[table_name] = count
        else:
            stats[table_name] = 0
        
        print()

    # Final commit
    conn.commit()
    
    # Re-enable foreign keys for SQLite
    if is_sqlite(conn):
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
    
    # Print summary statistics
    print("\n" + "="*50)
    print("📊 DATABASE STATISTICS")
    print("="*50)
    
    for table_name, count in stats.items():
        print(f"{table_name:.<30} {count:>15,} rows")
    
    print("="*50)
    print(f"✅ Total rows loaded: {sum(stats.values()):,}")
    print("="*50 + "\n")
    
    conn.close()
    print("🎉 All data loaded successfully!")

if __name__ == "__main__":
    # First run with debug_columns=True to see what columns exist
    # load_hf_dataset_to_db("msr_challenge.sqlite", use_postgres=False, debug_columns=True)
    
    # Then run the actual load
    load_hf_dataset_to_db("msr_challenge.sqlite", use_postgres=False)