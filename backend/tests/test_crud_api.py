from concurrent.futures import ThreadPoolExecutor
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
    second_project_id = f"PROJ9{suffix}"

    created_paths: list[str] = []
    relationship_paths: list[str] = []
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

            second_project_payload = {
                "project_id": second_project_id,
                "name": f"Second API Integration Project {suffix}",
                "description": "Second project for allocation validation.",
                "status": "ACTIVE",
            }
            response = client.post(
                "/api/projects",
                json=second_project_payload,
            )
            assert response.status_code == 201, response.text
            created_paths.append(f"/api/projects/{second_project_id}")

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

            employee_skill_path = (
                f"/api/employees/{employee_id}/skills/{skill_id}"
            )
            assert client.put(
                employee_skill_path,
                json={"level": 6, "years_experience": 1},
            ).status_code == 422
            assert client.put(
                f"/api/employees/{employee_id}/skills/SK999999999999999999",
                json={"level": 3, "years_experience": 1},
            ).status_code == 404
            response = client.put(
                employee_skill_path,
                json={"level": 3, "years_experience": 1.5},
            )
            assert response.status_code == 201, response.text
            relationship_paths.append(employee_skill_path)

            response = client.put(
                employee_skill_path,
                json={"level": 4, "years_experience": 2},
            )
            assert response.status_code == 200
            assert response.json()["level"] == 4

            response = client.get(f"/api/employees/{employee_id}/skills")
            assert response.status_code == 200
            assert response.json()["total"] == 1

            requirement_path = (
                f"/api/projects/{project_id}/requirements/{skill_id}"
            )
            assert client.put(
                requirement_path,
                json={"min_level": 0, "priority": "URGENT"},
            ).status_code == 422
            response = client.put(
                requirement_path,
                json={"min_level": 3, "priority": "MUST"},
            )
            assert response.status_code == 201, response.text
            relationship_paths.append(requirement_path)

            response = client.put(
                requirement_path,
                json={"min_level": 4, "priority": "SHOULD"},
            )
            assert response.status_code == 200
            assert response.json()["min_level"] == 4

            response = client.get(
                f"/api/projects/{project_id}/requirements"
            )
            assert response.status_code == 200
            assert response.json()["total"] == 1

            first_assignment_path = (
                f"/api/projects/{project_id}/assignments/{employee_id}"
            )
            assert client.put(
                first_assignment_path,
                json={"role": "Backend Developer", "allocation": 101},
            ).status_code == 422
            response = client.put(
                first_assignment_path,
                json={"role": "Backend Developer", "allocation": 80},
            )
            assert response.status_code == 201, response.text
            relationship_paths.append(first_assignment_path)

            response = client.put(
                first_assignment_path,
                json={"role": "Tech Lead", "allocation": 70},
            )
            assert response.status_code == 200
            assert response.json()["employee_total_allocation"] == 70

            second_assignment_path = (
                f"/api/projects/{second_project_id}/assignments/{employee_id}"
            )
            response = client.put(
                second_assignment_path,
                json={"role": "Advisor", "allocation": 31},
            )
            assert response.status_code == 409
            assert "101%" in response.json()["detail"]

            response = client.put(
                second_assignment_path,
                json={"role": "Advisor", "allocation": 30},
            )
            assert response.status_code == 201, response.text
            relationship_paths.append(second_assignment_path)
            assert response.json()["employee_total_allocation"] == 100
            assert response.json()["employee_remaining_allocation"] == 0

            response = client.get(
                f"/api/projects/{project_id}/assignments"
            )
            assert response.status_code == 200
            assert response.json()["items"][0][
                "employee_total_allocation"
            ] == 100

            assert client.delete(first_assignment_path).status_code == 204
            relationship_paths.remove(first_assignment_path)
            assert client.delete(second_assignment_path).status_code == 204
            relationship_paths.remove(second_assignment_path)

            def assign_concurrently(path: str):
                return client.put(
                    path,
                    json={"role": "Concurrent Test", "allocation": 60},
                )

            assignment_paths = [
                first_assignment_path,
                second_assignment_path,
            ]
            with ThreadPoolExecutor(max_workers=2) as executor:
                concurrent_responses = list(
                    executor.map(assign_concurrently, assignment_paths)
                )

            assert sorted(
                response.status_code for response in concurrent_responses
            ) == [201, 409]
            winning_index = next(
                index
                for index, response in enumerate(concurrent_responses)
                if response.status_code == 201
            )
            relationship_paths.append(assignment_paths[winning_index])
            assert concurrent_responses[winning_index].json()[
                "employee_total_allocation"
            ] == 60

            assert client.delete(employee_skill_path).status_code == 204
            relationship_paths.remove(employee_skill_path)
            assert client.delete(employee_skill_path).status_code == 404

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
            for path in reversed(relationship_paths):
                response = client.delete(path)
                assert response.status_code in {204, 404}, response.text
            for path in reversed(created_paths):
                response = client.delete(path)
                assert response.status_code in {204, 404}, response.text
