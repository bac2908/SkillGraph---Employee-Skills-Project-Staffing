# SkillGraph - Employee Skills & Project Staffing

SkillGraph is a FastAPI and Neo4j application for analyzing a project's skill
coverage and recommending available employees for uncovered skills.

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
- `GET /api/projects/{project_id}/skill-gap`
- `GET /api/projects/{project_id}/recommendations`

Example project: `PROJ001`.

List endpoints accept `q`, `limit`, and `offset`. Employee and project lists
also accept `status`; the skill list accepts `category`. Deletes are safe by
default: a node that still has graph relationships returns `409 Conflict`.

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
