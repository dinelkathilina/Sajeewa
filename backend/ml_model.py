from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
import os
import json
from openai import OpenAI

class MLModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.boq_df = None
        self.tfidf_matrix = None
        
        # Initialize OpenRouter (Sole Provider)
        self.openrouter_client = None
        or_key = os.getenv("OPENROUTER_API_KEY")
        if or_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=or_key,
            )

    def fit_boq(self, boq_items):
        if not boq_items: return
        data = [{'id': item.id, 'description': item.description, 'rate': item.rate, 'quantity': item.quantity} for item in boq_items]
        self.boq_df = pd.DataFrame(data)
        self.tfidf_matrix = self.vectorizer.fit_transform(self.boq_df['description'])

    def find_similar_item(self, description, top_n=1):
        if self.tfidf_matrix is None: return None
        query_vec = self.vectorizer.transform([description])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        best_match_indices = similarities.argsort()[-top_n:][::-1]
        results = []
        for idx in best_match_indices:
            if similarities[idx] > 0.1:
                item = self.boq_df.iloc[idx].to_dict()
                item['similarity'] = float(similarities[idx])
                results.append(item)
        return results[0] if results and top_n==1 else results

    def predict_productivity(self, item_description, complexity_factor=1.0):
        base_productivity = 50.0
        desc = item_description.lower()
        if "granite" in desc: base_productivity = 15.0
        elif "marble" in desc: base_productivity = 20.0
        elif "ceramic" in desc: base_productivity = 40.0
        elif "carpet" in desc: base_productivity = 100.0
        return base_productivity / complexity_factor

    def parse_instruction(self, text, project_context=None):
        context_str = f"\nPROJECT BOQ CONTEXT (Samples):\n{project_context}" if project_context else ""
        prompt = f"""
        You are an Expert AI Quantity Surveyor and Variation Assistant.
        User Query: "{text}"
        {context_str}

        Instructions:
        1. Analyze the query against the Project BOQ provided.
        2. If the user wants to evaluate a variation, identify the EXACT item from context.
        3. Respond to the user naturally as a Quantity Surveyor.
        
        MANDATORY JSON Output Format:
        {{
            "reply": "Your natural language response",
            "command": {{
                "intent": "change_spec" | "change_qty" | "delay" | null,
                "description": "EXACT description from BOQ",
                "new_material": "name if change_spec",
                "quantity": numerical value or null
            }}
        }}
        Only return JSON.
        """

        if self.openrouter_client:
            try:
                print(f"DEBUG: Attempting OpenRouter call with model z-ai/glm-4.5-air:free")
                response = self.openrouter_client.chat.completions.create(
                    model="z-ai/glm-4.5-air:free",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                print("DEBUG: OpenRouter call successful.")
                content = response.choices[0].message.content
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: Extract JSON from markdown blocks if present
                    import re
                    match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if match:
                        return json.loads(match.group(1))
                    raise
            except Exception as e:
                print(f"ERROR: OpenRouter failed: {e}")
                if hasattr(e, 'response'):
                    print(f"DEBUG: Response body: {e.response.text}")

        return {'reply': "AI services are currently offline.", 'command': None}
