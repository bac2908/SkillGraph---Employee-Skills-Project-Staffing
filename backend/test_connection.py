from app.db.graph import graph_db


try:
    graph_db.verify_connection()
    print("CognoDB connection successful.")

    with graph_db.driver.session() as session:
        result = session.run("RETURN 1 AS connected")
        record = result.single()
        print("Database returned:", record["connected"])

except Exception as exc:
    print("CognoDB connection failed.")
    print(exc)

finally:
    graph_db.close()
