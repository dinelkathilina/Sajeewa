import unittest
from unittest.mock import MagicMock, patch
from backend.engine import CostEngine
from backend.database import Project, RateBreakdown
import pandas as pd
import os

class TestCostEngine(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.engine = CostEngine(self.mock_db)
        
        # Mock ML Model
        self.engine.ml_model = MagicMock()
        
    def test_calculate_new_rate_no_change(self):
        """Test rate remains same if thresholds not met"""
        item = {
            'project_id': 1,
            'rate': 100.0,
            'quantity': 1000.0,
            'is_fixed_rate': 0,
            'description': 'Test Item'
        }
        
        mock_project = Project(accepted_contract_amount=1000000.0)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        
        # Qty change 5% (below 10%)
        qty_change = 50.0 
        
        new_rate, source = self.engine.calculate_new_rate(item, qty_change)
        self.assertEqual(new_rate, 100.0)
        self.assertEqual(source, "Original Rate")

    def test_calculate_new_rate_threshold_met(self):
        """Test star rate derivation triggered when thresholds met"""
        item = {
            'project_id': 1,
            'rate': 100.0,
            'quantity': 1000.0,
            'is_fixed_rate': 0,
            'description': 'Test Item'
        }
        
        mock_project = Project(accepted_contract_amount=1000000.0) # 0.01% = 100.0
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        
        # Qty change 20% (above 10%)
        qty_change = 200.0 
        
        # Mock derivation to return a new rate and source
        self.engine.derive_star_rate = MagicMock(return_value=(120.0, "Derived Source"))
        
        new_rate, source = self.engine.calculate_new_rate(item, qty_change, unit_cost_change_pct=2.0)
        
        self.engine.derive_star_rate.assert_called_once()
        self.assertEqual(new_rate, 120.0)
        self.assertEqual(source, "Derived Source")

    def test_search_external_rates_bsr(self):
        """Test searching BSR file returns tuple"""
        # Create dummy BSR
        if not os.path.exists("uploaded_files"):
            os.makedirs("uploaded_files")
            
        bsr_content = "Item Description,Unit,Rate\nConcrete Grade 30,m3,25500.00\nReinforcement Bar,kg,450.00"
        with open("uploaded_files/BSR_2024.csv", "w") as f:
            f.write(bsr_content)
            
        try:
            rate, source = self.engine.search_external_rates("Concrete Grade 30 for columns")
            self.assertEqual(rate, 25500.00)
            self.assertEqual(source, "BSR_2024.csv")
            
            rate_fail, source_fail = self.engine.search_external_rates("Non existent item")
            self.assertEqual(rate_fail, 0.0)
            self.assertIsNone(source_fail)
        finally:
            # Cleanup
            if os.path.exists("uploaded_files/BSR_2024.csv"):
                os.remove("uploaded_files/BSR_2024.csv")

if __name__ == '__main__':
    unittest.main()
