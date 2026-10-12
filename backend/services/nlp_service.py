"""
NLP Classifier and Inference Service
Public Grievance Auto-Routing System
"""

import os
import re
import joblib
import numpy as np

from backend.config import CLASS_MARGIN_THRESHOLD, CONFIDENCE_THRESHOLD

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "grievance_classifier.joblib")

DEPARTMENTS_META = {
    "roads": {
        "name": "Roads & Footpaths",
        "keywords": ["pothole", "crater", "road", "footpath", "divider", "asphalt", "paver", "gravel", "culvert", "flyover", "tar"]
    },
    "water_supply": {
        "name": "Water Supply & Pipelines",
        "keywords": ["water", "tap", "pipeline", "tanker", "leakage", "pressure", "muddy", "drinking", "contamination", "valve", "pump"]
    },
    "electricity": {
        "name": "Electricity & Streetlighting",
        "keywords": ["streetlight", "electric", "pole", "wire", "sparking", "transformer", "power", "darkness", "tripping", "short circuit"]
    },
    "sanitation": {
        "name": "Solid Waste & Sanitation",
        "keywords": ["garbage", "trash", "waste", "dustbin", "dead animal", "carcass", "sweeper", "dump", "rotting", "litter", "stench"]
    },
    "drainage": {
        "name": "Drainage & Sewerage",
        "keywords": ["drain", "sewer", "gutter", "manhole", "sewage", "stormwater", "overflow", "choked", "nullah", "sludge"]
    },
    "public_health": {
        "name": "Public Health & Pest Control",
        "keywords": ["mosquito", "dengue", "malaria", "fogging", "stray dog", "dog bite", "pest", "stagnant water", "health", "infestation", "larvae"]
    },
    "encroachment": {
        "name": "Encroachments & Town Planning",
        "keywords": ["encroachment", "illegal", "hawker", "stall", "footpath blocked", "unauthorized", "shed", "cart", "pavement blocked", "construction"]
    }
}

# Common Hindi/Marathi civic vocabulary, including Roman-script spellings.
# This lightweight normalization keeps the current model useful until a fully
# reviewed Indic-language training corpus is available.
INDIC_NORMALIZATION = {
    "सड़क": "road", "रस्ता": "road", "रस्ता खराब": "broken road", "खड्डा": "pothole",
    "पानी": "water", "पाणी": "water", "नल": "tap", "पाइप": "pipeline",
    "बिजली": "electricity", "वीज": "electricity", "तार": "wire", "दिवा": "streetlight",
    "कचरा": "garbage", "कूड़ा": "garbage", "घाण": "waste",
    "नाली": "drain", "गटार": "drain", "सीवर": "sewer",
    "मच्छर": "mosquito", "डेंगू": "dengue", "कुत्रा": "dog",
    "अतिक्रमण": "encroachment", "फुटपाथ": "footpath",
    "paani": "water", "pani": "water", "sadak": "road", "rasta": "road",
    "khadda": "pothole", "kachra": "garbage", "kooda": "garbage", "naali": "drain",
    "gutter": "drain", "bijli": "electricity", "taar": "wire", "machhar": "mosquito",
}

EMERGENCY_TERMS = [
    "live wire", "sparking", "fire hazard", "snapped wire", "open manhole", "death trap",
    "severe accident", "sinkhole", "dengue outbreak", "rabid dog", "dog bite", "poisonous",
    "flooding into house", "sewage backflow", "acute shortage", "toxic"
]

class GrievanceClassifier:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
            except Exception as e:
                print(f"Error loading model: {e}")
                self.model = None
        else:
            print(f"Model file not found at {MODEL_PATH}")

    def clean_text(self, text: str) -> str:
        text = text.lower()
        for source, replacement in INDIC_NORMALIZATION.items():
            text = text.replace(source, replacement)
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def detect_language(self, text: str) -> str:
        if re.search(r"[\u0900-\u097f]", text):
            marathi_markers = ("आहे", "नाही", "झाले", "कृपया", "रस्ता", "पाणी", "कचरा")
            return "Marathi" if any(marker in text for marker in marathi_markers) else "Hindi"
        roman_markers = tuple(key for key in INDIC_NORMALIZATION if key.isascii())
        return "Hinglish / Roman Indic" if any(re.search(rf"\b{re.escape(marker)}\b", text.lower()) for marker in roman_markers) else "English"

    def detect_urgency(self, text: str) -> str:
        clean = text.lower()
        for term in EMERGENCY_TERMS:
            if term in clean:
                return "HIGH"
        if any(w in clean for w in ["urgent", "danger", "immediate", "terrible", "overflowing", "burst", "foul", "sick"]):
            return "HIGH"
        if any(w in clean for w in ["since week", "days", "problem", "broken", "leak", "blocked", "dark"]):
            return "MEDIUM"
        return "LOW"

    def extract_salient_terms(self, text: str, dept_code: str) -> list:
        clean = self.clean_text(text)
        found = []
        if dept_code in DEPARTMENTS_META:
            for kw in DEPARTMENTS_META[dept_code]["keywords"]:
                if kw in clean and kw not in found:
                    found.append(kw)
        return found[:5]

    def has_any_dept_keywords(self, text: str) -> bool:
        clean = self.clean_text(text)
        for dept, meta in DEPARTMENTS_META.items():
            for kw in meta["keywords"]:
                if kw in clean:
                    return True
        return False

    def predict(self, text: str):
        if not text or not text.strip():
            return {
                "predicted_department": "roads",
                "department_name": DEPARTMENTS_META["roads"]["name"],
                "confidence_score": 0.0,
                "routing_type": "MANUAL_REVIEW",
                "urgency": "LOW",
                "probabilities": {},
                "top_features": [],
                "reasoning": "Empty complaint text provided."
            }

        cleaned = self.clean_text(text)
        detected_language = self.detect_language(text)
        urgency = self.detect_urgency(text)
        has_keywords = self.has_any_dept_keywords(text)

        if not self.model:
            self._load_model()

        if self.model:
            probas = self.model.predict_proba([cleaned])[0]
            classes = list(self.model.classes_)
            
            prob_dict = {cls_name: round(float(prob), 4) for cls_name, prob in zip(classes, probas)}
            # Sort by probability descending
            sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
            
            top_dept, top_conf = sorted_probs[0]
            second_dept, second_conf = sorted_probs[1] if len(sorted_probs) > 1 else (None, 0.0)
            margin = round(top_conf - second_conf, 4)
            top_features = self.extract_salient_terms(text, top_dept)
            
            # Confidence & ambiguity fallback check
            # Falls back to MANUAL_REVIEW if:
            # 1. top_conf below the configured confidence threshold, OR
            # 2. margin between top 2 classes below the configured ambiguity margin, OR
            # 3. no specific civic department keywords found in text (vague complaint)
            if not has_keywords:
                routing_type = "MANUAL_REVIEW"
                reasoning = (
                    f"Complaint lacks specific departmental keywords. Model confidence is ungrounded. "
                    f"Diverted to Triage Desk for manual review."
                )
            elif top_conf < CONFIDENCE_THRESHOLD or margin < CLASS_MARGIN_THRESHOLD:
                routing_type = "MANUAL_REVIEW"
                second_name = DEPARTMENTS_META.get(second_dept, {}).get('name', second_dept) if second_dept else 'N/A'
                reasoning = (
                    f"Model confidence ({round(top_conf * 100, 1)}%) or margin ({round(margin * 100, 1)}%) indicates ambiguity. "
                    f"Flagged for human operator review at Triage Desk. Closest matches: "
                    f"{DEPARTMENTS_META.get(top_dept, {}).get('name', top_dept)} ({round(top_conf * 100, 1)}%) vs "
                    f"{second_name} ({round(second_conf * 100, 1)}%)."
                )
            else:
                routing_type = "AUTO"
                reasoning = (
                    f"Classified into {DEPARTMENTS_META.get(top_dept, {}).get('name', top_dept)} with "
                    f"{round(top_conf * 100, 1)}% confidence (lead margin: {round(margin * 100, 1)}%), exceeding the "
                    f"operational threshold of {int(CONFIDENCE_THRESHOLD * 100)}%."
                )

            return {
                "predicted_department": top_dept,
                "department_name": DEPARTMENTS_META.get(top_dept, {}).get("name", top_dept),
                "confidence_score": round(top_conf, 4),
                "routing_type": routing_type,
                "urgency": urgency,
                "probabilities": prob_dict,
                "top_features": top_features,
                "reasoning": reasoning,
                "detected_language": detected_language
            }
        else:
            # Fallback if model not available
            return {
                "predicted_department": "roads",
                "department_name": "Roads & Footpaths",
                "confidence_score": 0.50,
                "routing_type": "MANUAL_REVIEW",
                "urgency": urgency,
                "probabilities": {},
                "top_features": [],
                "reasoning": "Model pipeline not loaded; defaulting to manual review.",
                "detected_language": detected_language
            }

classifier = GrievanceClassifier()
