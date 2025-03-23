import os
import psycopg2
import streamlit as st

from datetime import datetime

from Azure.Search import search_client


class DatabaseManager:
    def __init__(self):
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                port=os.getenv("DB_PORT"),
            )
            conn.autocommit = True
            self.cursor = conn.cursor()
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            st.stop()
        
    def save_message(self, email, user_question, assistant_response):
        try:
            # Save to the database and retrieve the conversation ID
            self.cursor.execute(
                """
                INSERT INTO conversation_history (email, question, response)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (email, user_question, assistant_response),
            )
            conversation_id = self.cursor.fetchone()[0]  # Get the generated ID

            # Commit the changes if using manual commit mode
            self.cursor.connection.commit()

            # Format the timestamp to remove microseconds
            formatted_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

            # Save to Azure AI Search
            document = {
                "id": str(conversation_id),  # Convert conversation ID to string
                "email": email,
                "question": user_question,
                "response": assistant_response,
                "timestamp": formatted_timestamp,
            }

            # Upload document to Azure AI Search
            result = search_client.upload_documents(documents=[document])

            # Add conversation ID to session state
            if "chat_history_ids" not in st.session_state:
                st.session_state["chat_history_ids"] = []
            st.session_state["chat_history_ids"].append(conversation_id)

            return conversation_id  # Return the conversation ID
        except Exception as e:
            print(f"Error in save_message: {e}")