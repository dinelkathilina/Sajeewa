import unittest
from backend.ocr_processor import OCRProcessor
import pandas as pd

class TestQuotationParsing(unittest.TestCase):
    def setUp(self):
        self.processor = OCRProcessor()

    def test_parse_quotation_text(self):
        # Simulated OCR text from a quotation
        text = """
        VENDOR QUOTATION
        Date: 2024-01-01
        
        Item Description Qty Unit Rate Amount
        
        1. Supply of Concrete Grade 30 10 m3 15,000.00 150,000.00
        2. Steel Reinforcement Bar 500 kg 250.00 125,000.00
        
        Subtotal: 275,000.00
        Total: 275,000.00
        """
        
        df = self.processor._text_to_dataframe_quotation(text)
        
        self.assertFalse(df.empty, "DataFrame should not be empty")
        # Print for debug
        if len(df) != 2:
            print(f"\nDebug DF:\n{df.to_string()}\n")
            
        self.assertEqual(len(df), 2, f"Should have 2 items, got {len(df)}")
        
        # Check Item 1
        item1 = df.iloc[0]
        self.assertIn("Concrete Grade 30", item1['description'])
        self.assertEqual(item1['rate'], 15000.0)
        
        # Check Item 2
        item2 = df.iloc[1]
        self.assertIn("Steel Reinforcement", item2['description'])
        self.assertEqual(item2['rate'], 250.0)

    def test_parse_quotation_noisy(self):
        # Noisy text
        text = """
        Quotation Ref: Q-123
        
        Excavation in soft soil
        Qty: 100 Rate: 450.00 Amount: 45,000.00
        
        Transport of material
        50 km @ 120.00 = 6,000.00
        """
        
        df = self.processor._text_to_dataframe_quotation(text)
        
        # Should catch "Excavation..." line
        # The line "Qty: 100 Rate: 450.00 Amount: 45,000.00" has numbers
        # 100, 450.00, 45000.00
        # Rate = 450.00
        
        self.assertFalse(df.empty)
        
        # Find item with rate 450
        item = df[df['rate'] == 450.0]
        self.assertFalse(item.empty)
        # Description might be messy ("Excavation... Qty: Rate:") or just the line content
        # My heuristic takes the line content minus numbers
        # "Qty:  Rate:  Amount: " -> "Qty: Rate: Amount:"
        
        # The line "50 km @ 120.00 = 6,000.00"
        # Numbers: 50, 120, 6000
        # Rate = 120.0
        item2 = df[df['rate'] == 120.0]
        self.assertFalse(item2.empty)

if __name__ == '__main__':
    unittest.main()
