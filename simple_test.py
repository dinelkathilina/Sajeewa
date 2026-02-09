"""Simple database test"""
import sys
sys.path.insert(0, 'backend')

try:
    print("Importing database...")
    from backend.database import init_db, SessionLocal, VariationType
    
    print("Initializing database...")
    init_db()
    
    print("Creating session...")
    db = SessionLocal()
    
    print("Querying variation types...")
    types = db.query(VariationType).all()
    print(f"Found {len(types)} variation types")
    
    for t in types:
        print(f"  - {t.code}: {t.name}")
    
    db.close()
    print("\n✓ Database test passed!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
