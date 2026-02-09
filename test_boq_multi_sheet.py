import pandas as pd
import os
from sqlalchemy.orm import Session
from backend.engine import CostEngine
from backend.database import SessionLocal, Project

def setup_test_excel(file_path):
    # Sheet 1: GS (Summary) - This should be ignored or not cause failure if Bill 1 is valid
    df_gs = pd.DataFrame([
        ['General Summary', ''],
        ['Bill 1', 1000.0],
        ['Total', 1000.0]
    ], columns=['Description', 'Amount'])
    
    # Sheet 2: Bill 1 (Valid BOQ)
    df_bill = pd.DataFrame([
        ['1.1', 'Concrete work', 'm3', 10, 500, 5000],
        ['1.2', 'Steel work', 'kg', 100, 5, 500]
    ], columns=['Item', 'Description', 'Unit', 'Qty', 'Rate', 'Amount'])
    
    with pd.ExcelWriter(file_path) as writer:
        df_gs.to_excel(writer, sheet_name='GS', index=False)
        df_bill.to_excel(writer, sheet_name='Bill 1', index=False)

def test_validation():
    test_file = "test_multi_sheet.xlsx"
    setup_test_excel(test_file)
    
    db = SessionLocal()
    engine = CostEngine(db)
    
    try:
        print(f"Testing validation of {test_file}...")
        result = engine.validate_boq_file(test_file)
        print(f"Validation Result: {result['valid']}")
        if result['errors']:
            print(f"Errors: {result['errors']}")
        
        assert result['valid'] == True
        print("SUCCESS: Validation passed as expected.")
        
    finally:
        db.close()
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_validation()
