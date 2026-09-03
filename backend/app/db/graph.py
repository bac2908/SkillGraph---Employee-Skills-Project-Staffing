from neo4j import GraphDatabase

from app.core.config import settings


class GraphDB:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.cognodb_uri,
            auth=(
                settings.cognodb_user,
                settings.cognodb_password,
            ),
        )

    def verify_connection(self):
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()


graph_db = GraphDB()
