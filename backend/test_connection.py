from app.db.graph import graph_db


def main() -> int:
    try:
        graph_db.verify_connection()
        print("CognoDB connection successful.")

        with graph_db.driver.session() as session:
            result = session.run("RETURN 1 AS connected")
            record = result.single()
            print("Database returned:", record["connected"])
        return 0
    except Exception as exc:
        print(
            f"CognoDB connection failed ({type(exc).__name__}). "
            "Check the configured environment variables."
        )
        return 1
    finally:
        graph_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
