import sqlite3
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be blank")
        return title


class TaskUpdate(TaskCreate):
    completed: bool


def create_app(database_path: str | Path | None = None) -> FastAPI:
    database_path = (
        Path(database_path) if database_path is not None
        else Path(__file__).resolve().parent.parent / "tasks.db"
    )

    @contextmanager
    def connection():
        db = sqlite3.connect(database_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with connection() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                    completed INTEGER NOT NULL DEFAULT 0
                        CHECK(completed IN (0, 1))
                )
            """)
        yield

    app = FastAPI(title="Codzee Demo API", lifespan=lifespan)

    def task_json(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "completed": bool(row["completed"]),
        }

    @app.get("/")
    def home():
        return {"message": "Codzee Demo API is running"}

    @app.get("/tasks")
    def get_tasks():
        with connection() as db:
            rows = db.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        return [task_json(row) for row in rows]

    @app.post("/tasks", status_code=201)
    def create_task(task: TaskCreate):
        with connection() as db:
            cursor = db.execute(
                "INSERT INTO tasks (title) VALUES (?)", (task.title,)
            )
            row = db.execute(
                "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return task_json(row)

    @app.get("/tasks/{task_id}")
    def get_task(task_id: int):
        with connection() as db:
            row = db.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_json(row)

    @app.put("/tasks/{task_id}")
    def update_task(task_id: int, updated_task: TaskUpdate):
        with connection() as db:
            cursor = db.execute(
                "UPDATE tasks SET title = ?, completed = ? WHERE id = ?",
                (updated_task.title, int(updated_task.completed), task_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Task not found")
            row = db.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return task_json(row)

    @app.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int):
        with connection() as db:
            cursor = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Task not found")
        return Response(status_code=204)

    return app


app = create_app()
