from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture()
def client():
    # Snapshot the in-memory state so each test starts clean and independent.
    original_activities = deepcopy(app_module.activities)

    # Reset global state before the test runs.
    app_module.activities.clear()
    app_module.activities.update(deepcopy(original_activities))

    with TestClient(app_module.app) as test_client:
        yield test_client

    # Reset global state again after the test to avoid test interference.
    app_module.activities.clear()
    app_module.activities.update(deepcopy(original_activities))


def test_root_redirects_to_static_index(client):
    # We disable redirect following to assert the actual redirect response itself.
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_expected_structure(client):
    # This is the read-only endpoint returning all activities.
    response = client.get("/activities")

    assert response.status_code == 200

    payload = response.json()

    assert "Chess Club" in payload
    assert payload["Chess Club"]["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
    assert payload["Chess Club"]["max_participants"] == 12
    assert payload["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_new_participant(client):
    # Happy path: a new email can register for an existing activity.
    email = "new.student@mergington.edu"

    response = client.post("/activities/Chess Club/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Chess Club"}
    assert email in app_module.activities["Chess Club"]["participants"]


def test_signup_returns_404_for_unknown_activity(client):
    # Unknown activities should return 404 to signal invalid resource.
    response = client.post(
        "/activities/Unknown Activity/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_returns_400_for_duplicate_participant(client):
    # Duplicate signup should be rejected by backend validation.
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }


def test_unregister_removes_existing_participant(client):
    # Happy path: an existing participant can be removed from an activity.
    email = "michael@mergington.edu"

    response = client.delete(
        "/activities/Chess Club/participants",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from Chess Club"}
    assert email not in app_module.activities["Chess Club"]["participants"]


def test_unregister_returns_404_for_unknown_activity(client):
    # Removing from an unknown activity should return 404.
    response = client.delete(
        "/activities/Unknown Activity/participants",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_returns_404_for_missing_participant(client):
    # Removing a non-member should return 404 because that participant is not in the activity.
    response = client.delete(
        "/activities/Chess Club/participants",
        params={"email": "not.registered@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Participant not found in this activity"}