from app.ai import analyse_request, find_similar, priority_score

def test_fallback_analysis_extracts_theme():
    result = analyse_request("Email alerts", "I need notifications when a task is assigned.", "SMB")
    assert result["theme"] == "Notifications & alerts"
    assert result["underlying_need"]

def test_priority_score_is_deterministic_and_bounded():
    score = priority_score(10, "High", "Medium")
    assert score == priority_score(10, "High", "Medium")
    assert 0 <= score <= 100

def test_similarity_returns_matching_request():
    result = find_similar("Task alerts", "Notify me when work is assigned.", [
        {"id": 7, "title": "Assignment notifications", "description": "Send an alert when tasks are assigned."}])
    assert result and result[0]["request_id"] == 7
