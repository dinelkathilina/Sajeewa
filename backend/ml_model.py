from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

class MLModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.boq_data = None
        self.tfidf_matrix = None

    def load_boq_data(self, boq_df):
        self.boq_data = boq_df
        self.tfidf_matrix = self.vectorizer.fit_transform(boq_df['description'])

    def find_similar_item(self, description):
        if self.tfidf_matrix is None:
            return None
        
        query_vec = self.vectorizer.transform([description])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)
        best_match_idx = similarities.argmax()
        
        return self.boq_data.iloc[best_match_idx]

    def predict_productivity(self, item_description, parameters):
        # Placeholder for productivity prediction logic
        # Could use regression model here
        return 1.0
