from conftest import signup


def _fb(**over):
    return {"manual_hours": 10, "campusnest_minutes": 6, "ease": 5, "would_recommend": True, **over}


def test_only_students_can_submit_and_login_is_required(client, owner, student):
    assert client.post("/api/feedback", json=_fb()).status_code == 401
    assert client.post("/api/feedback", json=_fb(), headers=owner).status_code == 403
    assert client.post("/api/feedback", json=_fb(), headers=student).status_code == 201


def test_one_response_per_student_and_resubmitting_updates_it(client, student):
    client.post("/api/feedback", json=_fb(ease=2), headers=student)
    client.post("/api/feedback", json=_fb(ease=4, comment="  Much better  "), headers=student)
    mine = client.get("/api/feedback/mine", headers=student).json()
    assert mine["ease"] == 4 and mine["comment"] == "Much better"
    assert client.get("/api/feedback/summary", headers=student).json()["responses"] == 1


def test_validation(client, student):
    assert client.post("/api/feedback", json=_fb(ease=6), headers=student).status_code == 422
    assert client.post("/api/feedback", json=_fb(campusnest_minutes=-1), headers=student).status_code == 422
    assert client.post("/api/feedback", json={"ease": 3}, headers=student).status_code == 422


def test_my_feedback_is_null_before_submitting(client, student):
    assert client.get("/api/feedback/mine", headers=student).json() is None


def test_summary_math_and_time_saved(client, owner):
    a = signup(client, "student", "a@example.com")
    b = signup(client, "student", "b@example.com")
    c = signup(client, "student", "c@example.com")
    client.post("/api/feedback", json=_fb(manual_hours=10, campusnest_minutes=6, ease=5), headers=a)
    client.post("/api/feedback", json=_fb(manual_hours=20, campusnest_minutes=12, ease=3, would_recommend=False), headers=b)
    client.post("/api/feedback", json=_fb(manual_hours=None, campusnest_minutes=30, ease=4), headers=c)  # no old-way time
    s = client.get("/api/feedback/summary", headers=owner).json()
    assert s["responses"] == 3
    assert s["avg_ease"] == 4.0
    assert s["avg_manual_hours"] == 15.0                       # only the two who answered
    assert s["time_saved_pct"] == 99.0                         # (1 - 0.15h / 15h) * 100, paired answers only
    assert s["would_recommend_pct"] == 66.7


def test_summary_with_no_responses(client, student):
    s = client.get("/api/feedback/summary", headers=student).json()
    assert s["responses"] == 0 and s["time_saved_pct"] is None and s["avg_ease"] is None
