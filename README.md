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

The overview now uses a bounded, authenticated `GET /api/dashboard` aggregate
instead of loading all catalogues and assignments on initial page load. Project
selection is searchable and paginated. See [dashboard design and tests](docs/dashboard.md)
and the [next-step roadmap](docs/next-steps.md).

Admins can now view **Hoạt động** in the sidebar or a project's activity tab:
actor, timestamp and before/after changes for projects, assignments and skill
requirements. Existing installations should run `python -m scripts.setup_activity_schema`
from `backend`. See [project activity and migration](docs/project-activity.md).
Every new feature/change must have documentation: [documentation index](docs/README.md).

## Login and access control

The frontend is implemented: dashboard, employee/skill/project management,
relationship editors, staffing, login, account security and user administration.
All business APIs now require login. Admins manage accounts and catalogues;
Managers write only to assigned projects; Viewers have read-only access.

Create your first Admin interactively (no default credentials), from `backend`:

```powershell
.\.venv\Scripts\python.exe -m scripts.create_admin
```

See [authentication setup, permissions and deployment safeguards](docs/authentication.md).
Account/session data lives in ignored `backend/data/auth.sqlite3`, separately
from CognoDB. Do not delete it as cache or commit it to Git.

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
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

Open Swagger UI at <http://127.0.0.1:8000/docs>.
Business requests require the session cookie; writes also require the allowed
Origin and X-CSRF-Token from `/api/auth/me`. The frontend handles these automatically.

## API endpoints

- `GET /health`
- `GET /api/dashboard` (authenticated workspace overview)
- `GET /api/activity` (Admin-only project history, cursor pagination)
- `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`
- `POST /api/auth/password`
- `GET|POST /api/auth/users` (Admin)
- `PATCH /api/auth/users/{user_id}` (Admin)
- `POST /api/auth/users/{user_id}/password` (Admin)
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
pytest -m "not integration" -q
pytest -m integration -q
ruff check app tests scripts
```
090 450 6600
