import unittest
from backend.ml_model import MLModel
from collections import namedtuple
import pandas as pd

class TestMLModel(unittest.TestCase):
    def setUp(self):
        self.model = MLModel()
        
    def test_train_and_predict(self):
        # Create mock items
        Item = namedtuple('Item', ['id', 'project_id', 'description', 'rate', 'quantity', 'is_fixed_rate'])
        items = [
            Item(1, 1, "Supply of Grade 30 Concrete", 15000.0, 10, False),
            Item(2, 1, "Pouring Concrete", 5000.0, 10, False),
            Item(3, 1, "Valid Concrete Mix", 15500.0, 10, False),
            Item(4, 1, "Reinforcement Steel", 250.0, 100, False),
            Item(5, 1, "Steel Bars", 260.0, 100, False),
            Item(6, 1, "High Grade Concrete", 16000.0, 5, False)
        ]
        
        self.model.fit_boq(items)
        self.assertTrue(self.model.is_fitted)
        
        # Predict Concrete
        rate, conf = self.model.predict_rate("Supply Concrete")
        print(f"Pred Concrete: {rate}, Conf: {conf}")
        # Expect roughly weighted average of concrete items (15000, 15500, 16000)
        self.assertTrue(14000 < rate < 17000, f"Rate {rate} out of range for Concrete")
        
        # Predict Steel
        rate, conf = self.model.predict_rate("Steel Reinforcement")
        print(f"Pred Steel: {rate}, Conf: {conf}")
        self.assertTrue(240 < rate < 270, f"Rate {rate} out of range for Steel")
        
        # Predict Unknown
        rate, conf = self.model.predict_rate("Space Shuttle")
        print(f"Pred Unknown: {rate}, Conf: {conf}")
        # Confidence should be low
        self.assertTrue(conf < 0.2, f"Confidence {conf} too high for unknown item")

if __name__ == '__main__':
    unittest.main()
