
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Codzee Demo API is running"
    }


def test_get_tasks_initially_empty():
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_create_task():
    response = client.post(
        "/tasks",
        json={"title": "Learn FastAPI"}
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Learn FastAPI"
    assert response.json()["completed"] is False
    assert "id" in response.json()


def test_create_task_with_empty_title():
    response = client.post(
        "/tasks",
        json={"title": ""}
    )

    assert response.status_code == 422


def test_get_nonexistent_task():
    response = client.get("/tasks/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}

def test_create_task_with_whitespace_title():
    for title in ["   ", "\t", "\n"]:
        response = client.post("/tasks", json={"title": title})
        assert response.status_code == 422


def test_create_task_trims_title():
    response = client.post(
        "/tasks",
        json={"title": "  Learn FastAPI  "}
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Learn FastAPI"