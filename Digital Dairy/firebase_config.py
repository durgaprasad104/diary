import firebase_admin
from firebase_admin import credentials, firestore, auth

# Initialize Firebase Admin
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
except ValueError as e:
    print("Firebase already initialized")

db = firestore.client()