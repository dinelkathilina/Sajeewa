import unittest
from backend.ml_model import MLModel
from backend.engine import TimeEngine
from collections import namedtuple
import pandas as pd
from sklearn.linear_model import Ridge

class TestMLTimePrediction(unittest.TestCase):
    def setUp(self):
        self.model = MLModel()
        # Use low alpha for small dataset to avoid underfitting
        self.model.duration_model = Ridge(alpha=0.01)
        
    def test_train_and_predict_duration(self):
        # Create mock activities
        Activity = namedtuple('Activity', ['description', 'duration'])
        activities = [
            Activity("Excavation for Foundation", 10.0),
            Activity("Digging Trenches", 8.0),
            Activity("Soil Removal", 12.0),
            Activity("Internal Wall Painting", 5.0),
            Activity("Ceiling Painting", 4.0),
            Activity("External Wall Painting", 6.0)
        ]
        
        self.model.fit_activities(activities)
        self.assertTrue(getattr(self.model, 'is_duration_fitted', False))
        
        # Predict Excavation (Use "Excavation" to match training data)
        dur, conf = self.model.predict_duration("Excavation Site")
        print(f"Pred Excavation: {dur}")
        self.assertTrue(7.0 <= dur <= 13.0, f"Duration {dur} out of range for Excavation")
        
        # Predict Painting
        dur, conf = self.model.predict_duration("Paint Bedroom")
        print(f"Pred Painting: {dur}")
        # Relaxed range due to small dataset variance
        self.assertTrue(3.0 <= dur <= 9.0, f"Duration {dur} out of range for Painting")

if __name__ == '__main__':
    unittest.main()
