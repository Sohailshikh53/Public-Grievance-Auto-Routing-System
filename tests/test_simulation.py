from backend.services.simulation_service import list_presets, run_simulation


def test_all_presets_run():
    for preset in list_presets():
        result = run_simulation({"preset": preset["key"], "seed": 42, "confidence_threshold": 0.65})
        assert result["summary"]["total_complaints"] > 0
        assert len(result["department_metrics"]) == 7
        assert len(result["ward_activity"]) == 15


def test_simulation_is_deterministic():
    config = {"preset": "monsoon", "seed": 2026, "confidence_threshold": 0.65}
    assert run_simulation(config) == run_simulation(config)


def test_higher_threshold_increases_manual_review():
    base = {"preset": "normal", "seed": 99}
    low = run_simulation({**base, "confidence_threshold": 0.45})
    high = run_simulation({**base, "confidence_threshold": 0.85})
    assert high["summary"]["manual_review"] >= low["summary"]["manual_review"]


def test_staff_shortage_creates_more_pressure():
    normal = run_simulation({"preset": "normal", "seed": 17, "duration_hours": 36, "arrival_rate": 14})
    shortage = run_simulation({"preset": "staff_shortage", "seed": 17, "duration_hours": 36, "arrival_rate": 14})
    assert shortage["summary"]["p95_resolution_hours"] > normal["summary"]["p95_resolution_hours"]


def test_city_scoped_simulation_returns_top_issues():
    result = run_simulation({"preset": "monsoon", "seed": 41, "city_scope": "Nagpur"})
    assert result["top_issues"]
    assert result["city_activity"] == [result["city_activity"][0]]
    assert result["city_activity"][0]["city"] == "Nagpur"
