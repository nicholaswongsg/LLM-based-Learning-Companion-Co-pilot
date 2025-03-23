import os
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from Azure.Search import pdf_client, client
from utils.llm_utils import get_llm_fast

class RetrieveCourseContextInput(BaseModel):
    query: str = Field(..., description="The search query for retrieving context.")
    course_id: str = Field(..., description="The course identifier to restrict the search.")

def filter_relevant_results(query: str, search_results: list) -> list:
    print("[DEBUG] Filtering search results using LLM grader.")

    if not search_results:
        return []

    llm = get_llm_fast()
    prompt = f"""
    You are a grader tasked with filtering search results for relevance.
    The query is: "{query}"
    
    Given the following search results, determine which ones are relevant. 
    Return a JSON list of only the relevant results.

    Search Results:
    {search_results}

    Output format (JSON list of relevant results):
    [
        "Relevant Result 1",
        "Relevant Result 2",
        ...
    ]
    """

    try:
        response = llm.invoke(prompt)
        relevant_results = eval(response)  # Convert string response to list
        print(f"[DEBUG] Filtered results count: {len(relevant_results)}")
        return relevant_results
    except Exception as e:
        print(f"[ERROR] LLM filtering failed: {str(e)}")
        return search_results  # Fallback: Return all results if filtering fails

def get_course_context_tool(email: str) -> StructuredTool:
    def course_context_func(query: str, course_id: str) -> str:
        print(f"[DEBUG] Starting course_context_func with query: '{query}' and course_id: '{course_id}'")
        try:
            # Generate Embedding
            print(f"[DEBUG] Generating embedding for query: '{query}'")
            embedding_response = client.embeddings.create(
                model=os.getenv('TEXT_EMBEDDING_MODEL_NAME'),
                input=[query]
            )
            embedding_vector = embedding_response.data[0].embedding
            print(f"[DEBUG] Embedding generated successfully. Length: {len(embedding_vector)}")

            # Construct Filter Query - filter on both email and course_id
            filter_query = f"user_email eq '{email}' and course_id eq '{course_id}'"
            print(f"[DEBUG] Filter query constructed: {filter_query}")

            # Perform Vector Search
            print("[DEBUG] Performing vector search with embedding vector.")
            search_results = pdf_client.search(
                search_text="*",
                filter=filter_query,
                vector_queries=[
                    {
                        "kind": "vector",
                        "vector": embedding_vector,
                        "fields": "vector", 
                        "k": 6
                    }
                ]
            )

            raw_results = list(search_results)
            print(f"[DEBUG] Vector search completed. Number of raw results: {len(raw_results)}")

            # Extract Content
            raw_contexts = [result.get("content", "") for result in raw_results if result.get("content", "")]
            print(f"[DEBUG] Extracted raw contexts count: {len(raw_contexts)}")

            # Filter Relevant Results Using LLM Grader
            filtered_contexts = filter_relevant_results(query, raw_contexts)

            if not filtered_contexts:
                print("[DEBUG] No relevant context found after filtering.")
                return "No relevant context found from your uploaded course materials."

            final_context = "\n\n".join(filtered_contexts)
            print(f"[DEBUG] Final concatenated context length: {len(final_context)}")
            return final_context

        except Exception as e:
            print(f"[ERROR] Exception occurred: {str(e)}")
            return f"Error retrieving course context: {str(e)}"

    return StructuredTool.from_function(
        func=course_context_func,
        args_schema=RetrieveCourseContextInput,
        name="retrieve_course_context",
        description=(
            "Retrieve relevant context from the uploaded textbook/course materials by performing "
            "a vector search using the query's embedding vector. The results are further filtered "
            "using an LLM to ensure only relevant content is returned."
        )
    )
