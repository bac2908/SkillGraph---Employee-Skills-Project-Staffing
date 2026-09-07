# SkillGraph - Employee Skills & Project Staffing

SkillGraph is a FastAPI and Neo4j application for analyzing a project's skill
coverage and recommending available employees for uncovered skills.

## Frontend dashboard

The Vietnamese React/TypeScript dashboard supports employee, skill, and project
management, graph relationships, skill-gap analysis, and staffing recommendations.
With the backend running on port 8000, open a second terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open <http://127.0.0.1:5173>. See [frontend setup and testing](docs/frontend.md)
for configuration, architecture, and browser tests.

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set `COGNODB_URI`, `COGNODB_USER`, and `COGNODB_PASSWORD` in `backend/.env`.
The `.env` file is ignored by Git and must not be committed.

Initialize the graph and start the API:

```powershell
python -m scripts.setup_schema
python -m scripts.seed
uvicorn app.main:app --reload
```

Open Swagger UI at <http://127.0.0.1:8000/docs>.

## API endpoints

- `GET /health`
- `GET|POST /api/employees`
- `GET|PATCH|DELETE /api/employees/{employee_id}`
- `GET|POST /api/skills`
- `GET|PATCH|DELETE /api/skills/{skill_id}`
- `GET|POST /api/projects`
- `GET|PATCH|DELETE /api/projects/{project_id}`
- `GET /api/employees/{employee_id}/skills`
- `PUT|DELETE /api/employees/{employee_id}/skills/{skill_id}`
- `GET /api/projects/{project_id}/assignments`
- `PUT|DELETE /api/projects/{project_id}/assignments/{employee_id}`
- `GET /api/projects/{project_id}/requirements`
- `PUT|DELETE /api/projects/{project_id}/requirements/{skill_id}`
- `GET /api/projects/{project_id}/skill-gap`
- `GET /api/projects/{project_id}/recommendations`

Example project: `PROJ001`.

List endpoints accept `q`, `limit`, and `offset`. Employee and project lists
also accept `status`; the skill list accepts `category`. Deletes are safe by
default: a node that still has graph relationships returns `409 Conflict`.

Relationship item endpoints use idempotent `PUT`: the first request creates the
relationship and returns `201 Created`; later requests replace its properties
and return `200 OK`. Employee allocation is an integer percentage from 1 to 100.
All `WORKS_ON` relationships for one employee may total at most 100%; this rule
is checked under a per-employee database lock to remain correct under concurrent
requests.

## Validation

From the `backend` directory:

```powershell
python test_connection.py
python test_skill_gap.py
python test_candidate_recommendation.py
```

Install the development dependencies and run the full CRUD integration test:

```powershell
pip install -r requirements-dev.txt
pytest -m integration -q
ruff check app tests scripts
```
090 450 6600
