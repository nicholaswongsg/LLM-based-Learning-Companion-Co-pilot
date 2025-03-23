import re
import json
import PyPDF2

from io import BytesIO
from datetime import datetime
from typing import List, Dict
from fastapi import UploadFile

from utils.llm_utils import get_llm
from DB.index import database_manager
from API.curriculum import curriculum_handler


class PdfHandler:
    def __init__(self):
        print("PdfHandler initialized!")

    def process_pdfs(self, pdf_files: List) -> Dict[str, str]:
        """
        Extract text from multiple uploaded PDFs and organize content by file.

        Supports Streamlit's UploadedFile and FastAPI's UploadFile.
        """
        extracted_text_by_pdf = {}
        for pdf_file in pdf_files:
            try:
                filename, file_content = self._extract_file_details(pdf_file)
                pdf_text = self._extract_text_from_pdf(file_content)
                extracted_text_by_pdf[filename] = pdf_text.strip()
            except Exception as e:
                print(f"Failed to process {pdf_file}: {e}")
                extracted_text_by_pdf[filename if 'filename' in locals() else "Unknown"] = ""

        return extracted_text_by_pdf

    @staticmethod
    def _extract_file_details(pdf_file) -> (str, bytes): # type: ignore
        """
        Extract filename and content from the uploaded file.
        """
        if hasattr(pdf_file, "name"):  # Streamlit's UploadedFile
            return pdf_file.name, pdf_file.read()
        elif hasattr(pdf_file, "filename"):  # FastAPI's UploadFile
            return pdf_file.filename, pdf_file.file.read()
        raise ValueError(f"Unsupported file type: {type(pdf_file)}")

    @staticmethod
    def _extract_text_from_pdf(file_content: bytes) -> str:
        """
        Extract text from a PDF file.
        """
        text = ""
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text

    def generate_curriculum(self, email: str, pdf_files: List[UploadFile]) -> str:
        """
        Handle PDF uploads and generate a curriculum using an LLM.
        """
        llm = get_llm()
        extracted_text = self.process_pdfs(pdf_files)
        if not any(extracted_text.values()):
            return "No content could be extracted from the uploaded PDFs."

        combined_text = "\n\n".join(extracted_text.values())
        subject = self._generate_subject(combined_text, llm)
        if not subject:
            return "Failed to generate a subject name from the uploaded PDFs."

        chapters = self._generate_chapters(subject, llm)
        if not chapters:
            return "Failed to generate valid chapters from the LLM response."

        return self._save_curriculum_to_db(email, subject, chapters)

    def _generate_subject(self, text: str, llm) -> str:
        """
        Generate a subject name based on extracted content using an LLM.
        """
        subject_request = f"""
        Based on the following content:\n{text[:1000]}
        Suggest a concise course name for a curriculum. Reply back only with the course name.
        """
        subject_response = llm([{"role": "user", "content": subject_request}])
        return subject_response.content.strip()[:100]

    def _generate_chapters(self, subject: str, llm) -> List[Dict]:
        """
        Generate course chapters and descriptions using an LLM.
        """
        chapter_request = f"""
        Create a course outline for '{subject}' in JSON format as a list of dictionaries with 'title' and 'description' keys.
        """
        response = llm([{"role": "user", "content": chapter_request}])
        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            match = re.search(r'(\[.*\])', response.content, re.DOTALL)
            return json.loads(match.group(1)) if match else None

    def _save_curriculum_to_db(self, email: str, subject: str, chapters: List[Dict]) -> str:
        """
        Save curriculum and chapters to the database.
        """
        start_date = datetime.now().strftime("%Y-%m-%d")
        commitment_level = "Weekly"
        total_chapters = len(chapters)
        scheduled_dates = curriculum_handler.calculate_scheduled_dates(commitment_level, start_date, total_chapters)

        try:
            # Save curriculum
            database_manager.cursor.execute("""
                INSERT INTO curriculums (email, subject, goal_description, commitment_level, duration_per_session, start_date, learning_goal, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING curriculum_id
            """, (
                email,
                subject,
                f"Curriculum generated from {subject}"[:100],
                commitment_level,
                60,
                start_date,
                f"Learn topics from {subject}"[:100],
                datetime.now()
            ))
            curriculum_id = database_manager.cursor.fetchone()[0]

            # Save chapters
            for i, chapter in enumerate(chapters):
                database_manager.cursor.execute("""
                    INSERT INTO curriculum_chapters (curriculum_id, title, description, scheduled_date)
                    VALUES (%s, %s, %s, %s)
                """, (curriculum_id, chapter['title'], chapter['description'], scheduled_dates[i]))

            return f"Curriculum '{subject}' generated successfully with ID {curriculum_id}."

        except Exception as e:
            return f"Error saving curriculum or chapters: {e}"


pdf_handler = PdfHandler()
