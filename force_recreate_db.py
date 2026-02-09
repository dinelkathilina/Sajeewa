"""
Force Complete Database Recreation
"""
import sys
import os
sys.path.insert(0, 'backend')

# Delete existing database
if os.path.exists('construction_data.db'):
    os.remove('construction_data.db')
    print("Deleted existing database")

# Import all models to ensure they're registered
from backend.database import (
    Base, engine, SessionLocal,
    Project, Session, ChatMessage, VariationType,
    BOQItem, RateBreakdown, Variation, Activity,
    AdditionalFile, VariationDetail
)

print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Tables created!")

# Seed variation types
from backend.database import seed_variation_types
db = SessionLocal()
seed_variation_types(db)
db.close()

print("\nVerifying schema...")
import sqlite3
conn = sqlite3.connect('construction_data.db')
cursor = conn.cursor()

print("\nPROJECTS TABLE:")
cursor.execute("PRAGMA table_info(projects)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

print("\nCHAT_MESSAGES TABLE:")
cursor.execute("PRAGMA table_info(chat_messages)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

print("\nSESSIONS TABLE:")
cursor.execute("PRAGMA table_info(sessions)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

conn.close()
print("\nDatabase ready!")
