from backend.database import engine
from sqlalchemy import text

def migrate():
    print("Starting migration...")
    with engine.connect() as conn:
        # Check if columns exist first (SQLite specific check)
        cursor = conn.execute(text("PRAGMA table_info(projects)"))
        columns = [row[1] for row in cursor]
        
        if 'boq_filename' not in columns:
            print("Adding column boq_filename...")
            conn.execute(text("ALTER TABLE projects ADD COLUMN boq_filename VARCHAR"))
        
        if 'description' not in columns:
            print("Adding column description...")
            conn.execute(text("ALTER TABLE projects ADD COLUMN description VARCHAR"))
        
        conn.commit()
    print("Migration successful.")

if __name__ == "__main__":
    migrate()
