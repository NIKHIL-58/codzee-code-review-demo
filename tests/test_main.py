
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


def test_update_task():
    created = client.post("/tasks", json={"title": "Original"}).json()
    task_id = created["id"]

    response = client.put(
        f"/tasks/{task_id}",
        json={"title": "  Updated  ", "completed": True},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": task_id,
        "title": "Updated",
        "completed": True,
    }
    assert client.get(f"/tasks/{task_id}").json() == response.json()

    response = client.put(
        f"/tasks/{task_id}",
        json={"title": "Reopened", "completed": False},
    )
    assert response.status_code == 200
    assert response.json()["completed"] is False


def test_update_task_rejects_blank_title():
    created = client.post("/tasks", json={"title": "Keep me"}).json()
    task_id = created["id"]

    for title in ["", "   "]:
        response = client.put(
            f"/tasks/{task_id}",
            json={"title": title, "completed": True},
        )
        assert response.status_code == 422

    assert client.get(f"/tasks/{task_id}").json() == created


def test_update_nonexistent_task():
    response = client.put(
        "/tasks/99999",
        json={"title": "Missing", "completed": True},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_delete_task():
    first = client.post("/tasks", json={"title": "Delete me"}).json()
    second = client.post("/tasks", json={"title": "Keep me"}).json()

    response = client.delete(f"/tasks/{first['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{first['id']}").status_code == 404
    assert client.get(f"/tasks/{second['id']}").json() == second
    assert first not in client.get("/tasks").json()


def test_delete_nonexistent_task():
    response = client.delete("/tasks/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}