import unittest
import pandas as pd
import os
from backend.engine import CostEngine
from unittest.mock import MagicMock

class TestBOQValidation(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.engine = CostEngine(self.mock_db)
        self.test_dir = "test_data"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

    def tearDown(self):
        # Cleanup with retry/ignore errors
        try:
            import shutil
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception as e:
            print(f"Cleanup error: {e}")

    def test_valid_csv(self):
        path = os.path.join(self.test_dir, "valid.csv")
        df = pd.DataFrame({
            'Item No': ['1', '2'],
            'Description': ['Concrete', 'Steel'],
            'Unit': ['m3', 'kg'],
            'Qty': [10, 100],
            'Rate': [500, 50]
        })
        try:
            df.to_csv(path, index=False)
        except Exception as e:
            self.fail(f"Failed to create CSV: {e}")
        
        try:
            result = self.engine.validate_boq_file(path)
            self.assertTrue(result['valid'], f"Valid CSV failed. Errors: {result.get('errors')}")
        except Exception as e:
            self.fail(f"Validation raised exception: {e}")

    def test_missing_column_csv(self):
        path = os.path.join(self.test_dir, "invalid.csv")
        df = pd.DataFrame({
            'Item No': ['1'],
            'Qty': [10],
            'Rate': [500]
        })
        df.to_csv(path, index=False)
        
        result = self.engine.validate_boq_file(path)
        self.assertFalse(result['valid'])
        # Check if 'Description' is mentioned in errors
        found = any("Missing" in e and "description" in e.lower() for e in result['errors'])
        self.assertTrue(found, f"Expected validation error about missing description, got: {result.get('errors')}")

    def test_valid_excel(self):
        code_path = os.path.join(self.test_dir, "valid.xlsx")
        df = pd.DataFrame({
            'Item No': ['1'],
            'Description': ['Concrete'],
            'Unit': ['m3'],
            'Quantity': [10],
            'Rate': [500]
        })
        df.to_excel(code_path, index=False)
        
        result = self.engine.validate_boq_file(code_path)
        self.assertTrue(result['valid'], f"Valid Excel failed: {result.get('errors')}")

    def test_excel_multiple_sheets(self):
        path = os.path.join(self.test_dir, "multi_sheet.xlsx")
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({'A': [1]}).to_excel(writer, sheet_name='Summary')
            pd.DataFrame({
                'Item': ['1'],
                'Description': ['Valid Item'],
                'Qty': [1],
                'Rate': [1]
            }).to_excel(writer, sheet_name='Bill No 1', index=False)
            
        result = self.engine.validate_boq_file(path)
        self.assertTrue(result['valid'], f"Multi-sheet Excel failed: {result.get('errors')}")

    def test_invalid_format(self):
        path = os.path.join(self.test_dir, "test.txt")
        with open(path, "w") as f:
            f.write("Some text")
            
        result = self.engine.validate_boq_file(path)
        self.assertFalse(result['valid'])
        # Precise check
        expected = "Unsupported file format. Please upload .xlsx, .xls, or .csv"
        self.assertIn(expected, result['errors'])

if __name__ == '__main__':
    unittest.main()
