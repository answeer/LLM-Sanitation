import os
import json
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from llm import call_llm
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Load environment variables if needed
load_dotenv()

MASTER_CATEGORIES_PATH = os.path.join("metadata", "master_catagories.txt")
DOCUMENTS_FOLDER = "document"
OUTPUT_JSON = "visa_compliance_langgraph.json"

# Pydantic model for a change item
class ChangeItem(BaseModel):
    description: str
    impact: str
    deadline_date: str
    source_context: str
    impact_or_awareness: str
    countries_impacted: List[str] = Field(default_factory=list)
    mapped_category: str = Field(default="Uncategorized")

# Pydantic model for a document summary
class DocumentSummary(BaseModel):
    filename: str
    article_id: str
    publication_date: str
    effective_date: str
    topic_of_change: str
    summary_of_change: str
    list_of_changes: List[ChangeItem]

# Pydantic model for the agent state
class AgentState(BaseModel):
    summaries: List[DocumentSummary] = Field(default_factory=list)

# Read master categories
def read_master_categories(path):
    categories = {}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    current_cat = None
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit() and line[1] == ".":
            current_cat = line[3:]
            categories[current_cat] = []
        elif current_cat and line:
            categories[current_cat].append(line)
    return categories

# Extract text from PDF
def extract_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# Build system prompt for LLM extraction and mapping
def build_system_prompt(master_categories):
    prompt = (
        "You are a compliance extraction agent. "
        "Given the text of a Visa compliance bulletin, extract the following details as a JSON object: "
        "article_id, publication_date, effective_date, topic_of_change, summary_of_change, "
        "list_of_changes (each with description, impact, deadline_date, source_context, impact_or_awareness , countries_impacted mapped_category), "
        "and map each change to one of the following master categories: "
        "source_context is the text supporting the change description in the document. "
        "countries_impacted is a list of countries impacted by the change. "
    )
    for cat, items in master_categories.items():
        prompt += f"\n{cat}: " + ", ".join(items)
    prompt += (
        "\nIf a change does not fit any category, use 'Uncategorized'. "
        "Return only the JSON object, no explanation."
    )
    return prompt

# StateGraph node: process a single document
def process_document_node(state: AgentState, filename: str, master_categories: Dict[str, List[str]]) -> AgentState:
    pdf_path = os.path.join(DOCUMENTS_FOLDER, filename)
    text = extract_pdf_text(pdf_path)
    system_prompt = build_system_prompt(master_categories)
    llm_query = f"System prompt:\n{system_prompt}\n\nDocument text:\n{text}"  # Limit to 4000 chars for input
    response = call_llm(llm_query)
    response = response.replace("json","").replace("\n","").replace("`","").replace("```","")

    # Remove leading/trailing whitespace and newlines
    response_clean = response.strip()

    try:
        doc_json = json.loads(response_clean)
        print(doc_json)
        # Parse list_of_changes into ChangeItem objects
        changes = [ChangeItem(**change) for change in doc_json.get("list_of_changes", [])]
        summary = DocumentSummary(
            filename=filename,
            article_id=doc_json.get("article_id", "Unknown"),
            publication_date=doc_json.get("publication_date", "Unknown"),
            effective_date=doc_json.get("effective_date", "Unknown"),
            topic_of_change=doc_json.get("topic_of_change", "Unknown"),
            summary_of_change=doc_json.get("summary_of_change", ""),
            list_of_changes=changes
        )
    except Exception as e:
        print("Error  ", e)
        summary = DocumentSummary(
            filename=filename,
            article_id="Error",
            publication_date="Error",
            effective_date="Error",
            topic_of_change="Error",
            summary_of_change=str(response_clean),
            list_of_changes=[]
        )
    state.summaries.append(summary)
    print(f"\nSummary for {filename}:")
    print(summary.model_dump_json(indent=2))
    return state

# StateGraph node: save all summaries
def save_summaries_node(state: AgentState) -> AgentState:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump([s.dict() for s in state.summaries], f, indent=2)
    print(f"\nAll summaries saved to {OUTPUT_JSON}")
    return state

if __name__ == "__main__":

    master_categories = read_master_categories(MASTER_CATEGORIES_PATH)
    state = AgentState()
    graph = StateGraph(AgentState)
    # Add nodes for each PDF file
    for filename in os.listdir(DOCUMENTS_FOLDER)[:4]:
        filename = "AI14871.pdf"
        if filename.lower().endswith(".pdf"):
            state = process_document_node(state, filename, master_categories)

        break
    # Save summaries
    state = save_summaries_node(state)





import json
from llm import call_llm
from langchain.tools import tool

@tool
def create_compliance_markdown_llm(summary_dict: dict, format_instructions: str = None) -> str:
    # System prompt for LLM summarization
    if format_instructions is None:
        format_instructions = (
            "Summarize the following compliance bulletin for the compliance team in Markdown format. "
            "Include all key details, and use headings, bullet points, and sections as appropriate. "
            "If the format instructions change, adapt the output accordingly."
        )
    system_prompt = f"{format_instructions}\n\nInput JSON:\n{json.dumps(summary_dict, indent=2)}"
    markdown = call_llm(system_prompt)
    return markdown.strip()

if __name__ == "__main__":
    # Example input (replace with actual input or file read)
    input_json = '''{
      "filename": "11.pdf",
      "article_id": "AI 23",
      "publication_date": "30 January 2025",
      "effective_date": "April 2025",
      "topic_of_change": "Introduction of VCS Hub and Visa B2B Payables",
      "summary_of_change": "Visa will launch the Visa Commercial Solutions (VCS) Hub platform, along with the next gen",
      "list_of_changes": [
        {
          "description": "Launch of VCS Hub platform and transition of current VPA clients to Visa B2B Payables",
          "impact": "Awareness only for Issuers",
          "deadline_date": "April 2025",
          "source_context": "Effective April 2025, Visa will launch the Visa Commercial Solutions (VCS) Hub platf",
          "impact_or_awareness": "Awareness",
          "mapped_category": "Product & Service Updates"
        },
        {
          "description": "New Visa B2B Payables pricing structure implementation",
          "impact": "Financial impact for VPA clients",
          "deadline_date": "1 September 2025",
          "source_context": "The following pricing will be effective 1 September 2025: • Generic user interface (UI): 4.0 bps per use • White–label UI: 8.0 bps per use • Visa Connector: 4.0 bps per use • API + support UI: 2.0 bps per use • Transaction fee: A USD 1.00 per transaction fee cap will be applied to all Visa B2B Payables transactions regardless of the VCS Hub access channel(s) being utilized.",
          "impact_or_awareness": "Impact",
          "mapped_category": "Interchange Fees & Assessments"
        },
        {
          "description": "Introduction of VCS Hub monthly subscription fee",
          "impact": "Financial impact for all VCS Hub users",
          "deadline_date": "1 October 2025",
          "source_context": "Additionally, a VCS Hub monthly subscription fee of USD 2,500 will apply to all VCS Hub users effective 1 October 2025.",
          "impact_or_awareness": "Impact",
          "mapped_category": "Interchange Fees & Assessments"
        },
        {
          "description": "Implementation of volume-based discount tiers for Visa B2B Payables",
          "impact": "Potential cost savings for high-volume users",
          "deadline_date": "1 September 2025",
          "source_context": "With the new Visa B2B Payables solution and associated pricing, there will be a usage fee discount applied each month where applicable, as driven by usage. The discount will be based on a client's total monthly Visa B2B Payables payment volume and will be applied against the applicable Visa B2B Payables transaction usage fees for that month.",
          "impact_or_awareness": "Impact",
          "mapped_category": "Interchange Fees & Assessments"
        }
      ]
    }'''
    summary_dict = json.loads(input_json)
    format_instruction = """
    Create a professional markdown summary for Visa compliance bulletins, suitable for a compliance team. Use the following format:

    # [Title: Topic of Change]

    **Article ID:** [article_id]
    **Filename:** [filename]
    **Publication Date:** [publication_date]
    **Effective Date:** [effective_date]

    ## Description
    [summary_of_change]

    ## Key Changes Table
    | Description | Impact/Awareness | Impact | Deadline Date | Mapped Category |
    |-------------|------------------|--------|--------------|----------------|
    | ...fill for each change... |

    ## Details of Each Change
    For each change, provide:
    - **Description**
    - **Impact/Awareness**
    - **Impact**
    - **Deadline Date**
    - **Source Context**
    - **Mapped Category**

    Make the summary concise, clear, and easy to scan for compliance professionals. If the format instructions change, adapt the output accordingly.
    """
    markdown = create_compliance_markdown_llm(summary_dict, format_instruction)
    print(markdown)

