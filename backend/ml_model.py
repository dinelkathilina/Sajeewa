from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import Ridge
import pandas as pd
import numpy as np
import os
import json
from groq import Groq
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

class MLModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.boq_df = None
        self.tfidf_matrix = None
        self.cost_model = Ridge(alpha=1.0)
        self.duration_model = Ridge(alpha=1.0)
        self.is_fitted = False
        self.is_duration_fitted = False
        
        # Initialize Groq Client
        self.groq_client = None
        groq_key = os.getenv("GROQ_API_KEY")
        print(f"DEBUG: MLModel init - GROQ_API_KEY found: {bool(groq_key)}")
        if groq_key:
            print(f"DEBUG: MLModel init - Key starts with: {groq_key[:5]}")
            try:
                self.groq_client = Groq(api_key=groq_key)
                print("DEBUG: MLModel init - Groq client created successfully")
            except Exception as e:
                print(f"DEBUG: MLModel init - Error creating Groq client: {e}")
        else:
            print("DEBUG: MLModel init - GROQ_API_KEY is missing from environment")

    def fit_boq(self, boq_items):
        if not boq_items: return
        data = [{'id': item.id, 'project_id': item.project_id, 'description': item.description, 'rate': item.rate, 'quantity': item.quantity, 'is_fixed_rate': item.is_fixed_rate} for item in boq_items]
        self.boq_df = pd.DataFrame(data)
        
        # TF-IDF for similarity
        self.tfidf_matrix = self.vectorizer.fit_transform(self.boq_df['description'])
        
        # Train Cost Model (if enough data)
        # Filter out items with 0 rate
        train_df = self.boq_df[self.boq_df['rate'] > 0]
        if len(train_df) >= 3:
            y = train_df['rate'].values
            # We must transform only the training descriptions
            X = self.vectorizer.transform(train_df['description'])
            self.cost_model.fit(X, y)
            self.is_fitted = True
        else:
            self.is_fitted = False

    def fit_activities(self, activities):
        """Train duration model on activities"""
        if not activities: return
        data = [{'description': a.description, 'duration': a.duration} for a in activities if a.duration > 0]
        if not data: return
        
        df = pd.DataFrame(data)
        if len(df) >= 3:
            # Re-use the same vectorizer? Or a new one?
            # Re-using might be tricky if vocab differs. 
            # But creating a new one specifically for duration seems safer.
            # Ideally share for memory, but separating is cleaner for accuracy.
            # Let's use the MAIN vectorizer for now, assuming BOQ descriptions cover construction terms.
            # BUT fit_boq resets it. If fit_activities is called later, transform might fail on new words.
            # Better to have a separate vectorizer for duration or re-fit on combined vocab.
            # Simplified approach: Use a separate vectorizer for simplicity.
            self.duration_vectorizer = TfidfVectorizer(stop_words='english')
            X = self.duration_vectorizer.fit_transform(df['description'])
            y = df['duration'].values
            self.duration_model.fit(X, y)
            self.is_duration_fitted = True

    def predict_duration(self, description):
        """Predict duration in days"""
        if not getattr(self, 'is_duration_fitted', False):
            return 0.0, 0.0
            
        try:
            vec = self.duration_vectorizer.transform([description])
            duration = self.duration_model.predict(vec)[0]
            return max(0.1, float(duration)), 1.0 # Placeholder confidence
        except:
            return 0.0, 0.0

    def predict_rate(self, description):
        """
        Predict rate for a description using the trained regression model.
        Returns: (predicted_rate, confidence_score)
        """
        if not self.is_fitted:
            return 0.0, 0.0
            
        try:
            vec = self.vectorizer.transform([description])
            rate = self.cost_model.predict(vec)[0]
            
            # Confidence proxy: Max similarity to known items
            # If we are predicting something very different from training data, confidence is low.
            similarities = cosine_similarity(vec, self.tfidf_matrix).flatten()
            confidence = float(np.max(similarities)) if len(similarities) > 0 else 0.0
            
            return max(0.0, float(rate)), confidence
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0.0, 0.0

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

    def parse_instruction(self, text, project_context=None, chat_history=None, session_metadata=None):
        """
        Enhanced instruction parsing with FIDIC workflow support
        """
        context_str = f"\nPROJECT BOQ CONTEXT (Samples):\n{project_context}" if project_context else ""
        history_str = ""
        if chat_history:
            history_str = "\nCONVERSATION HISTORY:\n" + "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_history[-10:]])  # Last 10 messages
        
        # Check session metadata for current state
        session_state = session_metadata or {}
        variation_type = session_state.get('variation_type')
        collected_details = session_state.get('collected_details', {})
        
        # Build dynamic prompt based on workflow state
        if not variation_type:
            # Step 1: Variation Type Selection
            prompt = f"""
You are an Expert AI Quantity Surveyor (QS) and Variation Assistant.

User Query: "{text}"
{history_str}
{context_str}

WORKFLOW STATE: Variation Type Selection

Instructions:
1. If the user is asking about a variation or change, guide them to select a FIDIC variation type.
2. Present the 6 FIDIC variation types clearly:
   - Type 1: Quantity Changes
   - Type 2: Quality/Characteristics Changes
   - Type 3: Levels/Positions/Dimensions Changes
   - Type 4: Omission of Work
   - Type 5: Additional Work/Plant/Materials
   - Type 6: Sequence/Timing Changes
3. Ask the user to select which type best describes their variation.
4. If the user's query clearly indicates a specific type, suggest it and ask for confirmation.

MANDATORY JSON Output Format:
{{
    "reply": "Your natural language response",
    "workflow_state": "type_selection",
    "suggested_type": "TYPE1" | "TYPE2" | "TYPE3" | "TYPE4" | "TYPE5" | "TYPE6" | null,
    "command": null
}}
Only return JSON.
"""
        elif not collected_details.get('complete'):
            # Step 2: Collect Variation Details (Questionnaire)
            missing_fields = []
            if not collected_details.get('affected_items'): missing_fields.append("Affected BOQ Items")
            if not collected_details.get('quantity_changes'): missing_fields.append("Quantity Changes")
            if not collected_details.get('specification_changes'): missing_fields.append("Specification Changes")
            if not collected_details.get('method_changes'): missing_fields.append("Method Changes")
            if not collected_details.get('location_changes'): missing_fields.append("Location Changes")
            if not collected_details.get('affected_activities'): missing_fields.append("Affected Activities")
            
            prompt = f"""
You are an Expert AI Quantity Surveyor (QS) and Variation Assistant.

User Query: "{text}"
{history_str}
{context_str}

WORKFLOW STATE: Collecting Variation Details
Selected Variation Type: {variation_type}
Collected Details So Far: {collected_details}
MISSING DETAILS: {missing_fields}

Instructions:
1. Check the user's latest query for any of the missing details.
2. If any information is found, extract it and update the JSON.
3. Your reply should:
   - Acknowledge information provided.
   - Ask for the NEXT missing detail from the list: {missing_fields}.
   - Be professional and helpful.
4. If ALL details are provided (or the user says they have no more info), set "complete": true in extracted_data.

MANDATORY JSON Output Format:
{{
    "reply": "Your natural language response asking for the next detail",
    "workflow_state": "collecting_details",
    "extracted_data": {{
        "affected_items": ["item description 1"] or null,
        "quantity_changes": "description/values" or null,
        "specification_changes": "description" or null,
        "method_changes": "description" or null,
        "location_changes": "description" or null,
        "affected_activities": ["activity name 1"] or null,
        "complete": true | false
    }},
    "command": null
}}
Only return JSON.
"""
        elif not collected_details.get('additional_files_asked'):
            # Step 3: Ask for Additional Files
            prompt = f"""
You are an Expert AI Quantity Surveyor (QS) and Variation Assistant.

User Query: "{text}"
{history_str}
{context_str}

WORKFLOW STATE: Requesting Additional Files
Selected Variation Type: {variation_type}
Collected Details: {collected_details}

Instructions:
1. Ask the user if they have additional supporting documents:
   - BSR (Basic Schedule of Rates)
   - HSR (Historical Schedule of Rates)
   - Quotations from suppliers
   - Specifications
   - Drawings
2. Explain that these files will help in accurate rate determination.
3. If they say yes, instruct them on how to upload.
4. If they say no, proceed to evaluation.

MANDATORY JSON Output Format:
{{
    "reply": "Your natural language response",
    "workflow_state": "requesting_files",
    "proceed_to_evaluation": true | false,
    "command": null
}}
Only return JSON.
"""
        else:
            # Step 4: Evaluation and Command Extraction
            prompt = f"""
You are an Expert AI Quantity Surveyor (QS) and Variation Assistant.

User Query: "{text}"
{history_str}
{context_str}

WORKFLOW STATE: Evaluation
Selected Variation Type: {variation_type}
Collected Details: {collected_details}

Instructions:
1. Analyze the collected information and prepare for cost/time evaluation.
2. Extract specific commands for evaluation:
   - change_spec: Material/specification changes
   - change_qty: Quantity changes
   - delay: Time impact analysis
3. Provide professional QS advice and insights.

MANDATORY JSON Output Format:
{{
    "reply": "Your natural language response",
    "workflow_state": "evaluation",
    "command": {{
        "intent": "change_spec" | "change_qty" | "delay" | null,
        "description": "EXACT description from BOQ",
        "new_material": "name if change_spec",
        "quantity": numerical value or null
    }}
}}
Only return JSON.
"""

        if self.groq_client:
            try:
                print(f"DEBUG: Attempting Groq call with model qwen/qwen3-32b")
                response = self.groq_client.chat.completions.create(
                    model="qwen/qwen3-32b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_completion_tokens=4096,
                    top_p=0.95,
                    reasoning_effort="default",
                    stream=False
                )
                print("DEBUG: Groq call successful.")
                content = response.choices[0].message.content
                
                # Check for thinking blocks and extract JSON
                if "<think>" in content:
                    content = content.split("</think>")[-1].strip()

                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: Extract JSON from markdown blocks if present
                    import re
                    match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if match:
                        return json.loads(match.group(1))
                    
                    # Last ditch effort: find first { and last }
                    start = content.find('{')
                    end = content.rfind('}')
                    if start != -1 and end != -1:
                        return json.loads(content[start:end+1])
                    raise
            except Exception as e:
                print(f"ERROR: Groq failed: {e}")

        return {'reply': "AI services are currently offline.", 'workflow_state': 'error', 'command': None}
