import os
import sqlite3
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load Postgres DB connection
load_dotenv()
pg_url = os.getenv("DATABASE_URL")
if not pg_url or pg_url.startswith("sqlite"):
    print("Error: DATABASE_URL must be set to the PostgreSQL instance (e.g. postgresql://olrac:password@localhost:5432/olrac_signage)")
    exit(1)

# SQLite DB connection
sqlite_path = "../backups/olrac_signage.db.bak"
if not os.path.exists(sqlite_path):
    print(f"Error: SQLite backup not found at {sqlite_path}")
    exit(1)

pg_engine = sqlalchemy.create_engine(pg_url)
SessionLocal = sessionmaker(bind=pg_engine)
session = SessionLocal()

sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()

# Order matters for foreign keys
TABLES = [
    "plans",
    "organizations",
    "users",
    "playlists",
    "screen_groups",
    "screens",
    "content",
    "playlist_items",
    "schedules",
    "subscriptions",
    "webhook_events"
]

print("Starting data migration from SQLite to Postgres...")

with pg_engine.connect() as pg_conn:
    # SQLite stores naive text for datetimes and every one of them was written as UTC
    # (models.utcnow). Passed straight into a timestamptz column, Postgres resolves the
    # missing offset with the session TimeZone instead — on an IST host that moved every
    # migrated instant 5h30m earlier. Pinning the session to UTC makes the implicit
    # offset the correct one, for every table and column, without touching the values.
    pg_conn.execute(sqlalchemy.text("SET TIME ZONE 'UTC'"))

    # Disable triggers/constraints for bulk load
    # pg_conn.execute(sqlalchemy.text("SET session_replication_role = 'replica';"))

    for table in TABLES:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        if not rows:
            print(f"Skipping {table} (0 rows)")
            continue
            
        columns = rows[0].keys()
        col_names = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])
        
        insert_sql = sqlalchemy.text(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})")
        
        # Convert sqlite rows to dicts and handle booleans
        data = []
        for row in rows:
            d = dict(row)
            if 'is_active' in d:
                d['is_active'] = bool(d['is_active'])
            data.append(d)
        pg_conn.execute(insert_sql, data)
        print(f"Migrated {len(data)} rows to {table}")

    # Re-enable triggers/constraints
    # pg_conn.execute(sqlalchemy.text("SET session_replication_role = 'origin';"))
    pg_conn.commit()

    # Advance every identity sequence past the ids we just inserted.
    #
    # Inserting explicit primary keys does NOT move Postgres sequences, so without
    # this every sequence still sits at 1 and the very next INSERT fails with
    # "duplicate key value violates unique constraint". Matching row counts hide it
    # completely: the data looks perfect and then no TV can ever register again.
    print("\nResynchronising identity sequences...")
    sequences = pg_conn.execute(sqlalchemy.text("""
        SELECT t.relname AS table_name,
               a.attname AS column_name,
               pg_get_serial_sequence(t.relname, a.attname) AS sequence_name
        FROM pg_class t
        JOIN pg_attribute a ON a.attrelid = t.oid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relkind = 'r'
          AND a.attnum > 0
          AND pg_get_serial_sequence(t.relname, a.attname) IS NOT NULL
        ORDER BY t.relname
    """)).fetchall()

    for table_name, column_name, sequence_name in sequences:
        max_id = pg_conn.execute(
            sqlalchemy.text(f"SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}")
        ).scalar()
        # is_called=False on an empty table so the first row still gets id 1.
        pg_conn.execute(sqlalchemy.text(
            f"SELECT setval('{sequence_name}', GREATEST({max_id}, 1), {str(max_id > 0).lower()})"
        ))
        print(f"  {table_name}.{column_name} -> next id {max_id + 1}")
    pg_conn.commit()

print("Data migration complete!")
sqlite_conn.close()
session.close()
