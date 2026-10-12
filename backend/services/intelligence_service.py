"""ML-assisted issue intelligence over grievances received by the platform."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.database.db import get_db
from backend.services.nlp_service import DEPARTMENTS_META


def _top_terms(texts: list[str], limit: int = 10) -> list[dict[str, Any]]:
    if not texts:
        return []
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=250,
            min_df=1,
            stop_words="english",
        )
        matrix = vectorizer.fit_transform(texts)
        weights = np.asarray(matrix.mean(axis=0)).ravel()
        terms = vectorizer.get_feature_names_out()
        ranked = sorted(zip(terms, weights), key=lambda item: item[1], reverse=True)
        return [{"term": term, "score": round(float(score), 4)} for term, score in ranked[:limit]]
    except ValueError:
        return []


def build_issue_intelligence(city: str | None = None, limit: int = 8) -> dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    query = """
    SELECT id, tracking_token, city, ward_number, locality, complaint_text, urgency,
           predicted_department, assigned_department, confidence_score, routing_type,
           status, is_escalated, escalation_level, sla_due_at, created_at
    FROM complaints WHERE 1=1
    """
    params: list[Any] = []
    if city:
        query += " AND city = ?"
        params.append(city)
    query += " ORDER BY created_at DESC;"
    cursor.execute(query, params)
    complaints = [dict(row) for row in cursor.fetchall()]
    conn.close()

    now = datetime.now(timezone.utc)
    by_department: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for complaint in complaints:
        code = complaint["predicted_department"] or complaint["assigned_department"]
        by_department[code].append(complaint)

    top_issues = []
    for department, rows in by_department.items():
        meta = DEPARTMENTS_META.get(department, {"name": department.replace("_", " ").title()})
        terms = _top_terms([row["complaint_text"] for row in rows], 4)
        top_issues.append({
            "department": department,
            "name": meta["name"],
            "count": len(rows),
            "share": round(len(rows) / len(complaints) * 100, 1) if complaints else 0.0,
            "high_urgency": sum(row["urgency"] == "HIGH" for row in rows),
            "active_escalations": sum(bool(row["is_escalated"]) and row["status"] not in ("RESOLVED", "REJECTED") for row in rows),
            "average_confidence": round(sum(row["confidence_score"] for row in rows) / len(rows) * 100, 1),
            "representative_terms": [term["term"] for term in terms],
            "example_token": rows[0]["tracking_token"],
        })
    top_issues.sort(key=lambda item: (item["count"], item["active_escalations"], item["high_urgency"]), reverse=True)

    priorities = []
    for complaint in complaints:
        try:
            created = datetime.fromisoformat(complaint["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now - created).total_seconds() / 3600)
        except (TypeError, ValueError):
            age_hours = 0.0
        score = (
            (35 if complaint["urgency"] == "HIGH" else 16 if complaint["urgency"] == "MEDIUM" else 5)
            + int(complaint["escalation_level"] or 0) * 25
            + min(20, age_hours / 6)
            + (1 - float(complaint["confidence_score"])) * 12
            + (8 if complaint["routing_type"] == "MANUAL_REVIEW" else 0)
        )
        priorities.append({
            "tracking_token": complaint["tracking_token"],
            "city": complaint["city"],
            "ward": complaint["ward_number"],
            "locality": complaint["locality"],
            "department": complaint["predicted_department"],
            "urgency": complaint["urgency"],
            "status": complaint["status"],
            "priority_score": round(score, 1),
            "summary": complaint["complaint_text"][:180],
        })
    priorities.sort(key=lambda item: item["priority_score"], reverse=True)

    city_counts = Counter(row["city"] for row in complaints)
    city_escalations = Counter(row["city"] for row in complaints if row["is_escalated"] and row["status"] not in ("RESOLVED", "REJECTED"))
    city_hotspots = [
        {"city": name, "complaints": count, "active_escalations": city_escalations[name]}
        for name, count in city_counts.most_common()
    ]

    return {
        "scope": city or "Maharashtra",
        "total_analyzed": len(complaints),
        "method": "TF-IDF issue-term extraction plus operational priority scoring",
        "top_issues": top_issues[:limit],
        "top_complaints": priorities[:limit],
        "emerging_terms": _top_terms([row["complaint_text"] for row in complaints], limit),
        "city_hotspots": city_hotspots,
    }

