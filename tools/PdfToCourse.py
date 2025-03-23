from langchain.tools import StructuredTool


def get_pdftocourse_tool():
    return StructuredTool.from_function(
        func=lambda: "Uploading PDF to create course...",
        name="PDFtoCourse",
        description=(
            "Always use this tool when the user wants to upload PDFs to create a course. "
            "Do not attempt to respond directly; invoke this tool immediately to start the upload process."
        ),
        return_direct=True,  # Directly return the string response
    )