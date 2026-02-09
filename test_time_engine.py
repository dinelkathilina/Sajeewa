import unittest
from unittest.mock import MagicMock
from backend.engine import TimeEngine
import networkx as nx

class TestTimeEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TimeEngine()
        # Create a simple project graph: A -> B -> C
        self.engine.graph.add_node('A', name='Task A', duration=5.0)
        self.engine.graph.add_node('B', name='Task B', duration=10.0)
        self.engine.graph.add_node('C', name='Task C', duration=5.0)
        self.engine.graph.add_edge('A', 'B')
        self.engine.graph.add_edge('B', 'C')
        
    def test_cpm_calculation(self):
        """Test basic CPM calculation"""
        cpm = self.engine.calculate_cpm_full()
        
        # A: 0-5
        self.assertEqual(cpm['A']['es'], 0.0)
        self.assertEqual(cpm['A']['ef'], 5.0)
        
        # B: 5-15
        self.assertEqual(cpm['B']['es'], 5.0)
        self.assertEqual(cpm['B']['ef'], 15.0)
        
        # C: 15-20
        self.assertEqual(cpm['C']['es'], 15.0)
        self.assertEqual(cpm['C']['ef'], 20.0)
        
        self.assertTrue(cpm['A']['is_critical'])
        self.assertTrue(cpm['B']['is_critical'])
        self.assertTrue(cpm['C']['is_critical'])

    def test_eot_calculation_critical(self):
        """Test EOT when critical task is delayed"""
        # Delay Task B by 5 days
        eot, breakdown = self.engine.calculate_eot('Task B', 5.0)
        
        self.assertEqual(eot, 5.0)
        self.assertEqual(breakdown['original_project_duration'], 20.0)
        self.assertEqual(breakdown['new_project_duration'], 25.0)
        self.assertTrue(breakdown['is_on_critical_path'])
        
    def test_eot_calculation_non_critical(self):
        """Test EOT when non-critical task is delayed"""
        # Add non-critical task D parallel to B: A -> D -> C
        # D duration = 2.0. Path A-D-C = 5+2+5=12. Float = 20-12=8.
        self.engine.graph.add_node('D', name='Task D', duration=2.0)
        self.engine.graph.add_edge('A', 'D')
        self.engine.graph.add_edge('D', 'C')
        
        # Delay Task D by 5 days (Float is 8, so no EOT)
        eot, breakdown = self.engine.calculate_eot('Task D', 5.0)
        
        self.assertEqual(eot, 0.0)
        self.assertFalse(breakdown['is_on_critical_path'])
        self.assertIn("absorbed within the float", breakdown['justification'])

    def test_generate_gantt_data(self):
        """Test Gantt data generation"""
        data = self.engine.generate_gantt_data()
        
        self.assertGreater(len(data), 2)
        task_a = next(t for t in data if t['name'] == 'Task A')
        self.assertEqual(task_a['start_day'], 0.0)
        self.assertEqual(task_a['end_day'], 5.0)
        self.assertIn('is_critical', task_a)

if __name__ == '__main__':
    unittest.main()
