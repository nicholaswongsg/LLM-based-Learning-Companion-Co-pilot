from datetime import datetime, timedelta
from DB.index import database_manager


class StreakHandler:
    def __init__(self):
        print("StreakHandler initialized!")

    def update_user_streak(self, email: str):
        """Updates the user's streak when they interact with the system."""
        today = datetime.today().date()

        try:
            # Fetch the user's current streak details
            database_manager.cursor.execute(
                "SELECT current_streak, longest_streak, last_active_date FROM user_streaks WHERE email = %s",
                (email,),
            )
            streak_data = database_manager.cursor.fetchone()

            if streak_data:
                current_streak, longest_streak, last_active_date = streak_data
                last_active_date = last_active_date or today  # Handle NULL case

                if last_active_date == today:
                    return  # Already updated today

                if last_active_date == today - timedelta(days=1):
                    current_streak += 1  # Continue streak
                else:
                    current_streak = 1  # Reset streak

                longest_streak = max(longest_streak, current_streak)

                database_manager.cursor.execute(
                    """
                    UPDATE user_streaks 
                    SET current_streak = %s, longest_streak = %s, last_active_date = %s
                    WHERE email = %s
                    """,
                    (current_streak, longest_streak, today, email),
                )
            else:
                database_manager.cursor.execute(
                    """
                    INSERT INTO user_streaks (email, current_streak, longest_streak, last_active_date)
                    VALUES (%s, 1, 1, %s)
                    """,
                    (email, today),
                )

        except Exception as e:
            print(f"Error updating streak: {e}")

    def get_streak(self, email: str):
        """Retrieves the user's current and longest streak."""
        try:
            database_manager.cursor.execute(
                "SELECT current_streak, longest_streak FROM user_streaks WHERE email = %s", (email,)
            )
            streak = database_manager.cursor.fetchone()
            return streak if streak else (0, 0)
        except Exception as e:
            print(f"Error fetching streak: {e}")
            return (0, 0)


# Create a single instance of StreakHandler for import
streak_handler = StreakHandler()
