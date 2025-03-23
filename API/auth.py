import bcrypt
from DB.index import database_manager


class AuthHandler:
    def __init__(self):
        print("AuthHandler initialized!")

    def user_exists(self, user_email: str) -> bool:
        database_manager.cursor.execute(
            "SELECT COUNT(*) FROM users WHERE email = %s", (user_email,)
        )
        return database_manager.cursor.fetchone()[0] > 0

    def register_user(self, user_email: str, password: str, school_id: int, role: str):
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        database_manager.cursor.execute(
            """
            INSERT INTO users (email, password_hash, role, school_id)
            VALUES (%s, %s, %s, %s)
            """,
            (user_email, hashed.decode("utf-8"), role, school_id),
        )

    def validate_user(self, user_email: str, password: str) -> bool:
        database_manager.cursor.execute(
            "SELECT password_hash FROM users WHERE email = %s", (user_email,)
        )
        result = database_manager.cursor.fetchone()
        if not result:
            return False
        stored_hash = result[0]
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))

auth_handler = AuthHandler()