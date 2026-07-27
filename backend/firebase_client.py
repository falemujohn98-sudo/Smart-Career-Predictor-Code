import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = Path(__file__).resolve().parent
CRED_PATH = BASE_DIR / "careeriq-d0ce1-firebase-adminsdk.json"

_app = None
_db = None


def get_db():
    global _app, _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(CRED_PATH))
        _app = firebase_admin.initialize_app(cred)
    else:
        _app = firebase_admin.get_app()

    _db = firestore.client()
    return _db