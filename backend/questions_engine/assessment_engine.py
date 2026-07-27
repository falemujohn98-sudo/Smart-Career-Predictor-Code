import json
import os
import secrets
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from random import Random

import bcrypt
from google.cloud.firestore_v1 import FieldFilter

# Ensure project root (ml/) is on sys.path for cross-package imports
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.ml_models.tests.predict import predict_career
from backend.firebase_client import get_db

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "assessment_questions.json"

TEST_CONFIG = [
    {"slug": "aptitude", "title": "Aptitude Test", "category": "aptitude", "question_count": 10},
    {"slug": "cognitive", "title": "Cognitive Test", "category": "cognitive", "question_count": 10},
    {"slug": "psychometric", "title": "Psychometric Test", "category": "psychometric", "question_count": 10},
    {"slug": "personality", "title": "Personality Test", "category": "personality", "question_count": 10},
]

STUDENTS_COLLECTION = "users"
ASSESSMENTS_COLLECTION = "assessments"


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def _load_question_bank() -> List[Dict[str, Any]]:
    if QUESTIONS_PATH.exists():
        with QUESTIONS_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return data
    return []


def _seed_question_bank_if_missing() -> List[Dict[str, Any]]:
    return _load_question_bank()


def get_question_bank_stats() -> Dict[str, Any]:
    questions = _load_question_bank()
    per_category = {}
    for category in ["aptitude", "cognitive", "psychometric", "personality"]:
        per_category[category] = sum(1 for q in questions if q.get("category") == category)
    return {"total_questions": len(questions), "per_category": per_category}


def get_student_attempt_count(student_id: str) -> int:
    db = get_db()
    docs = db.collection(ASSESSMENTS_COLLECTION).where(
        filter=FieldFilter("student_id", "==", student_id)
    ).stream()
    return sum(1 for _ in docs)


def _normalise_subject_category(value: Any) -> str:
    raw = str(value or "General").strip().lower()
    if "art" in raw:
        return "Arts"
    if "commercial" in raw or "business" in raw:
        return "Commercial"
    if "science" in raw:
        return "Science"
    return "General"


def _shuffle_options_for_question(question: Dict[str, Any], rng: Random) -> List[str]:
    options = list(question.get("options", []))
    if str(question.get("category", "")).lower() in {"aptitude", "cognitive"}:
        rng.shuffle(options)
    return options


def build_assessment_session(student_id: str, shuffle_seed: Optional[str] = None) -> Dict[str, Any]:
    student_row = db_get_student(student_id)
    dept = student_row.get("department", "Science") if student_row else "Science"
    dept = dept or "Science"

    subj_cat = _normalise_subject_category(dept)
    questions = _load_question_bank()
    attempt_count = get_student_attempt_count(student_id)
    session_seed = shuffle_seed or secrets.token_urlsafe(16)
    rng = Random(f"{student_id}-{attempt_count}-{session_seed}")

    tests = []
    for config in TEST_CONFIG:
        department_questions = [
            q for q in questions
            if str(q.get("category")).lower() == config["category"].lower()
            and _normalise_subject_category(q.get("subject_category")) == subj_cat
        ]
        general_questions = [
            q for q in questions
            if str(q.get("category")).lower() == config["category"].lower()
            and _normalise_subject_category(q.get("subject_category")) == "General"
        ]
        rng.shuffle(department_questions)
        rng.shuffle(general_questions)
        category_questions = department_questions + general_questions

        if len(category_questions) < config["question_count"]:
            extra_questions = [
                q for q in questions
                if str(q.get("category")).lower() == config["category"].lower()
                and q not in category_questions
            ]
            rng.shuffle(extra_questions)
            category_questions.extend(extra_questions)

        selected = category_questions[: config["question_count"]] if category_questions else []

        tests.append({
            "slug": config["slug"],
            "title": config["title"],
            "category": config["category"],
            "question_count": len(selected),
            "questions": [
                {
                    "id": q["id"],
                    "prompt": q["prompt"],
                    "options": _shuffle_options_for_question(q, rng),
                    "subject_category": q.get("subject_category", "General"),
                    "source": q.get("source", ""),
                }
                for q in selected
            ],
        })
    return {"student_id": student_id, "tests": tests, "created_at": str(uuid.uuid4())[:8]}


def firestore_server_timestamp():
    from firebase_admin import firestore
    return firestore.SERVER_TIMESTAMP


def save_assessment(student_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    assessment_id = str(uuid.uuid4())
    db.collection(ASSESSMENTS_COLLECTION).document(assessment_id).set({
        "student_id": student_id,
        "payload": json.dumps(payload),
        "created_at": firestore_server_timestamp(),
    })
    return {"assessment_id": assessment_id, "student_id": student_id}


def get_assessment_history(student_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    docs = (
        db.collection(ASSESSMENTS_COLLECTION)
        .where(filter=FieldFilter("student_id", "==", student_id))
        .order_by("created_at", direction="DESCENDING")
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append({
            "id": doc.id,
            "payload": json.loads(data.get("payload", "{}")),
            "created_at": str(data.get("created_at")),
        })
    return results


# DB Helper operations for Students
def db_create_student(student_data: dict) -> bool:
    db = get_db()
    student_id = student_data.get("id")
    if not student_id:
        return False

    email = student_data.get("email")
    if email:
        existing = db_get_student_by_email(email)
        if existing:
            return False

    data = dict(student_data)
    data["created_at"] = firestore_server_timestamp()
    db.collection(STUDENTS_COLLECTION).document(student_id).set(data)
    return True


def db_get_student_by_email(email: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    docs = db.collection(STUDENTS_COLLECTION).where(
        filter=FieldFilter("email", "==", email)
    ).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def db_get_student(student_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    doc = db.collection(STUDENTS_COLLECTION).document(student_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def db_update_student_profile(student_id: str, updates: dict) -> bool:
    db = get_db()
    try:
        db.collection(STUDENTS_COLLECTION).document(student_id).update(updates)
        return True
    except Exception:
        return False


# Grading function
def grade_answers(answers: Dict[str, str]) -> Dict[str, float]:
    questions = _load_question_bank()
    q_map = {q["id"]: q for q in questions}

    category_scores = {
        "aptitude": {"correct": 0, "total": 0},
        "cognitive": {"correct": 0, "total": 0},
        "psychometric": {"sum": 0, "total": 0},
        "personality": {"sum": 0, "total": 0},
    }

    psychometric_map = {
        "strongly disagree": 1.0,
        "disagree": 2.0,
        "neutral": 3.0,
        "agree": 4.0,
        "strongly agree": 5.0,
    }
    personality_map = {"never": 1.0, "sometimes": 2.0, "often": 4.0, "always": 5.0}

    for q_id, user_ans in answers.items():
        if q_id not in q_map:
            continue
        q = q_map[q_id]
        category = q["category"]

        if category in ["aptitude", "cognitive"]:
            category_scores[category]["total"] += 1
            if str(user_ans).strip().lower() == str(q["answer"]).strip().lower():
                category_scores[category]["correct"] += 1
        elif category == "psychometric":
            ans_clean = str(user_ans).strip().lower()
            val = psychometric_map.get(ans_clean, 3.0)
            category_scores["psychometric"]["sum"] += val
            category_scores["psychometric"]["total"] += 1
        elif category == "personality":
            ans_clean = str(user_ans).strip().lower()
            val = personality_map.get(ans_clean, 3.0)
            category_scores["personality"]["sum"] += val
            category_scores["personality"]["total"] += 1

    results = {}
    apt_stats = category_scores["aptitude"]
    results["aptitude_score_10"] = float(round((apt_stats["correct"] / apt_stats["total"]) * 10, 1)) if apt_stats["total"] > 0 else 5.0

    cog_stats = category_scores["cognitive"]
    results["cognitive_score_10"] = float(round((cog_stats["correct"] / cog_stats["total"]) * 10, 1)) if cog_stats["total"] > 0 else 5.0

    psy_stats = category_scores["psychometric"]
    results["psychometric_avg_5"] = float(round(psy_stats["sum"] / psy_stats["total"], 2)) if psy_stats["total"] > 0 else 3.0

    per_stats = category_scores["personality"]
    results["sentiment_avg_5"] = float(round(per_stats["sum"] / per_stats["total"], 2)) if per_stats["total"] > 0 else 3.0

    defaults = {
        "aptitude_score_10": 5.0,
        "cognitive_score_10": 5.0,
        "psychometric_avg_5": 3.0,
        "sentiment_avg_5": 3.0,
    }
    for k, v in defaults.items():
        if k not in results:
            results[k] = v

    return results


def run_recommendation(student_id: str, student_profile: Dict[str, Any]) -> Dict[str, Any]:
    prediction = predict_career(student_profile)
    assessment_session = build_assessment_session(student_id)
    result = {
        "student_id": student_id,
        "prediction": prediction,
        "assessment": assessment_session,
        "question_bank": get_question_bank_stats(),
    }
    save_assessment(student_id, result)
    return result