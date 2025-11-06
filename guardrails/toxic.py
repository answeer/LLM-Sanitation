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
import time 
# Hard-coded paths for other necessary files
CONFIG_PATH = "config/config.yaml"  # Adjust the path as needed
MANIFEST_PATH = "manifest/manifest.json"  # manifest_test
CONSOLIATED_CONTRACTS_PATH = "data/consolidated_data.csv"  # Adjust the path as needed
llm_lookup = {"claude-sonnet-4-5":"claude-sonnet-4-5",
              "llama-3-3":"swo-llama-3-3-70b-instruct",
              "GPT4.5":"gpt4o"}

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
        # Clause analysis results
    clause_analysis_results = result.get("clause_analysis_results", {})
    
    # Create a list to collect all clauses for the consolidated table
    all_clauses = []

    for clause_name, clause_data in clause_analysis_results.items():
        clause_data['Standard clause'] = clause_name
        all_clauses.append(clause_data)
    
    # Merge all clauses into a single DataFrame
    if all_clauses:
        consolidated_clauses_df = pd.concat([pd.json_normalize(clause) for clause in all_clauses], ignore_index=True)

        cols = ['Standard clause'] + [col for col in consolidated_clauses_df.columns if col != 'Standard clause']
        consolidated_clauses_df = consolidated_clauses_df[cols]
        
        # Display the consolidated clauses table
        st.write("### Clause Analysis Results")
        st.dataframe(consolidated_clauses_df.style.set_table_attributes('class="streamlit-table"'))


### this function needs to fixed based on the structure of consolidated contracts

def update_consolidated_contracts(result,contracts_df):
    
    # Update the contracts DataFrame with the new results
    new_data = pd.DataFrame([result])  # Assuming result is a dictionary
    updated_contracts_df = pd.concat([contracts_df, new_data], ignore_index=True)

    # Save the updated DataFrame to the specified path
    updated_contracts_df.to_csv(CONSOLIATED_CONTRACTS_PATH, index=False)
    
    

# Function for extracting information from a single file
def extract_single_file(contract_content, config_path, manifest, option):
    # Load config and schema
    config = load_config(str(config_path))
    schema = generate(manifest)
    manifest_instruction = manifest_to_human_instructions(manifest)

    # Build prompt
    rendered = render_prompt(config.prompt_template, schema, contract_content, manifest_instruction)
    user_prompt = rendered
    
    # Run LLM inference
    client = LLMClient(
        model=llm_lookup[option], 
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

    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    option = st.selectbox("Select an option:", ["claude-sonnet-4-5", "llama-3-3", "GPT4.5"], index=0)
    contracts_df = pd.read_csv(CONSOLIATED_CONTRACTS_PATH)
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Extract Information based on manifest", "Chat with Contract","Contract Analysis"])

    with tab1:
        
        uploaded_manifest_file = st.file_uploader("Choose the manifest file", type=["json"])

        if uploaded_manifest_file is not None:
            with open("uploaded_manifest.json", "wb") as f:
                f.write(uploaded_manifest_file.getbuffer())

        MANIFEST_PATH_ = "uploaded_manifest.json" if uploaded_manifest_file is not None else MANIFEST_PATH
        manifest = load_manifest(str(MANIFEST_PATH_))
        if "manifest" not in st.session_state:
            st.session_state['manifest'] = manifest

        with st.form(key='manifest form'):
            st.write("Default Manifest:")
            st.json(manifest, expanded=False, width=700)
            manifest_json_str = st.text_area("Edit Manifest JSON:", value=json.dumps(manifest, indent=4), height=300)
            submit_manifest = st.form_submit_button("Update Manifest")
            if submit_manifest:
                try:
                    st.session_state['manifest'] = json.loads(manifest_json_str)
                    manifest = st.session_state['manifest']
                    st.success("Manifest updated successfully!")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON format: {str(e)}")
    
        # File upload for PDF

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
                if st.button("Start Extraction", key = "start extraction button"):
                    
                    
                    if uploaded_file.name in contracts_df['Contract'].values:
                        st.warning("This contract has already been processed with defaulf manifest. Fetching cached results.")
                        
                        
                        st.success("Fetching cached results...")
                        #display_mandatory_and_clause(contracts_df[contracts_df['Contract'] == uploaded_file.name].iloc[0].to_dict())
                        
                        ## to do
                        
                        
                                    
                                    
                                 
                    else:    
                    # Display a processing message
                        with st.spinner("Processing file, please wait..."):

                            contract_content = read_pdf("uploaded_contract.pdf")
                            
                            # Process the contract
                            result = extract_single_file(
                                contract_content=contract_content, 
                                config_path=CONFIG_PATH, 
                                manifest=st.session_state['manifest'],
                                option=option
                            )

                            st.success("Extraction successful!")
                            display_mandatory_and_clause(result)
                            update_consolidated_contracts(result,contracts_df) ## might have to do some work based on structure of consolidated contracts

    with tab2:
        if uploaded_file is not None:
            user_question = st.text_input("Ask a question about the contract:")
            config = load_config(str(CONFIG_PATH))
            if st.button("Get Answer", key = "tab2 get answer button"):
                if user_question:
                    # Call the LLM with the user's question
                    client = LLMClient(
                        model=llm_lookup[option],
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
        else:
            st.warning("Please upload a PDF file enable this feature.")
    with tab3:
        
        
        
        
        user_question = st.text_input("Ask a questions to filter and select a contract:")
        config = load_config(str(CONFIG_PATH))
        if st.button("Get Answer", key = "tab3_button"):
            if user_question:
                # Call the LLM with the user's question
                client = LLMClient(
                    model=llm_lookup[option],
                    temperature=config.temperature,
                    max_output_tokens=config.max_output_tokens
                )
                
                question_prompt = f"""{user_question}\n\n{contracts_df}.
                                    Filter the contracts df based on your question and return relavent documents that satify all criteria in the question.
                                    Answer only questions that are relevant to the given content and answer only based on valid facts in the contract else say 'I don't know'."""
                answer = client.chat(question_prompt)

                # Display the answer
                st.success("Answer:")
                st.write(answer)
    
if __name__ == "__main__":
    run_streamlit_app()
