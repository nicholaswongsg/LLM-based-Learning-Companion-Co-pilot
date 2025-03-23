import uuid
import openai
import PyPDF2
from io import BytesIO
from typing import List, Dict, Union
from datetime import datetime

from Azure.Search import pdf_client
from DB.index import database_manager

class ContextHandler:
    def __init__(self):
        print("ContextHandler initialized!")

    def process_pdfs(
        self,
        pdf_files: List[Union[bytes]],
        user_email: str = "unknown@example.com",
        course_id: str = "default_course"
    ) -> Dict[str, str]:

        extracted_text_map = {}
        for pdf_file in pdf_files:
            try:
                filename, file_content = self._extract_file_details(pdf_file)
                # Extract all text from the PDF
                full_text = self._extract_text_from_pdf(file_content)

                # Split text into chunks for embedding
                chunks = self._split_into_chunks(full_text)
                if not chunks:
                    extracted_text_map[filename] = ""
                    continue
                # Create embedding documents and upload to Azure Search
                documents = self._create_index_documents(chunks, user_email, course_id)
                self._upload_to_pdf_index(documents)
                # Keep the full text for debugging purposes
                extracted_text_map[filename] = full_text
            except Exception as e:
                print(f"[ERROR] Processing {getattr(pdf_file, 'name', 'unknown')}: {e}")
                extracted_text_map[getattr(pdf_file, 'name', 'unknown')] = ""
        return extracted_text_map

    def _extract_file_details(self, pdf_file):
        """
        Returns a tuple (filename, file_content_bytes).
        Supports Streamlit's UploadedFile, FastAPI's UploadFile, or raw bytes.
        """
        if hasattr(pdf_file, "name") and hasattr(pdf_file, "read"):
            return pdf_file.name, pdf_file.read()
        if hasattr(pdf_file, "filename") and hasattr(pdf_file.file, "read"):
            return pdf_file.filename, pdf_file.file.read()
        if isinstance(pdf_file, bytes):
            return f"pdf_{uuid.uuid4()}.pdf", pdf_file
        raise ValueError("Unsupported file type. Must be an upload file or raw bytes.")

    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """
        Extracts and returns raw text from all pages of a PDF.
        """
        reader = PyPDF2.PdfReader(BytesIO(file_content))
        all_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            all_text.append(text)
        return "\n".join(all_text)

    def _split_into_chunks(self, full_text: str, chunk_size: int = 500) -> List[str]:
        """
        Splits the full text into word-based chunks.
        """
        words = full_text.split()
        chunks = [
            " ".join(words[i : i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _store_document_summary(self, user_email: str, filename: str, topic: str, summary: str):
        """
        Stores the document summary in the document_summaries table.
        """
        try:
            query = """
                INSERT INTO document_summaries (email, filename, topic, summary)
                VALUES (%s, %s, %s, %s)
            """
            database_manager.cursor.execute(query, (user_email, filename, topic, summary))
            database_manager.cursor.connection.commit()
        except Exception as e:
            print(f"[ERROR] Storing document summary: {e}")

    def _create_index_documents(self, chunks: List[str], user_email: str, course_id: str) -> List[dict]:
        """
        Creates a list of documents with embeddings from text chunks.
        """
        documents = []
        pdf_id = str(uuid.uuid4())

        for i, chunk in enumerate(chunks):
            try:
                response = openai.embeddings.create(
                    input=chunk,
                    model="text-embedding-ada-002"
                )
                embedding_vector = response.data[0].embedding
            except Exception as e:
                print(f"[ERROR creating embedding chunk {i}]: {e}")
                continue

            doc = {
                "id": f"{pdf_id}-{i}",
                "content": chunk,
                "user_email": user_email,
                "course_id": course_id,
                "chunk_id": str(i),
                "vector": embedding_vector,
            }
            print(f"[DEBUG] Created document: {doc}")
            documents.append(doc)
        return documents

    def _upload_to_pdf_index(self, documents: List[dict]) -> None:
        """
        Uploads the documents to the Azure Search index.
        """
        if not documents:
            print("[DEBUG] No documents to upload.")
            return
        print(f"[DEBUG] Uploading documents to index: {documents}")
        try:
            result = pdf_client.upload_documents(documents=documents)
            print(f"[DEBUG] Upload result: {result}")
            if hasattr(result, "results"):
                errors = [r for r in result.results if not r.succeeded]
                if errors:
                    print(f"[ERROR] Some documents had errors: {errors}")
        except Exception as e:
            print(f"[ERROR] Error uploading documents to Azure Search: {e}")

# Create a global instance for use elsewhere in your application
context_handler = ContextHandler()
