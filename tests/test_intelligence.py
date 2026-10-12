import tempfile
from pathlib import Path

from backend.database import db
from backend.database.seed_data import seed_database
from backend.routes.analytics import get_issue_intelligence, get_summary_metrics


def test_maharashtra_city_scopes_and_issue_intelligence():
    original_path = db.DB_PATH
    try:
        with tempfile.TemporaryDirectory() as directory:
            db.DB_PATH = str(Path(directory) / "intelligence.db")
            db.init_db()
            seed_database()
            db.init_db()

            statewide = get_summary_metrics(city=None)
            pune = get_summary_metrics(city="Pune")
            intelligence = get_issue_intelligence(city=None, limit=8)

            assert statewide["total_complaints"] == 22
            assert len(statewide["city_breakdown"]) == 10
            assert 0 < pune["total_complaints"] < statewide["total_complaints"]
            assert intelligence["top_issues"]
            assert intelligence["top_complaints"]
            assert intelligence["emerging_terms"]
    finally:
        db.DB_PATH = original_path

