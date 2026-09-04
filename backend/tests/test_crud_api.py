from time import time_ns

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_crud_lifecycle_and_api_guards() -> None:
    suffix = str(time_ns())
    employee_id = f"EMP{suffix}"
    skill_id = f"SK{suffix}"
    project_id = f"PROJ{suffix}"

    created_paths: list[str] = []
    with TestClient(app) as client:
        try:
            assert client.get("/health").json() == {"status": "ok"}

            employee_payload = {
                "employee_id": employee_id,
                "name": "API Integration Employee",
                "email": f"{suffix}@example.com",
                "title": "Backend Developer",
                "seniority": "Senior",
                "status": "AVAILABLE",
                "location": "Ho Chi Minh City",
            }
            response = client.post("/api/employees", json=employee_payload)
            assert response.status_code == 201, response.text
            created_paths.append(f"/api/employees/{employee_id}")

            duplicate = client.post("/api/employees", json=employee_payload)
            assert duplicate.status_code == 409

            response = client.patch(
                f"/api/employees/{employee_id}",
                json={"status": "ASSIGNED"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "ASSIGNED"

            response = client.get(
                "/api/employees",
                params={"q": employee_id, "status": "ASSIGNED"},
            )
            assert response.status_code == 200
            assert response.json()["total"] == 1

            assert client.patch(
                f"/api/employees/{employee_id}",
                json={},
            ).status_code == 422
            assert client.post(
                "/api/employees",
                json={**employee_payload, "email": "not-an-email"},
            ).status_code == 422

            skill_payload = {
                "skill_id": skill_id,
                "name": f"API Integration Skill {suffix}",
                "category": "Backend",
            }
            response = client.post("/api/skills", json=skill_payload)
            assert response.status_code == 201, response.text
            created_paths.append(f"/api/skills/{skill_id}")

            response = client.patch(
                f"/api/skills/{skill_id}",
                json={"category": "Platform Engineering"},
            )
            assert response.status_code == 200
            assert response.json()["category"] == "Platform Engineering"

            response = client.get(
                "/api/skills",
                params={"q": skill_id, "category": "Platform Engineering"},
            )
            assert response.status_code == 200
            assert response.json()["total"] == 1

            project_payload = {
                "project_id": project_id,
                "name": f"API Integration Project {suffix}",
                "description": "Temporary CRUD integration test project.",
                "status": "PLANNING",
            }
            response = client.post("/api/projects", json=project_payload)
            assert response.status_code == 201, response.text
            created_paths.append(f"/api/projects/{project_id}")

            response = client.patch(
                f"/api/projects/{project_id}",
                json={"status": "ACTIVE"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "ACTIVE"

            response = client.get(
                "/api/projects",
                params={"q": project_id, "status": "ACTIVE"},
            )
            assert response.status_code == 200
            assert response.json()["total"] == 1

            assert client.delete("/api/projects/PROJ001").status_code == 409
            assert client.get(
                "/api/employees/EMP999999999999999999",
            ).status_code == 404

            response = client.get("/api/projects/PROJ001/skill-gap")
            assert response.status_code == 200
            assert response.json()["summary"]["coverage_percent"] == 80

            response = client.get("/api/projects/PROJ001/recommendations")
            assert response.status_code == 200
            assert response.json()["summary"]["candidate_count"] == 2
        finally:
            for path in reversed(created_paths):
                response = client.delete(path)
                assert response.status_code in {204, 404}, response.text
