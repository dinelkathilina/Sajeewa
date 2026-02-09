import unittest
from backend.engine import CostEngine
from backend.database import Base, Variation, VariationDetail, engine
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

class TestReviewLoop(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.engine = CostEngine(self.db)
        
        # Create Dummy Variation
        self.variation = Variation(description="Test Var", cost_impact=0.0)
        self.db.add(self.variation)
        self.db.commit()
        
        # Add Detail Items
        # Item 1: Qty change 10 -> 12, Rate 1000. Impact = (12*1000 - 10*1000) = 2000
        self.d1 = VariationDetail(variation_id=self.variation.id, original_quantity=10, new_quantity=12, original_rate=1000, new_rate=1000, cost_impact=2000)
        # Item 2: Rate change 500 -> 600, Qty 10. Impact = (10*600 - 10*500) = 1000
        self.d2 = VariationDetail(variation_id=self.variation.id, original_quantity=10, new_quantity=10, original_rate=500, new_rate=600, cost_impact=1000)
        
        self.db.add_all([self.d1, self.d2])
        self.db.commit()
        
        # Initial Calc
        self.engine.recalculate_variation_totals(self.variation.id)
        self.db.refresh(self.variation)
        print(f"Initial Cost: {self.variation.cost_impact}") # Should be 3000

    def tearDown(self):
        self.db.close()

    def test_update_detail(self):
        # User updates Item 1: New Qty 15 (was 12)
        # Old Val: 10 * 1000 = 10000
        # New Val: 15 * 1000 = 15000
        # Impact: 5000
        
        self.engine.update_variation_detail(self.d1.id, {"new_quantity": 15})
        
        self.db.refresh(self.d1)
        self.assertEqual(self.d1.new_quantity, 15)
        self.assertEqual(self.d1.cost_impact, 5000)
        
        # Check Total
        self.db.refresh(self.variation)
        # Total = 5000 (Item 1) + 1000 (Item 2) = 6000
        print(f"Updated Cost: {self.variation.cost_impact}")
        self.assertEqual(self.variation.cost_impact, 6000)

    def test_update_rate(self):
        # User updates Item 2: New Rate 700 (was 600)
        # Old Val: 10 * 500 = 5000
        # New Val: 10 * 700 = 7000
        # Impact: 2000
        
        self.engine.update_variation_detail(self.d2.id, {"new_rate": 700})
        
        self.db.refresh(self.d2)
        self.assertEqual(self.d2.new_rate, 700)
        self.assertEqual(self.d2.rate_source, "Manual Adjustment")
        self.assertEqual(self.d2.cost_impact, 2000)
        
        # Total = 2000 (Item 1 initial) + 2000 (Item 2) = 4000
        self.db.refresh(self.variation)
        self.assertEqual(self.variation.cost_impact, 4000)

if __name__ == '__main__':
    unittest.main()
