"""Deterministic discrete-event simulator for municipal grievance operations."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import median
from typing import Any

from backend.config import MAHARASHTRA_CITIES


DEPARTMENTS = {
    "roads": {"name": "Roads & Footpaths", "sla": 72, "staff": 9, "service": 8.0},
    "water_supply": {"name": "Water Supply", "sla": 48, "staff": 8, "service": 6.5},
    "electricity": {"name": "Electricity", "sla": 24, "staff": 7, "service": 5.0},
    "sanitation": {"name": "Sanitation", "sla": 24, "staff": 10, "service": 4.0},
    "drainage": {"name": "Drainage & Sewerage", "sla": 48, "staff": 7, "service": 7.0},
    "public_health": {"name": "Public Health", "sla": 24, "staff": 6, "service": 5.5},
    "encroachment": {"name": "Encroachment", "sla": 96, "staff": 5, "service": 12.0},
}

BASE_WEIGHTS = {
    "roads": 0.20,
    "water_supply": 0.16,
    "electricity": 0.13,
    "sanitation": 0.18,
    "drainage": 0.13,
    "public_health": 0.10,
    "encroachment": 0.10,
}

PRESETS = {
    "normal": {
        "name": "Normal weekday",
        "description": "Typical civic demand with balanced department load.",
        "arrival_rate": 10,
        "duration_hours": 24,
        "ambiguity_rate": 0.16,
        "high_urgency_rate": 0.18,
        "weight_overrides": {},
        "staff_factor": 1.0,
    },
    "monsoon": {
        "name": "Severe monsoon",
        "description": "Drainage, road and water complaints surge after extreme rainfall.",
        "arrival_rate": 28,
        "duration_hours": 36,
        "ambiguity_rate": 0.25,
        "high_urgency_rate": 0.36,
        "weight_overrides": {"drainage": 0.34, "roads": 0.25, "water_supply": 0.18},
        "staff_factor": 1.0,
    },
    "festival": {
        "name": "Festival waste surge",
        "description": "Sanitation and encroachment queues spike across market wards.",
        "arrival_rate": 22,
        "duration_hours": 30,
        "ambiguity_rate": 0.18,
        "high_urgency_rate": 0.22,
        "weight_overrides": {"sanitation": 0.42, "encroachment": 0.20},
        "staff_factor": 0.9,
    },
    "water_crisis": {
        "name": "Water supply emergency",
        "description": "A trunk pipeline failure creates a city-wide water complaint burst.",
        "arrival_rate": 30,
        "duration_hours": 18,
        "ambiguity_rate": 0.20,
        "high_urgency_rate": 0.45,
        "weight_overrides": {"water_supply": 0.58, "drainage": 0.15},
        "staff_factor": 1.0,
    },
    "electrical_storm": {
        "name": "Electrical storm",
        "description": "Live-wire and streetlight complaints require rapid dispatch.",
        "arrival_rate": 24,
        "duration_hours": 20,
        "ambiguity_rate": 0.12,
        "high_urgency_rate": 0.52,
        "weight_overrides": {"electricity": 0.56, "roads": 0.14},
        "staff_factor": 1.0,
    },
    "staff_shortage": {
        "name": "40% staff shortage",
        "description": "Normal demand with constrained field capacity across departments.",
        "arrival_rate": 14,
        "duration_hours": 36,
        "ambiguity_rate": 0.20,
        "high_urgency_rate": 0.20,
        "weight_overrides": {},
        "staff_factor": 0.6,
    },
}


@dataclass
class SimComplaint:
    arrival: float
    department: str
    confidence: float
    manual_review: bool
    urgent: bool
    ward: int
    city: str


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _weights(preset: dict[str, Any]) -> tuple[list[str], list[float]]:
    weights = dict(BASE_WEIGHTS)
    weights.update(preset.get("weight_overrides", {}))
    total = sum(weights.values())
    return list(weights), [weights[key] / total for key in weights]


def run_simulation(config: dict[str, Any]) -> dict[str, Any]:
    preset_key = config.get("preset", "normal")
    preset = PRESETS.get(preset_key, PRESETS["normal"])
    seed = int(config.get("seed", 42))
    rng = random.Random(seed)

    duration = float(config.get("duration_hours") or preset["duration_hours"])
    arrival_rate = float(config.get("arrival_rate") or preset["arrival_rate"])
    threshold = float(config.get("confidence_threshold", 0.65))
    ambiguity_rate = float(config.get("ambiguity_rate") if config.get("ambiguity_rate") is not None else preset["ambiguity_rate"])
    urgency_rate = float(config.get("high_urgency_rate") if config.get("high_urgency_rate") is not None else preset["high_urgency_rate"])
    triage_staff = max(1, int(config.get("triage_staff", 4)))
    staffing = config.get("staffing") or {}
    city_scope = config.get("city_scope")
    simulation_cities = [city_scope] if city_scope in MAHARASHTRA_CITIES else MAHARASHTRA_CITIES

    department_codes, department_weights = _weights(preset)
    arrivals: list[SimComplaint] = []
    clock = 0.0
    while clock < duration:
        clock += rng.expovariate(arrival_rate)
        if clock >= duration:
            break
        department = rng.choices(department_codes, weights=department_weights, k=1)[0]
        ambiguous = rng.random() < ambiguity_rate
        confidence = rng.betavariate(3, 4) if ambiguous else rng.betavariate(10, 2)
        arrivals.append(SimComplaint(
            arrival=clock,
            department=department,
            confidence=confidence,
            manual_review=ambiguous or confidence < threshold,
            urgent=rng.random() < urgency_rate,
            ward=rng.randint(1, 15),
            city=rng.choice(simulation_cities),
        ))

    triage_available = [0.0] * triage_staff
    dept_available: dict[str, list[float]] = {}
    for code, meta in DEPARTMENTS.items():
        requested = staffing.get(code)
        count = int(requested) if requested is not None else round(meta["staff"] * preset["staff_factor"])
        dept_available[code] = [0.0] * max(1, count)

    results: list[dict[str, Any]] = []
    dept_stats: dict[str, dict[str, Any]] = {
        code: {"received": 0, "resolved": 0, "breached": 0, "manual": 0, "wait": [], "resolution": [], "busy": 0.0}
        for code in DEPARTMENTS
    }
    timeline = [{"hour": hour, "arrivals": 0, "resolved": 0, "breached": 0} for hour in range(math.ceil(duration) + 1)]

    for idx, complaint in enumerate(arrivals, start=1):
        dispatch_at = complaint.arrival
        triage_delay = 0.0
        if complaint.manual_review:
            slot = min(range(len(triage_available)), key=triage_available.__getitem__)
            triage_start = max(dispatch_at, triage_available[slot])
            triage_duration = rng.uniform(0.15, 0.55)
            dispatch_at = triage_start + triage_duration
            triage_available[slot] = dispatch_at
            triage_delay = dispatch_at - complaint.arrival

        meta = DEPARTMENTS[complaint.department]
        servers = dept_available[complaint.department]
        officer_slot = min(range(len(servers)), key=servers.__getitem__)
        work_start = max(dispatch_at, servers[officer_slot])
        base_service = meta["service"] * (0.68 if complaint.urgent else 1.0)
        service_time = max(0.35, rng.lognormvariate(math.log(base_service), 0.38))
        resolved_at = work_start + service_time
        servers[officer_slot] = resolved_at
        total_time = resolved_at - complaint.arrival
        waiting = work_start - complaint.arrival
        breached = total_time > meta["sla"]
        overdue = max(0.0, total_time - meta["sla"])
        escalation = 2 if overdue >= 24 else 1 if breached else 0

        stat = dept_stats[complaint.department]
        stat["received"] += 1
        stat["resolved"] += 1
        stat["breached"] += int(breached)
        stat["manual"] += int(complaint.manual_review)
        stat["wait"].append(waiting)
        stat["resolution"].append(total_time)
        stat["busy"] += service_time

        arrival_bucket = min(math.floor(complaint.arrival), len(timeline) - 1)
        timeline[arrival_bucket]["arrivals"] += 1
        if resolved_at <= duration:
            timeline[min(math.floor(resolved_at), len(timeline) - 1)]["resolved"] += 1
        if breached:
            timeline[min(math.floor(complaint.arrival + meta["sla"]), len(timeline) - 1)]["breached"] += 1

        results.append({
            "id": f"SIM-{seed}-{idx:05d}",
            "arrival_hour": round(complaint.arrival, 2),
            "department": complaint.department,
            "ward": f"Ward {complaint.ward}",
            "city": complaint.city,
            "confidence": round(complaint.confidence, 3),
            "manual_review": complaint.manual_review,
            "urgent": complaint.urgent,
            "triage_delay_hours": round(triage_delay, 2),
            "wait_hours": round(waiting, 2),
            "resolution_hours": round(total_time, 2),
            "breached": breached,
            "escalation_level": escalation,
        })

    resolution_times = [row["resolution_hours"] for row in results]
    manual_count = sum(row["manual_review"] for row in results)
    breached_count = sum(row["breached"] for row in results)
    level1 = sum(row["escalation_level"] == 1 for row in results)
    level2 = sum(row["escalation_level"] == 2 for row in results)
    total = len(results)

    department_metrics = []
    for code, stat in dept_stats.items():
        staff_count = len(dept_available[code])
        capacity_window = max(duration, max(dept_available[code], default=duration)) * staff_count
        department_metrics.append({
            "code": code,
            "name": DEPARTMENTS[code]["name"],
            "staff": staff_count,
            "received": stat["received"],
            "manual_review": stat["manual"],
            "sla_breaches": stat["breached"],
            "sla_compliance": round((1 - stat["breached"] / stat["received"]) * 100, 1) if stat["received"] else 100.0,
            "avg_wait_hours": round(sum(stat["wait"]) / len(stat["wait"]), 2) if stat["wait"] else 0.0,
            "p95_resolution_hours": round(_percentile(stat["resolution"], 0.95), 2),
            "utilization": round(min(1.0, stat["busy"] / capacity_window) * 100, 1) if capacity_window else 0.0,
        })

    department_metrics.sort(key=lambda item: (item["sla_breaches"], item["avg_wait_hours"]), reverse=True)
    bottleneck = department_metrics[0] if department_metrics and department_metrics[0]["received"] else None
    events = []
    for row in sorted(results, key=lambda item: (not item["breached"], item["arrival_hour"]))[:80]:
        if row["breached"]:
            message = f"{row['id']} breached SLA in {DEPARTMENTS[row['department']]['name']}"
            event_type = "breach"
        elif row["manual_review"]:
            message = f"{row['id']} diverted to human triage"
            event_type = "triage"
        else:
            message = f"{row['id']} auto-routed to {DEPARTMENTS[row['department']]['name']}"
            event_type = "route"
        events.append({"at": row["arrival_hour"], "type": event_type, "message": message, "ward": row["ward"], "city": row["city"]})

    top_issues = [
        {
            "department": item["code"],
            "name": item["name"],
            "count": item["received"],
            "share": round(item["received"] / total * 100, 1) if total else 0.0,
            "sla_breaches": item["sla_breaches"],
            "severity": "CRITICAL" if item["sla_breaches"] > max(5, item["received"] * 0.35) else "ELEVATED" if item["sla_breaches"] else "STABLE",
        }
        for item in sorted(department_metrics, key=lambda row: (row["received"], row["sla_breaches"]), reverse=True)[:5]
    ]

    return {
        "scenario": {"key": preset_key, "name": preset["name"], "description": preset["description"]},
        "configuration": {
            "seed": seed,
            "duration_hours": duration,
            "arrival_rate": arrival_rate,
            "confidence_threshold": threshold,
            "ambiguity_rate": ambiguity_rate,
            "high_urgency_rate": urgency_rate,
            "triage_staff": triage_staff,
        },
        "summary": {
            "total_complaints": total,
            "auto_routed": total - manual_count,
            "auto_routing_rate": round((total - manual_count) / total * 100, 1) if total else 0.0,
            "manual_review": manual_count,
            "manual_review_rate": round(manual_count / total * 100, 1) if total else 0.0,
            "sla_compliance": round((total - breached_count) / total * 100, 1) if total else 100.0,
            "sla_breaches": breached_count,
            "level1_escalations": level1,
            "level2_escalations": level2,
            "median_resolution_hours": round(median(resolution_times), 2) if resolution_times else 0.0,
            "p95_resolution_hours": round(_percentile(resolution_times, 0.95), 2),
            "bottleneck_department": bottleneck["name"] if bottleneck else "None",
        },
        "department_metrics": department_metrics,
        "timeline": timeline,
        "events": events,
        "top_issues": top_issues,
        "city_activity": [
            {
                "city": city,
                "count": sum(item["city"] == city for item in results),
                "breaches": sum(item["city"] == city and item["breached"] for item in results),
                "high_urgency": sum(item["city"] == city and item["urgent"] for item in results),
            }
            for city in simulation_cities
        ],
        "ward_activity": [
            {"ward": f"Ward {ward}", "count": sum(item["ward"] == f"Ward {ward}" for item in results), "breaches": sum(item["ward"] == f"Ward {ward}" and item["breached"] for item in results)}
            for ward in range(1, 16)
        ],
    }


def list_presets() -> list[dict[str, Any]]:
    return [{"key": key, **value} for key, value in PRESETS.items()]
