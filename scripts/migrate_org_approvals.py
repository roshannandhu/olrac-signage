import sys, os
sys.path.insert(0, os.path.abspath("."))
from backend.database import engine
from sqlalchemy import text

def main():
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'pending_approval';
            ALTER TABLE organizations ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE organizations ADD COLUMN IF NOT EXISTS approved_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
            ALTER TABLE organizations ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR;
            CREATE TABLE IF NOT EXISTS system_settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description VARCHAR,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            UPDATE organizations SET status = 'active' WHERE id = 1;
            INSERT INTO system_settings (key, value, description, updated_at)
            VALUES ('universal_demo_video_url', '/uploads/f9863204-f997-4122-ac1b-a50157e3d905.mp4', 'Default Universal Demo Reel Video for unapproved screens', NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        """))
        conn.commit()
    print("Supabase DB migration for Organizations and SystemSettings applied successfully!")

if __name__ == "__main__":
    main()
