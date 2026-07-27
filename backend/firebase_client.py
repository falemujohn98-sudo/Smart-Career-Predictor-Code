import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = Path(__file__).resolve().parent
CRED_PATH = BASE_DIR / "careeriq-d0ce1-firebase-adminsdk.json"

_app = None
_db = None

def _ensure_initialized():
    global _app
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(CRED_PATH))
        _app = firebase_admin.initialize_app(cred)
    else:
        _app = firebase_admin.get_app()
    return _app

def get_db():
    global _db
    _ensure_initialized()
    if _db is not None:
        return _db
    _db = firestore.client()
    return _db

def verify_id_token(id_token: str):
    from firebase_admin import auth
    _ensure_initialized()
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Invalid or expired ID token: {e}")