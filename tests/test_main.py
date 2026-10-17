
from fastapi.testclient import TestClient

import pytest

from app.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as test_client:
        yield test_client


def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Codzee Demo API is running"
    }


def test_get_tasks_initially_empty(client):
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_create_task(client):
    response = client.post(
        "/tasks",
        json={"title": "Learn FastAPI"}
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Learn FastAPI"
    assert response.json()["completed"] is False
    assert "id" in response.json()


def test_create_task_with_empty_title(client):
    response = client.post(
        "/tasks",
        json={"title": ""}
    )

    assert response.status_code == 422


def test_get_nonexistent_task(client):
    response = client.get("/tasks/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}

def test_create_task_with_whitespace_title(client):
    for title in ["   ", "\t", "\n"]:
        response = client.post("/tasks", json={"title": title})
        assert response.status_code == 422


def test_create_task_trims_title(client):
    response = client.post(
        "/tasks",
        json={"title": "  Learn FastAPI  "}
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Learn FastAPI"


def test_update_task(client):
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


def test_update_task_rejects_blank_title(client):
    created = client.post("/tasks", json={"title": "Keep me"}).json()
    task_id = created["id"]

    for title in ["", "   "]:
        response = client.put(
            f"/tasks/{task_id}",
            json={"title": title, "completed": True},
        )
        assert response.status_code == 422

    assert client.get(f"/tasks/{task_id}").json() == created


def test_update_nonexistent_task(client):
    response = client.put(
        "/tasks/99999",
        json={"title": "Missing", "completed": True},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_delete_task(client):
    first = client.post("/tasks", json={"title": "Delete me"}).json()
    second = client.post("/tasks", json={"title": "Keep me"}).json()

    response = client.delete(f"/tasks/{first['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{first['id']}").status_code == 404
    assert client.get(f"/tasks/{second['id']}").json() == second
    assert first not in client.get("/tasks").json()


def test_delete_nonexistent_task(client):
    response = client.delete("/tasks/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}

def test_tasks_survive_process_restart(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    database_path = tmp_path / "persistent.db"
    script = """
import json
import sys
from fastapi.testclient import TestClient
from app.main import create_app
with TestClient(create_app(sys.argv[1])) as client:
    response = client.post('/tasks', json={'title': 'Survive restart'})
    assert response.status_code == 201
    print(json.dumps(response.json()))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(database_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, check=True,
    )
    created = json.loads(result.stdout)
    task_url = f"/tasks/{created['id']}"

    with TestClient(create_app(database_path)) as restarted:
        assert restarted.get(task_url).json() == created
        updated = restarted.put(
            task_url, json={"title": "Saved update", "completed": True}
        )
        assert updated.status_code == 200

    with TestClient(create_app(database_path)) as restarted:
        assert restarted.get(task_url).json() == updated.json()
        assert restarted.delete(task_url).status_code == 204

    with TestClient(create_app(database_path)) as restarted:
        assert restarted.get(task_url).status_code == 404
        assert restarted.get("/tasks").json() == []


def test_title_with_sql_characters_is_stored_as_text(client):
    title = "Robert'); DROP TABLE tasks;--"
    response = client.post("/tasks", json={"title": title})
    assert response.status_code == 201
    assert client.get(f"/tasks/{response.json()['id']}").json()["title"] == title
    assert client.post("/tasks", json={"title": "Still working"}).status_code == 201


def test_deleted_task_id_is_not_reused(client):
    first = client.post("/tasks", json={"title": "First"}).json()
    assert client.delete(f"/tasks/{first['id']}").status_code == 204
    second = client.post("/tasks", json={"title": "Second"}).json()
    assert second["id"] > first["id"]
