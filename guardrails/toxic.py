from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import sys
script_path = Path(sys.argv[0])
ROOT = str(Path(script_path).parent)
sys.path.insert(0, str(Path(script_path).parent.parent))

from prompt_engineering.prompt_builder import load_config, render_prompt
from utils.schema_loader import load_extraction_schema
from llm.llm_client import LLMClient
from utils.json_utils import coerce_to_json
from utils.read_pdf import read_pdf
from contract_extractor.logs.logging_setup import LogUtil, LogType, LogLevel
from databricks_langchain.chat_models import ChatDatabricks

def extract(contract_path: str | Path, schema_path: str | Path, config_path: str | Path) -> Dict[str, Any]:

    LogUtil.log(LogType.APPLICATION, LogLevel.INFO,'Step 1: Loading config..')
    config = load_config(str(config_path))
    schema = load_extraction_schema(str(schema_path))


    # contract_content = read_pdf(contract_path)

    # Build prompts
    # Split the rendered prompt into a concise system + user composition

    LogUtil.log(LogType.APPLICATION, LogLevel.INFO,'Step 2: Rendering prompt..')
    rendered = render_prompt(config.prompt_template, schema, Path(contract_path).read_text(encoding="utf-8"))

    # rendered = render_prompt(config.prompt_template, schema, contract_content)
    user_prompt = rendered
    LogUtil.log(LogType.APPLICATION, LogLevel.INFO,'Step 3: Runing the LLM inference..')
    client = LLMClient(model=config.model, temperature=config.temperature, max_output_tokens=config.max_output_tokens)
    raw = client.chat(user_prompt)
    LogUtil.log(LogType.APPLICATION, LogLevel.INFO,'Step 4: Parsing the output as JSON..')
    data = coerce_to_json(raw)
    return data
