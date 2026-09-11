"""Operator-only CLI; prints status codes, never connection details."""

import asyncio
import json

from app.services.readiness_service import ReadinessChecker


async def check():
    checker = ReadinessChecker()
    try:
        result = await checker.check()
        print(json.dumps(result))
        return 0 if all(value == "ok" for value in result.values()) else 1
    finally:
        await checker.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
