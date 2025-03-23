import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from DB.index import database_manager


class EscalationHandler:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")
        print("EscalationHandler initialized!")

    def __send_email(self, student_email: str, instructor_email: str, question: str):
        try:
            subject = "Escalated Question: Student-Instructor Communication"
            body = f"""Dear {instructor_email},

The following question has been escalated from a student:

Student Email: {student_email}
Question: {question}

Please coordinate with the student directly to resolve this query.

Best regards,
Study Companion Bot"""

            # Configure MIME format
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = f"{student_email}, {instructor_email}"
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            print(f"Debug: Email Body: {body}")

            # Send the email using SSL
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                print("Debug: Establishing SSL connection...")
                server.login(self.sender_email, self.sender_password)
                print("Debug: Logged in successfully.")
                server.sendmail(
                    self.sender_email,
                    [student_email, instructor_email],
                    msg.as_string(),
                )
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def escalate_to_instructor(self, student_email: str, question: str) -> str:
        try:
            database_manager.cursor.execute(
                """
                SELECT school_id FROM users WHERE email = %s AND role = 'Student'
            """,
                (student_email,),
            )
            result = database_manager.cursor.fetchone()

            if not result:
                return "Student not found or user is not a student."

            school_id = result[0]

            database_manager.cursor.execute(
                """
                SELECT email FROM users WHERE school_id = %s AND role = 'Instructor' LIMIT 1
            """,
                (school_id,),
            )
            instructor = database_manager.cursor.fetchone()

            if not instructor:
                return f"No instructor found for School ID {school_id}."

            instructor_email = instructor[0]

            database_manager.cursor.execute(
                """
                INSERT INTO escalated_tickets (student_email, instructor_email, escalated_message, ticket_status)
                VALUES (%s, %s, %s, %s)
            """,
                (student_email, instructor_email, question, "open"),
            )

            # Send email notification
            self.__send_email(student_email, instructor_email, question)

            return f"Your question has been escalated to your instructor ({instructor_email}). They will respond shortly."
        except Exception as e:
            print(f"Error escalating to instructor: {e}")
            return "Failed to escalate the query. Please try again later."

    def get_instructor_tickets(self, instructor_email: str):
        try:
            database_manager.cursor.execute(
                """
                SELECT ticket_id, student_email, escalated_message, ticket_status, created_at
                FROM escalated_tickets
                WHERE instructor_email = %s
                ORDER BY created_at DESC
            """,
                (instructor_email,),
            )
            return database_manager.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving escalated tickets: {e}")
            return []

    def get_student_tickets(self, student_email: str):
        try:
            database_manager.cursor.execute(
                """
                SELECT ticket_id, student_email, escalated_message, ticket_status, created_at
                FROM escalated_tickets
                WHERE student_email = %s
                ORDER BY created_at DESC
            """,
                (student_email,),
            )
            return database_manager.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving escalated tickets: {e}")
            return []
        
    def get_ticket_thread(self, ticket_id: int):
        try:
            database_manager.cursor.execute(
                """
                SELECT role, message_content, created_at
                FROM ticket_messages
                WHERE ticket_id = %s
                ORDER BY created_at ASC
            """,
                (ticket_id,),
            )
            return database_manager.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving escalated tickets: {e}")
            return []
        
    def add_ticket_message(self, ticket_id: int, role: str, message_content: str):
        try:
            database_manager.cursor.execute(
                """
                INSERT INTO ticket_messages (ticket_id, role, message_content)
                VALUES (%s, %s, %s)
            """,
                (ticket_id,role,message_content),
            )
            return database_manager.connection.commit()
        except Exception as e:
            print(f"Error adding ticket message: {e}")
            return []
        
    def update_ticket(self, status: str, ticket_id_to_update: int, email: str):
        database_manager.cursor.execute(
            """
                UPDATE escalated_tickets
                SET ticket_status = %s
                WHERE ticket_id = %s AND instructor_email = %s
            """,
            (status, ticket_id_to_update, email),
        )

escalation_handler = EscalationHandler()