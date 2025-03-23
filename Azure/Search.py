import os
import openai

from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

search_client = SearchClient(
    endpoint=os.getenv("search_service_endpoint"),
    index_name=os.getenv("INDEX_NAME", "questions-llm-responses"),
    credential=AzureKeyCredential(os.getenv("search_service_key")),
)

pdf_client = SearchClient(
    endpoint=os.getenv("pdf_search_service_endpoint"),
    index_name=os.getenv("pdf_index_name", "pdf"),
    credential=AzureKeyCredential(os.getenv("pdf_search_service_key")),
)

client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# For embedding deployment name and endpoint
AZURE_OPENAI_ENDPOINT = os.environ['AZURE_OPENAI_ENDPOINT']
AZURE_OPENAI_API_KEY = os.environ['AZURE_OPENAI_API_KEY']
AZURE_OPENAI_DEPLOYMENT = os.environ['AZURE_OPENAI_DEPLOYMENT']
OPENAI_API_VERSION = os.environ['OPENAI_API_VERSION']
TEXT_EMBEDDING_MODEL_NAME = os.environ['TEXT_EMBEDDING_MODEL_NAME']