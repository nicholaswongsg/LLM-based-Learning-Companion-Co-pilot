from langchain.tools import StructuredTool

def get_upload_pdfs_tool():
    return StructuredTool.from_function(
        func=lambda: "Uploading PDF for course context...",
        name="PDFtoContext",
        description=(
            "Use this tool when the user wants to upload PDFs to an enrolled course for context. "
            "This tool initiates the PDF upload process and should not be used for direct responses."
        ),
        return_direct=True,
    )
