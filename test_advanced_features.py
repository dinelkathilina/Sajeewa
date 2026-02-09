"""
Test Advanced Backend Features: Validation Engine & PDF Generation
"""
import os
from sqlalchemy.orm import Session
from backend.database import SessionLocal, Variation, VariationDetail, Project, Session as UserSession
from backend.validation_engine import ValidationEngine
from backend.pdf_utils import PDFGenerator
from datetime import datetime

# Setup DB session
db = SessionLocal()

def create_test_data(db: Session):
    print("Creating test data...")
    # 1. Create Project
    project = Project(
        name="Test Project for Validation",
        description="Testing detailed validation logic"
    )
    db.add(project)
    db.commit()
    
    # 2. Create Session
    session = UserSession(project_id=project.id)
    db.add(session)
    db.commit()
    
    # 3. Create Variation (Type 1: Quantity Change)
    variation = Variation(
        project_id=project.id,
        session_id=session.id,
        variation_type_id=1,
        description="Increase in Guard Stones",
        status="pending",
        cost_impact=42500.0,
        time_impact=5.0
    )
    db.add(variation)
    db.commit()
    
    # 4. Create Variation Details (Simulate issues for validation)
    # Detail 1: Normal item
    d1 = VariationDetail(
        variation_id=variation.id,
        boq_item_id=1,
        original_description="Guard Stones",
        original_quantity=150,
        new_quantity=200,
        original_rate=850.0,
        new_rate=850.0,
        cost_impact=42500.0
    )
    
    # Detail 2: Potential Duplicate (Double Counting Check)
    d2 = VariationDetail(
        variation_id=variation.id,
        boq_item_id=1,  # Same BOQ ID
        original_description="Guard Stones (Extra)",
        original_quantity=10,
        new_quantity=10,
        original_rate=850.0,
        new_rate=850.0,
        cost_impact=8500.0
    )
    
    # Detail 3: Excessive Rate Increase (Reasonableness Check)
    d3 = VariationDetail(
        variation_id=variation.id,
        boq_item_id=2,
        original_description="Concrete Grade 30",
        original_quantity=50,
        new_quantity=50,
        original_rate=15000.0,
        new_rate=25000.0,  # > 50% increase
        cost_impact=500000.0
    )
    
    db.add_all([d1, d2, d3])
    db.commit()
    
    return variation.id

def test_validation_engine(variation_id):
    print(f"\nTesting Validation Engine for Variation {variation_id}...")
    validator = ValidationEngine(db)
    
    # Run validation
    results = validator.validate_variation(variation_id)
    
    print("\n--- Validation Results ---")
    print(f"Valid: {results['valid']}")
    print(f"Status: {results.get('status')}")
    
    print("\nWarnings detected:")
    for w in results['warnings']:
        print(f"  [WARN] {w}")
        
    print("\nErrors detected:")
    for e in results['errors']:
        print(f"  [ERR] {e}")
        
    # Verify we caught the injected issues
    has_double_counting = any("double counting" in w.lower() for w in results['warnings'])
    has_rate_increase = any("rate increased" in w.lower() for w in results['warnings'])
    
    if has_double_counting and has_rate_increase:
        print("\n✅ SUCCESS: Validation Engine correctly identified issues.")
    else:
        print("\n❌ FAILED: Validation Engine missed some issues.")

def test_pdf_generation(variation_id):
    print(f"\nTesting PDF Generation for Variation {variation_id}...")
    
    try:
        # Fetch variation data
        variation = db.query(Variation).get(variation_id)
        
        # Prepare data for PDF
        proposal_data = {
            'variation_id': variation.id,
            'project_name': variation.project.name,
            'variation_type': 'Type 1: Quantity Changes',  # Mock for test
            'items': [
                {
                    'description': d.original_description,
                    'original_qty': d.original_quantity,
                    'new_qty': d.new_quantity,
                    'original_rate': d.original_rate,
                    'new_rate': d.new_rate,
                    'amount': d.cost_impact
                } for d in variation.details
            ],
            'total_cost': sum(d.cost_impact for d in variation.details),
            'time_impact': variation.time_impact,
            'status': variation.status,
            'validation_results': {
                'status': variation.validation_status,
                'notes': variation.validation_notes
            }
        }
        
        # Output path
        output_file = "test_proposal.pdf"
        
        # Generate
        PDFGenerator.generate_variation_proposal(proposal_data, output_file)
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"\n✅ SUCCESS: PDF generated successfully ({size} bytes)")
            print(f"File saved to: {os.path.abspath(output_file)}")
        else:
            print("\n❌ FAILED: PDF file was not created.")
            
    except Exception as e:
        print(f"\n❌ ERROR: PDF Generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        var_id = create_test_data(db)
        test_validation_engine(var_id)
        test_pdf_generation(var_id)
    finally:
        db.close()
