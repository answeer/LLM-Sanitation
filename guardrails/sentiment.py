import streamlit as st
import json
import base64
from prompt_engineering.prompt_builder import load_config, render_prompt
from llm.llm_client_databricks import LLMClient
from utils.json_utils import coerce_to_json
from utils.read_pdf import read_pdf
from utils.generate_output_schema import generate
from utils.manifest_loader import load_manifest, manifest_to_human_instructions
import pandas as pd

# Hard-coded paths for other necessary files
CONFIG_PATH = "config/config.yaml"  # Adjust the path as needed
MANIFEST_PATH = "manifest/manifest.json"  # Adjust the path as needed

# Function to apply CSS for table styling
def apply_table_styling():
    st.markdown("""
    <style>
    .streamlit-table th, .streamlit-table td {
        word-wrap: break-word;
        white-space: normal;
        padding: 10px;
        border: 1px solid #e1e1e1;
        text-align: left;
    }
    .streamlit-table th {
        background-color: #f1f1f1;
        color: #333;
    }
    .streamlit-table tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .streamlit-table tr:nth-child(odd) {
        background-color: #ffffff;
    }
    .streamlit-table td {
        max-width: 300px;
        text-overflow: ellipsis;
        overflow: hidden;
    }
    .streamlit-table {
        border-collapse: collapse;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# Function to display mandatory key and clause analysis results separately
def display_mandatory_and_clause(result):
    # Mandatory keys
    mandatory_keys = result['mandatory_key']

    # Convert mandatory keys into a DataFrame
    mandatory_df = pd.DataFrame(mandatory_keys.items(), columns=["Key", "Value"])
    
    # Apply CSS styling for the tables
    apply_table_styling()
    
    # Display Mandatory Key Table
    st.write("### Mandatory Key Information")
    st.dataframe(mandatory_df.style.set_table_attributes('class="streamlit-table"'))

    # Clause analysis results
    clause_analysis_results = result["clause_analysis_results"]
    st.write("### Clause Analysis Results")
    
    for clause_name, clause_data in clause_analysis_results.items():
        clause_df = pd.json_normalize(clause_data)
        
        # Apply CSS styling for each clause table
        st.write(f"#### {clause_name} Analysis")
        st.dataframe(clause_df.style.set_table_attributes('class="streamlit-table"'))

# Function for extracting information from a single file
def extract_single_file(contract_content, config_path, manifest):
    # Load config and schema
    config = load_config(str(config_path))
    schema = generate(manifest)
    manifest_instruction = manifest_to_human_instructions(manifest)

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

# Streamlit app
def run_streamlit_app():
    st.set_page_config(page_title="Contract Information Extraction", layout="wide")
    st.title("Contract Information Extraction")
    st.write("Upload the manifes")
    
    uploaded_manifest_file = st.file_uploader("Choose the manifest file", type=["json"])

    if uploaded_manifest_file is not None:
        with open("uploaded_manifest.json", "wb") as f:
            f.write(uploaded_manifest_file.getbuffer())
        
    MANIFEST_PATH_ = "uploaded_manifest.json" if uploaded_manifest_file is not None else MANIFEST_PATH
    manifest = load_manifest(str(MANIFEST_PATH_))

    with st.form(key='manifest form'):
        st.write("Default Manifest:")
        st.json(manifest, expanded=False, width=700)
        manifest_json_str = st.text_area("Edit Manifest JSON:", value=json.dumps(manifest, indent=4), height=300)
        submit_manifest = st.form_submit_button("Update Manifest")
        if submit_manifest:
            try:
                manifest = json.loads(manifest_json_str)
                st.success("Manifest updated successfully!")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {str(e)}")

    # File upload for PDF
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    st.write("Upload a PDF contract to extract information.")
    # File upload for the manifest

    if uploaded_file is not None:
        # Display the uploaded file name
        st.write(f"Uploaded file: {uploaded_file.name}")
        col1, col2 = st.columns([1, 1], gap='large')

        with col1:
            pdf_bytes = uploaded_file.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1600" type="application/pdf"></iframe>', unsafe_allow_html=True)

        with col2:
            with open("uploaded_contract.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Button to trigger extraction
            if st.button("Start Extraction"):
                    
                # Display a processing message
                st.write("Processing file, please wait...")

                contract_content = read_pdf("uploaded_contract.pdf")
                        
                # Process the contract
                result = extract_single_file(
                    contract_content=contract_content, 
                    config_path=CONFIG_PATH, 
                    manifest=manifest
                )
                st.write("Got the results successfully!")
                # Apply CSS styling to table
                # apply_table_styling()

                # Display results in a transposed table format
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Extraction successful!")
                    display_mandatory_and_clause(result)

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

if __name__ == "__main__":
    run_streamlit_app()
