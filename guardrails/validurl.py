import os 
import re
import json
from typing import List, Dict, Any

from PyPDF2 import PdfReader
from dotenv import load_dotenv

# ---- Your existing LLM shim -------------------------------------------------
from llm import call_llm

# ---- LangChain imports ------------------------------------------------------
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_core.language_models import LLM

from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_CATEGORIES_PATH = os.path.join(BASE_DIR, "metadata", "master_catagories.txt")
DOCUMENTS_FOLDER = os.path.join(BASE_DIR, "document")
OUTPUT_JSON = os.path.join(BASE_DIR, "visa_compliance_langgraph.json")


# ----------------------------------------------------------------------------
# Data models (Pydantic)
# ----------------------------------------------------------------------------
class ChangeItem(BaseModel):
    description: str
    impact: str
    deadline_date: str
    source_context: str
    impact_or_awareness: str
    countries_impacted: List[str] = Field(default_factory=list)
    mapped_category: str = Field(default="Uncategorized")

class DocumentSummary(BaseModel):
    filename: str
    article_id: str
    publication_date: str
    effective_date: str
    topic_of_change: str
    summary_of_change: str
    list_of_changes: List[ChangeItem]

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def read_master_categories(path: str) -> Dict[str, List[str]]:
    categories: Dict[str, List[str]] = {}
    if not os.path.exists(path):
        return categories
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    current_cat = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) > 2 and line[0].isdigit() and line[1] == ".":
            current_cat = line[3:]
            categories[current_cat] = []
        elif current_cat:
            categories[current_cat].append(line)
    return categories


def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def build_system_prompt(master_categories: Dict[str, List[str]]) -> str:
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


def robust_json_loads(s: str) -> Any:
    s = s.strip().strip("`")
    s = s.replace("```json", "").replace("```", "")

    try:
        return json.loads(s)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", s)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    cleaned = s.replace("json", "").replace("\n", " ")
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Could not parse JSON from model output")

# ----------------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------------

def _extract_compliance_from_pdf(filename: str) -> str:
    pdf_path = os.path.join(DOCUMENTS_FOLDER, filename)
    if not os.path.isfile(pdf_path):
        return json.dumps({
            "status": "error",
            "message": f"File not found: {pdf_path}"
        })

    master_categories = read_master_categories(MASTER_CATEGORIES_PATH)
    text = extract_pdf_text(pdf_path)
    system_prompt = build_system_prompt(master_categories)

    llm_query = f"System prompt:\n{system_prompt}\n\nDocument text:\n{text}"
    raw = call_llm(llm_query)

    try:
        doc_json = robust_json_loads(raw)
    except Exception:
        doc_json = {
            "filename": filename,
            "article_id": "Error",
            "publication_date": "Error",
            "effective_date": "Error",
            "topic_of_change": "Error",
            "summary_of_change": str(raw),
            "list_of_changes": []
        }

    doc_json.setdefault("filename", filename)
    doc_json.setdefault("article_id", "Unknown")
    doc_json.setdefault("publication_date", "Unknown")
    doc_json.setdefault("effective_date", "Unknown")
    doc_json.setdefault("topic_of_change", "Unknown")
    doc_json.setdefault("summary_of_change", "")
    doc_json.setdefault("list_of_changes", [])

    return json.dumps(doc_json, ensure_ascii=False)


def _create_compliance_markdown_llm(summary_dict: dict, format_instructions: str = None) -> str:
    if format_instructions is None:
        format_instructions = (
             "Summarize the following compliance bulletin for the compliance team in Markdown format. "
            "Include all key details, and use headings, bullet points, and sections as appropriate. "
            "If the format instructions change, adapt the output accordingly."
        )
    system_prompt = f"{format_instructions}\n\nInput JSON:\n{json.dumps(summary_dict, indent=2, ensure_ascii=False)}"
    markdown = call_llm(system_prompt)
    return markdown.strip()


def _save_summaries(summaries: List[dict]) -> str:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)
    return OUTPUT_JSON

def _list_documents() -> str:
    files = [f for f in os.listdir(DOCUMENTS_FOLDER) if f.lower().endswith('.pdf')]
    return json.dumps(files, ensure_ascii=False)

# Wrap as LangChain Tools
tools = [
    Tool(
        name="extract_compliance_from_pdf",
        func=_extract_compliance_from_pdf,
        description=(
            "Extract a structured JSON summary from a Visa compliance PDF. "
            "Input: the PDF filename (string) located under the 'document' folder. "
            "Output: JSON string with fields article_id, publication_date, effective_date, topic_of_change, summary_of_change, list_of_changes[]."
        ),
    ),
    Tool(
        name="create_compliance_markdown_llm",
        func=lambda summary_json_or_dict, format_instructions=None: _create_compliance_markdown_llm(
            json.loads(summary_json_or_dict) if isinstance(summary_json_or_dict, str) else summary_json_or_dict,
            format_instructions,
        ),
        description=(
            """
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
        ),
    ),
    Tool(
        name="save_summaries",
        func=lambda summaries_json_or_list: _save_summaries(
            json.loads(summaries_json_or_list) if isinstance(summaries_json_or_list, str) else summaries_json_or_list
        ),
        description=(
            "Save a list of summary dicts to a JSON file. Input: JSON string or list of dicts. Output: file path."
        ),
    ),
    Tool(
        name="list_documents",
        func=lambda _: _list_documents(),
        description="List available PDF documents in the {} folder.".format(DOCUMENTS_FOLDER),
    ),
]

# ----------------------------------------------------------------------------
# Simple LangChain LLM wrapper around call_llm()
# ----------------------------------------------------------------------------
class LocalCallLLM(LLM):
    @property
    def _llm_type(self) -> str:
        return "local-call-llm"

    def _call(self, prompt: str, stop: List[str] | None = None) -> str:
        return call_llm(prompt)

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {}

# ----------------------------------------------------------------------------
# Agent factory (using OpenAI Functions Agent)
# ----------------------------------------------------------------------------

def build_agent(verbose: bool = True):
    llm = LocalCallLLM()
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        verbose=verbose,
        handle_parsing_errors=True,
    )
    return agent

def chat(agent, query: str, chat_history: list):
    """Send query to agent, keep track of chat history automatically."""
    result = agent.invoke({"input": query, "chat_history": chat_history})

    # 保存到 chat_history
    chat_history.append(("user", query))
    chat_history.append(("assistant", result))

    return result


# ----------------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    agent = build_agent(verbose=True)

    chat_history = []
    filename = "AI14871.pdf"
    task = (
        "List the available PDFs, pick {} if present, ".format(filename),
        "Use extract_compliance_from_pdf with input {}. ".format(filename),
        "Then, save the JSON summary to disk."
        "After that, take the JSON summary to call create_compliance_markdown_llm to Create a professional markdown summary."
    )
    result = chat(agent, task, chat_history)
    print("\n--- Agent Final Answer (task) ---\n", result)




