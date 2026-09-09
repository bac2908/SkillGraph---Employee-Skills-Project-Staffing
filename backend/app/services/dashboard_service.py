from datetime import UTC, datetime

from app.repositories import dashboard_repository


class DashboardService:
    @staticmethod
    def overview() -> dict:
        result = dashboard_repository.get_dashboard()
        # Response generation time, not a claim of snapshot isolation or polling.
        return {**result, "generated_at": datetime.now(UTC)}
