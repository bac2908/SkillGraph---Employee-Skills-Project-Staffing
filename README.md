# SkillGraph - Employee Skills & Project Staffing

SkillGraph is a FastAPI/React application backed by CognoDB (Bolt/Neo4j driver)
for skill coverage analysis and rule-based staffing recommendations. A suggested
employee is not guaranteed to have remaining allocation.

New to the project? Start with the Vietnamese [project overview](docs/tong-quan-du-an.md)
for its purpose, business value, user roles, workflow, architecture, current scope
and proposed completion criteria.

**Receiving this project?** Follow the Vietnamese [handoff guide](docs/handoff.md)
for a clean installation, schema/account bootstrap, demo, verification, recovery
and known limitations. This is a local handoff candidate, not a production release.

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
If the only Admin cannot sign in because of a forgotten password, authorized
operators can use the [local Admin recovery CLI](docs/admin-recovery.md). It
requires interactive confirmation, resets only an existing active Admin, revokes
old sessions and forces a password change. Do not run it if recovery is not needed.
Account/session data lives in ignored `backend/data/auth.sqlite3`, separately
from CognoDB. Do not delete it as cache or commit it to Git.

Run `npm.cmd run test:rbac` from `frontend` for isolated three-role acceptance
through the UI and direct API calls. It uses real FastAPI/auth with temporary
SQLite and synthetic business services, not your graph or accounts. See the
Vietnamese [RBAC acceptance report and limitations](docs/rbac-acceptance.md).

For opt-in write acceptance against a dedicated empty graph, use the guarded
backend runner documented in [real graph E2E acceptance](docs/graph-e2e-acceptance.md).
This separate suite is prepared but has not yet been run on the test instance;
never point it at the working graph or reuse real account credentials.

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt -c constraints-windows-py312.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set `COGNODB_URI`, `COGNODB_USER`, and `COGNODB_PASSWORD` in `backend/.env`.
The `.env` file is ignored by Git and must not be committed.

For a new, dedicated graph only, initialize schema (includes activity indexes).
Review the [migration procedure](docs/handoff.md) before changing an existing DB:

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_schema
.\.venv\Scripts\python.exe -m scripts.create_admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

Open Swagger UI at <http://127.0.0.1:8000/docs>.
Seeding is optional and writes fixed IDs/properties. Never run `scripts.seed`
on existing working data as an installation or recovery step. Use the
[synthetic demo scenario](docs/demo-scenario.md) on a dedicated environment.
Business requests require the session cookie; writes also require the allowed
Origin and X-CSRF-Token from `/api/auth/me`. The frontend handles these automatically.

## API endpoints

- `GET /health`
- `GET /health/ready` (bounded dependency readiness, 200 or 503)
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

## Readiness and recovery

`/health` remains process liveness; `/health/ready` checks graph/schema and the
existing auth store without bootstrapping a missing database. See
[readiness checks](docs/readiness.md).

Local recovery commands now support a versioned graph + SQLite backup, checksum
verification and isolated restore. Pause all writers before backup; never use
the live graph as a restore target. No automated retention or production cutover
is enabled. See [backup/restore procedure and verification status](docs/backup-restore.md).

## Validation

From the `backend` directory:

```powershell
python test_connection.py
python test_skill_gap.py
python test_candidate_recommendation.py
```

Install development dependencies and run safe isolated tests:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-dev.txt -c constraints-windows-py312.txt
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -m ruff check app tests scripts
```
The three diagnostic scripts above connect to the configured graph. Integration
tests can write graph data; they are not part of the default handoff validation.
Use a dedicated test instance and the guarded [graph E2E procedure](docs/graph-e2e-acceptance.md).
