import copy
from pymongo import MongoClient

# Connexion à MongoDB (doit être lancé en local)
client = MongoClient("mongodb://localhost:27017/")
db = client["petzi_webhook"]
collection = db["events"]

def save_event(payload):
    """
    Sauvegarde un événement dans MongoDB sans modifier le dictionnaire original.
    """
    try:
        payload_copy = copy.deepcopy(payload)
        result = collection.insert_one(payload_copy)
        print(f"Event saved with ID: {result.inserted_id}")
    except Exception as e:
        print(f"Error saving event to MongoDB: {e}")
