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
import os

CONFIG_PATH = "config/config.yaml"
MANIFEST_PATH = "manifest/manifest.json"
CONSOLIATED_CONTRACTS_PATH = "data/consolidated_data.csv"
llm_lookup = {"claude-sonnet-4-5":"claude-sonnet-4-5",
              "llama-3-3":"swo-llama-3-3-70b-instruct",
              "GPT4.5":"gpt4o"}

# Function to list available extracted contracts
def list_extracted_contracts():
    extracted_folder = "extracted_results"
    files = [f for f in os.listdir(extracted_folder) if f.endswith(".csv")]
    return files

# Function to display the selected contract's result
def display_selected_contract(contract_file):
    extracted_folder = "extracted_results"
    contract_df = pd.read_csv(os.path.join(extracted_folder, contract_file))
    apply_table_styling()
    st.write(f"### Results for {contract_file}")
    st.dataframe(contract_df.style.set_table_attributes('class="streamlit-table"'))

# Function to apply table styling
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

# Main app function
def run_streamlit_app():
    st.set_page_config(page_title="Contract Information Extraction", layout="wide")
    st.title("Contract Information Extraction")

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Extract Information based on manifest", "Chat with Contract", "Contract Analysis", "Preview Extracted Results"])

    with tab1:
        # Existing manifest-based extraction code
        pass

    with tab2:
        # Existing chat with contract code
        pass

    with tab3:
        # Existing contract analysis code
        pass

    with tab4:
        st.write("### Preview Previously Extracted Contract Results")

        # List available extracted contract files
        extracted_files = list_extracted_contracts()

        if extracted_files:
            # Let the user select a file to preview
            selected_file = st.selectbox("Select a previously extracted contract:", extracted_files)

            if selected_file:
                # Display the selected file's results
                display_selected_contract(selected_file)
        else:
            st.warning("No extracted contract results found.")

if __name__ == "__main__":
    run_streamlit_app()
