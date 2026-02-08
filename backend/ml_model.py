from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np

class MLModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.boq_df = None
        self.tfidf_matrix = None

    def fit_boq(self, boq_items):
        """
        Trains the model on the current project's BOQ descriptions.
        boq_items: List of BOQItem objects
        """
        if not boq_items:
            return
        
        data = [{'id': item.id, 'description': item.description, 'rate': item.rate} for item in boq_items]
        self.boq_df = pd.DataFrame(data)
        self.tfidf_matrix = self.vectorizer.fit_transform(self.boq_df['description'])

    def find_similar_item(self, description, top_n=1):
        """
        Finds the most similar BOQ item to the given description.
        """
        if self.tfidf_matrix is None:
            return None
        
        query_vec = self.vectorizer.transform([description])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top matches
        best_match_indices = similarities.argsort()[-top_n:][::-1]
        
        results = []
        for idx in best_match_indices:
            if similarities[idx] > 0.1: # Minimum threshold
                item = self.boq_df.iloc[idx].to_dict()
                item['similarity'] = float(similarities[idx])
                results.append(item)
                
        return results[0] if results and top_n==1 else results

    def predict_productivity(self, item_description, complexity_factor=1.0):
        """
        Predicts productivity (m2/day) based on description and complexity.
        This is a heuristic/mockup as we lack historical data.
        """
        base_productivity = 50.0 # Default
        
        # Simple keyword heuristics
        desc = item_description.lower()
        if "granite" in desc: base_productivity = 15.0
        elif "marble" in desc: base_productivity = 20.0
        elif "ceramic" in desc: base_productivity = 40.0
        elif "carpet" in desc: base_productivity = 100.0
        
        return base_productivity / complexity_factor

    def parse_instruction(self, text):
        """
        Parses user text to extract intent and data.
        Returns dict with keys: intent, description, quantity, new_material
        """
        import re
        text = text.lower()
        result = {'intent': 'unknown', 'description': None, 'quantity': None, 'unit': None}
        
        # Regex for Quantity Change: "Change quantity of X to 500" or "Set qty of X to 500"
        qty_match = re.search(r'(?:quantity|qty) of (.+) to (\d+)', text)
        if qty_match:
            result['intent'] = 'change_qty'
            result['description'] = qty_match.group(1).strip()
            result['quantity'] = float(qty_match.group(2))
            return result

        # Regex for Material/Spec Change: "Change X to Y"
        change_match = re.search(r'change (.+) to (.+)', text)
        if change_match:
            result['intent'] = 'change_spec'
            result['description'] = change_match.group(1).strip()
            result['new_material'] = change_match.group(2).strip()
            return result
            
        # Regex for Delay: "Delay [Task] by [X] days"
        delay_match = re.search(r'delay (.+) by (\d+) days?', text)
        if delay_match:
            result['intent'] = 'delay'
            result['description'] = delay_match.group(1).strip()
            result['quantity'] = float(delay_match.group(2))
            return result

        return result

