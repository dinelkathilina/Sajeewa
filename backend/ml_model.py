from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
import os
import json
import google.generativeai as genai

class MLModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.boq_df = None
        self.tfidf_matrix = None
        
        # Initialize Gemini if key exists
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

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
        Uses Gemini if available, otherwise falls back to Regex.
        """
        # Get sample items for context if available
        context_items = ""
        if self.boq_df is not None:
            samples = self.boq_df['description'].head(10).tolist()
            context_items = "\nSample items in BOQ: " + ", ".join(samples)

        if self.model:
            try:
                prompt = f"""
                You are a Construction Variation Assistant.
                User Request: "{text}"
                {context_items}

                Task:
                1. If the user wants to change an item (qty or material), return JSON:
                   {{"intent": "change_spec" | "change_qty", "description": "old item name", "new_material": "new material", "quantity": val}}
                2. If the user wants to check a delay, return JSON:
                   {{"intent": "delay", "description": "task name", "quantity": days}}
                3. If it is a general question or greeting, return JSON:
                   {{"intent": "conversational", "reply": "A helpful response based on the BOQ samples provided above"}}
                4. Otherwise: {{"intent": "unknown"}}

                Only return the JSON.
                """
                response = self.model.generate_content(prompt)
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_json)
                return data
            except Exception as e:
                print(f"Gemini parsing failed: {e}")
        
        # Regex Fallback (Improved Local Intelligence)
        import re
        text = text.lower()
        result = {'intent': 'unknown', 'description': None, 'quantity': None, 'unit': None}
        
        # 1. Greetings
        if any(greet in text for greet in ['hi', 'hello', 'hey', 'start']):
            result['intent'] = 'conversational'
            result['reply'] = "Hello! I am your project assistant. You can ask me to 'Change [item] to [new material]' or 'Delay [task] by 10 days'."
            return result

        # 2. List items query
        if any(kw in text for kw in ['what', 'show', 'list', 'see', 'items']):
            if self.boq_df is not None:
                samples = self.boq_df['description'].head(5).tolist()
                result['intent'] = 'conversational'
                result['reply'] = f"I can see {len(self.boq_df)} items in the BOQ. Examples include: " + ", ".join(samples)
                return result

        # 3. Change Qty
        qty_match = re.search(r'(?:quantity|qty) of (.+) to (\d+)', text)
        if qty_match:
            result['intent'] = 'change_qty'
            result['description'] = qty_match.group(1).strip()
            result['quantity'] = float(qty_match.group(2))
            return result

        # 4. Change Spec
        change_match = re.search(r'change (.+) to (.+)', text)
        if change_match:
            result['intent'] = 'change_spec'
            result['description'] = change_match.group(1).strip()
            result['new_material'] = change_match.group(2).strip()
            return result
            
        # 5. Delay
        delay_match = re.search(r'delay (.+) by (\d+) days?', text)
        if delay_match:
            result['intent'] = 'delay'
            result['description'] = delay_match.group(1).strip()
            result['quantity'] = float(delay_match.group(2))
            return result

        return result

