import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import base64
from utils.schema_loader import load_extraction_schema
from prompt_engineering.prompt_builder import load_config, render_prompt
from llm.llm_client_databricks import LLMClient
from utils.json_utils import coerce_to_json
from utils.read_pdf import read_pdf
from utils.manifest_loader import load_manifest, manifest_to_human_instructions
from logs.logging_setup import LogUtil, LogType, LogLevel
import pandas as pd

# Hard-coded paths for other necessary files
SCHEMA_PATH = "schema/extraction_schema.json"  # Adjust the path as needed
CONFIG_PATH = "config/config.yaml"  # Adjust the path as needed
MANIFEST_PATH = "manifest/manifest.yml"  # Adjust the path as needed

# Function for extracting information from a single file
def extract_single_file(contract_path, schema_path, config_path, manifest_path) -> Dict[str, Any]:
    try:
        LogUtil.log(LogType.APPLICATION, LogLevel.INFO, f'Processing file: {contract_path}')
        
        # Load config and schema
        config = load_config(str(config_path))
        schema = load_extraction_schema(str(schema_path))
        manifest = load_manifest(str(manifest_path))
        manifest_instruction = manifest_to_human_instructions(manifest)

        # Display manifest instructions in a table
        if manifest_instruction:
            st.write("Manifest Details:")
            st.json(manifest, expanded=False, width=700)
        
        # Read contract content
        contract_content = read_pdf(contract_path)
        
        if not contract_content.strip():
            LogUtil.log(LogType.APPLICATION, LogLevel.WARNING, f'Empty file: {contract_path}')
            return {"error": "Empty file", "filename": str(contract_path)}

        # Build prompt
        rendered = render_prompt(config.prompt_template, schema, contract_content, manifest_instruction)
        user_prompt = rendered
        
        # Run LLM inference
        client = LLMClient(
            model=config.model, 
            temperature=config.temperature, 
            max_output_tokens=config.max_output_tokens
        )
        raw = client.chat(user_prompt)
        
        # Parse output
        data = coerce_to_json(raw)
        
        return data
        
    except Exception as e:
        LogUtil.log(LogType.APPLICATION, LogLevel.ERROR, f"Extraction failed for {contract_path}: {str(e)}")
        return {
            "error": str(e),
            "filename": str(contract_path),
            "_metadata": {
                "source_file": str(contract_path),
                "extraction_timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
        }

# Function to apply CSS styles for wrapping text
def apply_table_styling():
    st.markdown("""
    <style>
    .streamlit-table th, .streamlit-table td {
        word-wrap: break-word;
        white-space: normal;
        max-width: 300px; /* Adjust column width */
    }
    .streamlit-table td {
        text-overflow: ellipsis;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# Streamlit app
def run_streamlit_app():
    st.set_page_config(page_title="Contract Information Extraction", layout="wide")
    st.title("Contract Information Extraction")
    st.write("Upload a PDF contract to extract information.")
    
    # File upload for PDF
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    st.write("Upload the manifest for the document type.")
    # File upload for the manifest
    uploaded_manifest_file = st.file_uploader("Choose the manifest file", type=["json"])

    if uploaded_file is not None:
        # Display the uploaded file name
        st.write(f"Uploaded file: {uploaded_file.name}")
        col1, col2 = st.columns([1, 1], gap='large')

        with col1:
            pdf_bytes = uploaded_file.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="2400" type="application/pdf"></iframe>', unsafe_allow_html=True)

        with col2:
            with open("uploaded_contract.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())
            # User question input
            user_question = st.text_input("Ask a question about the contract:")
            config = load_config(str(CONFIG_PATH))
            if st.button("Get Answer"):
                if user_question:
                    # Call the LLM with the user's question
                    client = LLMClient(
                        model=config.model, 
                        temperature=config.temperature, 
                        max_output_tokens=config.max_output_tokens
                    )
                    contract_content = read_pdf("uploaded_contract.pdf")
                    question_prompt = f"{user_question}\n\n{contract_content}. Answer only questions that are relevant to the given content and answer only based on valid facts in the contract else say 'I don't know'."
                    answer = client.chat(question_prompt)

                    # Display the answer
                    st.success("Answer:")
                    st.write(answer)
                else:
                    st.warning("Please enter a question.")
            
            # Button to trigger extraction
            if st.button("Start Extraction"):
                # Save uploaded manifest file if available
                if uploaded_manifest_file is not None:
                    with open("uploaded_manifest.json", "wb") as f:
                        f.write(uploaded_manifest_file.getbuffer())
                    
                MANIFEST_PATH_ = "uploaded_manifest.json" if uploaded_manifest_file is not None else MANIFEST_PATH
                manifest = load_manifest(str(MANIFEST_PATH_))
                
                print(manifest)
                manifest_instruction = manifest_to_human_instructions(manifest)

                # Display manifest instructions
                if manifest_instruction:
                    st.write("Manifest Instructions:")
                    
                # Display a processing message
                st.write("Processing file, please wait...")
                        
                # Process the contract
                result = extract_single_file(
                    contract_path="uploaded_contract.pdf", 
                    schema_path=SCHEMA_PATH, 
                    config_path=CONFIG_PATH, 
                    manifest_path=MANIFEST_PATH_
                )

                # Apply CSS styling to table
                apply_table_styling()

                # Display results in a transposed table format
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Extraction successful!")
                    # Convert JSON result to pandas DataFrame for table display
                    if isinstance(result, dict):
                        result_df = pd.json_normalize(result)
                        result_df = result_df.transpose()  # Transpose to make the columns as rows
                        st.dataframe(result_df)  # Display result as a table

if __name__ == "__main__":
    run_streamlit_app()
