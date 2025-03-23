from utils.date_utils import get_today_date
from DB.index import database_manager


class ChapterHanlder:
    def __init__(self):
        print("ChapterHanlder initialized!")

    def get_scheduled_chapters(self, email: str):
        """
        Fetch scheduled and incomplete chapters for the user along with today's date and subject of the curriculum.
        """
        today_date = get_today_date()
        database_manager.cursor.execute(
            """
            SELECT cc.chapter_id, cc.title, cc.scheduled_date, c.subject
            FROM curriculum_chapters cc
            JOIN curriculums c ON cc.curriculum_id = c.curriculum_id
            WHERE c.email = %s
            AND cc.scheduled_date = %s
            AND cc.is_completed = FALSE
            ORDER BY cc.scheduled_date ASC
        """,
            (email, today_date),
        )
        chapters = database_manager.cursor.fetchall()

        print("Filtered Incomplete Chapters for Today:", chapters)

        return {
            "today_date": today_date,
            "scheduled_chapters": [
                {
                    "chapter_id": row[0],
                    "title": row[1],
                    "scheduled_date": row[2].strftime("%Y-%m-%d"),
                    "subject": row[3],
                }
                for row in chapters
            ],
        }

chapter_handler = ChapterHanlder()