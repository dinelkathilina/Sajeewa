"""
Quick Backend Test Script
Tests core functionality of the enhanced backend
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 60)
    print("TESTING MODULE IMPORTS")
    print("=" * 60)
    
    try:
        from backend import database
        print("✓ database.py imported successfully")
        
        from backend import engine
        print("✓ engine.py imported successfully")
        
        from backend import ml_model
        print("✓ ml_model.py imported successfully")
        
        from backend import ocr_processor
        print("✓ ocr_processor.py imported successfully")
        
        from backend import session_manager
        print("✓ session_manager.py imported successfully")
        
        from backend import validation_engine
        print("✓ validation_engine.py imported successfully")
        
        from backend import pdf_utils
        print("✓ pdf_utils.py imported successfully")
        
        from backend import main
        print("✓ main.py imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database initialization"""
    print("\n" + "=" * 60)
    print("TESTING DATABASE")
    print("=" * 60)
    
    try:
        from backend.database import init_db, SessionLocal, VariationType
        
        # Initialize database
        init_db()
        print("✓ Database initialized")
        
        # Check variation types
        db = SessionLocal()
        types = db.query(VariationType).all()
        print(f"✓ Found {len(types)} FIDIC variation types")
        
        for vtype in types:
            print(f"  - {vtype.code}: {vtype.name}")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ocr_availability():
    """Test OCR processor availability"""
    print("\n" + "=" * 60)
    print("TESTING OCR PROCESSOR")
    print("=" * 60)
    
    try:
        from backend.ocr_processor import ocr_processor, OCR_AVAILABLE
        
        if OCR_AVAILABLE:
            print("✓ OCR libraries available (pytesseract, pdf2image)")
            print("  Note: Tesseract OCR must be installed separately")
        else:
            print("⚠ OCR libraries not available")
            print("  Install with: pip install pytesseract pdf2image Pillow")
        
        return True
    except Exception as e:
        print(f"✗ OCR test error: {e}")
        return False

def test_engines():
    """Test engine initialization"""
    print("\n" + "=" * 60)
    print("TESTING ENGINES")
    print("=" * 60)
    
    try:
        from backend.database import SessionLocal
        from backend.engine import CostEngine, TimeEngine
        
        db = SessionLocal()
        
        # Test CostEngine
        cost_engine = CostEngine(db)
        print("✓ CostEngine initialized")
        
        # Test TimeEngine
        time_engine = TimeEngine(db_session=db)
        print("✓ TimeEngine initialized")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Engine test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_manager():
    """Test session manager"""
    print("\n" + "=" * 60)
    print("TESTING SESSION MANAGER")
    print("=" * 60)
    
    try:
        from backend.database import SessionLocal, Project
        from backend.session_manager import SessionManager
        
        db = SessionLocal()
        
        # Create test project if needed
        project = db.query(Project).first()
        if not project:
            project = Project(name="Test Project")
            db.add(project)
            db.commit()
            db.refresh(project)
            print(f"✓ Created test project (ID: {project.id})")
        else:
            print(f"✓ Using existing project (ID: {project.id})")
        
        # Test session creation
        sm = SessionManager(db)
        session = sm.create_session(project.id, metadata={"test": True})
        print(f"✓ Created session (ID: {session.id}, Key: {session.session_key})")
        
        # Test message addition
        sm.add_message(session.id, "user", "Test message")
        print("✓ Added test message")
        
        # Test context retrieval
        context = sm.get_session_context(session.id)
        print(f"✓ Retrieved session context ({len(context['conversation_history'])} messages)")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Session manager test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_engine():
    """Test validation engine"""
    print("\n" + "=" * 60)
    print("TESTING VALIDATION ENGINE")
    print("=" * 60)
    
    try:
        from backend.database import SessionLocal
        from backend.validation_engine import ValidationEngine
        
        db = SessionLocal()
        validator = ValidationEngine(db)
        print("✓ ValidationEngine initialized")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Validation engine test error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("BACKEND COMPONENT TESTS")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("Module Imports", test_imports()))
    results.append(("Database", test_database()))
    results.append(("OCR Processor", test_ocr_availability()))
    results.append(("Engines", test_engines()))
    results.append(("Session Manager", test_session_manager()))
    results.append(("Validation Engine", test_validation_engine()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Backend is ready.")
        print("\nNext steps:")
        print("1. Start backend: python -m backend.main")
        print("2. Visit API docs: http://localhost:8000/docs")
        print("3. Test file upload and chat endpoints")
    else:
        print("\n⚠ Some tests failed. Please review errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
