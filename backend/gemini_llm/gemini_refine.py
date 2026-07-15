import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root (ml/) is on sys.path for cross-package imports
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.ml_models.tests.predict import predict_career

load_dotenv()

logger = logging.getLogger(__name__)

# Prefer the modern Google GenAI package, but fall back to the deprecated google-generativeai API
genai = None
genai_client = None
_genai_is_modern = False
_genai_supports_generative_model = False

try:
    import google.genai as _genai
    genai = _genai
    _genai_is_modern = hasattr(genai, "Client")
    _genai_supports_generative_model = hasattr(genai, "GenerativeModel")
except Exception:
    try:
        import google.generativeai as _genai
        genai = _genai
        _genai_is_modern = False
        _genai_supports_generative_model = hasattr(genai, "GenerativeModel")
    except Exception:
        logger.warning("Google Generative AI client library is not installed or cannot be imported.")

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if GEMINI_API_KEY and genai is not None:
    if _genai_is_modern and hasattr(genai, "Client"):
        try:
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as exc:
            logger.warning("Failed to initialize Google GenAI client: %s", exc)
            genai_client = None
    elif hasattr(genai, "configure"):
        genai.configure(api_key=GEMINI_API_KEY)
    elif _genai_supports_generative_model:
        # Older google-generativeai clients use model-level configuration with a global API key.
        logger.info("Using legacy Google Generative AI client without explicit client initialization.")
    else:
        logger.warning("Loaded Google GenAI library but could not configure an API client.")

# Define static local career recommendations for the 10 target classes
LOCAL_CAREER_GUIDANCE = {
    "Agriculture & Environmental Sciences": {
        "description": "This path is focused on modern food production, biotechnology, smart farming, and environmental management. Nigeria's agricultural sector is undergoing a technology revolution, offering opportunities in agribusiness, soil science, forestry, and sustainable resource management.",
        "actionable_steps": [
            "Focus on biology, chemistry, and agricultural science in your school curriculum.",
            "Read about modern agricultural techniques such as vertical farming, soil-less cultivation (hydroponics), and drone technology in agriculture.",
            "Prepare for the JAMB examinations focusing on English, Biology, Chemistry, and Agricultural Science/Physics."
        ]
    },
    "Business & Finance": {
        "description": "This path covers financial management, accounting, corporate finance, investment banking, and the rapidly growing fintech sector in Nigeria. Roles in this field are crucial for running corporate enterprises, banking institutions, and venture funds.",
        "actionable_steps": [
            "Focus on mathematics, economics, financial accounting, and commerce in school.",
            "Read local and international financial news (e.g. BusinessDay, fintech blogs) to understand banking, inflation, and investment.",
            "Practice quantitative analysis and analytical reasoning, and prepare for JAMB (English, Mathematics, Economics, and Financial Accounting/Commerce)."
        ]
    },
    "Computer Science & IT": {
        "description": "This path deals with software engineering, cybersecurity, data science, networking, and system administration. Nigeria's technology ecosystem is one of the most vibrant on the continent, offering tremendous careers in tech hubs like Yaba and Ikeja.",
        "actionable_steps": [
            "Prioritize mathematics, further mathematics, and computer studies in your academic work.",
            "Start learning coding basics (like Python, HTML/CSS, or JavaScript) through free portals like freeCodeCamp, W3Schools, or Sololearn.",
            "Build small software scripts, participate in coding clubs or competitions, and prepare for JAMB (English, Mathematics, Physics, and Chemistry)."
        ]
    },
    "Creative Arts & Design": {
        "description": "This path embraces graphic design, fine arts, fashion, music production, digital animation, and user interface (UI/UX) design. Nigeria's Nollywood, Afrobeat, and design industries are globally recognized, offering rewarding paths for creative minds.",
        "actionable_steps": [
            "Build a personal portfolio of your sketches, digital art designs, creative writing, or music mixes.",
            "Learn digital design software such as Figma, Canva, or Photoshop through free YouTube tutorials.",
            "Select creative arts and literature in school, and select JAMB subjects in the arts/humanities track."
        ]
    },
    "Education & Humanities": {
        "description": "This path is dedicated to teaching, history, languages, philosophy, and human services. It prepares you for careers in educational planning, public relations, writing, educational technology, and school leadership.",
        "actionable_steps": [
            " excel in literature-in-english, history, and local languages (Yoruba/Igbo/Hausa).",
            "Volunteer to tutor junior students in your school or community to build your teaching and communication skills.",
            "Plan your JAMB subject combination with English, Literature, Christian/Islamic studies or History, and Government."
        ]
    },
    "Engineering & Technology": {
        "description": "This path involves civil, electrical, mechanical, mechanical, and chemical engineering. It focuses on design, construction, robotics, power systems, and infrastructure development, which are essential for Nigeria's development.",
        "actionable_steps": [
            "Maintain strong grades in mathematics, further mathematics, physics, and chemistry.",
            "Read about how machines work, build physical models (e.g., electronic boards, small structural models), and join your school's Jet Club.",
            "Prepare for JAMB by mastering English, Mathematics, Physics, and Chemistry."
        ]
    },
    "Entrepreneurship & Management": {
        "description": "This path concentrates on building startups, project management, sales, marketing, and corporate administration. It teaches you how to coordinate teams, manage business budgets, and grow small-to-medium businesses.",
        "actionable_steps": [
            "Focus on commerce, marketing, economics, and civic education.",
            "Take the lead in group school projects, and read books on leadership, time management, and business operations.",
            "Practice writing simple business pitches, and select commerce/marketing and economics for JAMB."
        ]
    },
    "Law & Social Sciences": {
        "description": "This path explores legal frameworks, human rights, sociology, political science, and international relations. Lawyers and social scientists in Nigeria play critical roles in corporate counsel, civil rights, policy-making, and diplomacy.",
        "actionable_steps": [
            "Focus heavily on literature-in-english, government, civic education, and history.",
            "Join your school's debating society, press club, or mock trials to improve public speaking, logical analysis, and essay writing.",
            "Select JAMB subject combination of English, Literature, Government, and Christian/Islamic studies or Economics."
        ]
    },
    "Mass Communication & Media": {
        "description": "This path centers on journalism, broadcasting, public relations, and digital content creation. It is vital for news networks, radio stations, digital media, advertising agencies, and corporate communications in Nigeria.",
        "actionable_steps": [
            "Practice writing articles, blogs, or scripting short videos, and work on public speaking or broadcasting skills.",
            "Learn basic video/audio editing tools (like CapCut, Audacity, or Premiere Pro) and write for the school press club.",
            "Select English, Literature, Government, and an arts/social science elective for JAMB."
        ]
    },
    "Medicine & Health Sciences": {
        "description": "This path covers medicine, pharmacy, nursing, dentistry, medical lab sciences, and public health. Highly prestigious and critically needed, it offers opportunities to save lives in hospitals and health-tech startups.",
        "actionable_steps": [
            "Maintain exceptional grades in biology, chemistry, physics, and mathematics.",
            "Read about anatomy, basic healthcare practices, and first aid, or volunteer/observe at a local clinic if possible.",
            "Ensure you choose JAMB subjects: English, Biology, Chemistry, and Physics."
        ]
    }
}


def generate_local_fallback(xgb_result, test_scores, profile):
    predicted_career = xgb_result.get("predicted_career", "Computer Science & IT")
    
    # Fallback to default if predicted_career is not in the guidance dict
    guidance = LOCAL_CAREER_GUIDANCE.get(predicted_career, LOCAL_CAREER_GUIDANCE["Computer Science & IT"])
    
    department = profile.get("Department", "Science")
    gender = profile.get("Gender", "Student")
    school_type = profile.get("School_Type", "Government School")
    
    apt = test_scores.get("aptitude_score_10", 5.0)
    cog = test_scores.get("cognitive_score_10", 5.0)
    psy = test_scores.get("psychometric_avg_5", 3.0)
    per = test_scores.get("sentiment_avg_5", 3.0)
    
    # Analyze strengths based on scores
    strengths = []
    if apt >= 7.5:
        strengths.append("High Aptitude Score: Demonstrates excellent logical and mathematical reasoning ability.")
    else:
        strengths.append("Capable Problem Solving: Possesses steady analytical skills suited for structured problem solving.")
        
    if cog >= 7.5:
        strengths.append("Excellent Cognitive Processing: Quick learning speed, strong memory, and spatial/pattern recognition.")
    else:
        strengths.append("Solid Processing Skills: Steady attention to detail and good comprehension of new concepts.")
        
    if psy >= 4.0:
        strengths.append("High Professional Drive: Demonstrates strong initiative, independent learning interest, and career motivation.")
    if per >= 4.0:
        strengths.append("Excellent Team Alignment: Strong organizational and interpersonal habits suited for team collaboration and leadership.")
    elif per <= 2.5:
        strengths.append("Independent Work Style: Prefers autonomous focus and working quietly on tasks without team distractions.")
        
    strengths.append(f"Academic Department Alignment: Your department selection ({department}) aligns directly with this recommendation path.")
    
    strengths_html = "\n".join([f"- {s}" for s in strengths])
    steps_html = "\n".join([f"{i+1}. {step}" for i, step in enumerate(guidance["actionable_steps"])])
    
    summary = f"""### Career Pathway: {predicted_career}

    {guidance['description']}

    ### Key Strengths Detected:
    {strengths_html}

    ### Actionable Next Steps:
    {steps_html}

    *(Note: These career recommendations are locally generated by our rule-based expert engine based on your academic profile and test performance.)*"""
    
    return summary


def gemini_final_prediction(xgb_result, test_scores, profile):
    # Try calling Google Generative AI first
    if GEMINI_API_KEY and genai is not None:
        prompt = f"""
You are a career guidance mentor for Nigerian secondary school students (JSS–SSS level).

Student profile:
- School Type: {profile.get('School_Type')}
- Academic Department: {profile.get('Department')}
- Mathematics grade: {profile.get('Mathematics')}
- English grade: {profile.get('English')}
- XGBoost Model Prediction: {xgb_result}
- Graded Test Scores:
  - Aptitude Score: {test_scores.get('aptitude_score_10')}/10
  - Cognitive Score: {test_scores.get('cognitive_score_10')}/10
  - Psychometric Average: {test_scores.get('psychometric_avg_5')}/5 (RIASEC Interest scale)
  - Personality Average: {test_scores.get('sentiment_avg_5')}/5 (Big Five Behavioral scale)

Write a highly encouraging, structured career recommendation. Structure it as follows:
1. "### Career Pathway: [Career Category]"
   A short explanation of the predicted career path in a Nigerian context (e.g. opportunities in fintech, agribusiness, health-tech, Nollywood, etc.).
2. "### Key Strengths Detected"
   A list of strengths shown by the student based on their academic and test results.
3. "### Actionable Next Steps"
   3 specific next steps for a student in Nigeria (e.g., target WAEC requirements, online study resources, typical JAMB subject combinations).

Be extremely encouraging. Speak directly to the student.
"""
        for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                if genai_client is not None:
                    response = genai_client.models.generate_content(model=model_name, contents=prompt)
                elif _genai_supports_generative_model and hasattr(genai, "GenerativeModel"):
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                else:
                    logger.warning("Google Generative AI library loaded, but no supported generation API is available.")
                    break
                text = getattr(response, "text", "") or ""
                if text.strip():
                    return {"summary": text.strip(), "fallback_prediction": xgb_result}
            except Exception as exc:
                logger.warning("Gemini model %s failed: %s", model_name, exc)

    # Local fallback if Gemini fails or API key is not configured/revoked
    fallback_text = generate_local_fallback(xgb_result, test_scores, profile)
    return {
        "summary": fallback_text,
        "fallback_prediction": xgb_result,
        "is_fallback": True
    }


def recommend_with_gemini(student_profile, test_scores, student_id=None):
    xgb_result = predict_career(student_profile)
    return gemini_final_prediction(xgb_result, test_scores, student_profile)