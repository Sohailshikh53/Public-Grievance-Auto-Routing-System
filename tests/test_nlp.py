from backend.services.nlp_service import classifier


def test_clear_english_pothole_routes_to_roads():
    result = classifier.predict("A deep pothole and broken asphalt are causing accidents on the main road")
    assert result["predicted_department"] == "roads"
    assert result["detected_language"] == "English"


def test_marathi_civic_vocabulary_is_normalized():
    result = classifier.predict("मुख्य रस्ता वर मोठा खड्डा आहे कृपया तातडीने दुरुस्ती करा")
    assert result["predicted_department"] == "roads"
    assert result["detected_language"] == "Marathi"


def test_vague_complaint_uses_human_fallback():
    result = classifier.predict("There is a bad problem near my house please inspect it")
    assert result["routing_type"] == "MANUAL_REVIEW"

