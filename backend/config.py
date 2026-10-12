"""Shared runtime configuration for PG-ARS."""

import os
from datetime import datetime, timezone


CONFIDENCE_THRESHOLD = float(os.getenv("PGARS_CONFIDENCE_THRESHOLD", "0.65"))
CLASS_MARGIN_THRESHOLD = float(os.getenv("PGARS_CLASS_MARGIN_THRESHOLD", "0.15"))
TRACKING_YEAR = os.getenv("PGARS_TRACKING_YEAR", str(datetime.now(timezone.utc).year))

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "PGARS_ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if origin.strip()
]

MAHARASHTRA_CITIES = [
    "Mumbai",
    "Pune",
    "Nagpur",
    "Nashik",
    "Thane",
    "Chhatrapati Sambhajinagar",
    "Solapur",
    "Kolhapur",
    "Amravati",
    "Nanded",
]
