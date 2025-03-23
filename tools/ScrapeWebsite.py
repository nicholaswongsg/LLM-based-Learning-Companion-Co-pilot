import requests

from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from bs4 import BeautifulSoup


class ScrapeWebsiteInput(BaseModel):
    url: str = Field(description="The URL of the website to scrape")


def scrape_website(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        content = soup.get_text(separator="\n", strip=True)
        return content[:5000]
    except requests.exceptions.RequestException as e:
        return f"Failed to fetch the website content: {e}"


def get_scrape_website_tool():
    return StructuredTool.from_function(
        func=scrape_website,
        name="ScrapeWebsite",
        description="Fetch and parse content from a website.",
        args_schema=ScrapeWebsiteInput,
        return_direct=False,
    )
