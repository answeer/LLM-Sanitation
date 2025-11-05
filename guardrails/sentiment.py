import pandas as pd
import streamlit as st

# Function to display mandatory key and clause analysis results separately
def display_mandatory_and_clause(result):
    # Mandatory keys
    mandatory_keys = {
        "contract id": result.get("contract id"),
        "Contract Title": result.get("Contract Title"),
        "Contract Reference": result.get("Contract Reference"),
        "msa linked contracts": result.get("msa linked contracts"),
        "parties": result.get("parties"),
        "parties Address": result.get("parties Address"),
        "effective date": result.get("effective date"),
        "Expiration Date": result.get("Expiration Date"),
        "Term Type": result.get("Term Type"),
        "Goods/Services (Spend Category)": result.get("Goods/Services (Spend Category)"),
        "Total Contract Value": result.get("Total Contract Value"),
        "Governing Law": result.get("Governing Law"),
        "Notice Period": result.get("Notice Period"),
        "signature available": result.get("signature available"),
        "signature type": result.get("signature type"),
        "Bank Signatory Name": result.get("Bank Signatory Name"),
        "Bank Signatory Position": result.get("Bank Signatory Position"),
        "Bank Signatory Date": result.get("Bank Signatory Date"),
        "Supplier signatory Name": result.get("Supplier signatory Name"),
        "Supplier signatory position": result.get("Supplier signatory position"),
        "Supplier Signatory Date": result.get("Supplier Signatory Date"),
        "mandatory clause missing": result.get("mandatory clause missing"),
        "duplicate flag": result.get("duplicate flag"),
        "anomaly flag": result.get("anomaly flag"),
        "Contract Summary": result.get("Contract Summary"),
        "validation summary": result.get("validation summary")
    }

    # Convert mandatory keys into a DataFrame
    mandatory_df = pd.DataFrame(mandatory_keys.items(), columns=["Key", "Value"])
    st.write("### Mandatory Key Information")
    st.dataframe(mandatory_df)

    # Clause analysis results
    clause_analysis_results = result.get("clause_analysis_results", {})
    st.write("### Clause Analysis Results")
    
    for clause_name, clause_data in clause_analysis_results.items():
        clause_df = pd.json_normalize(clause_data)
        st.write(f"#### {clause_name} Analysis")
        st.dataframe(clause_df)

# In your main extraction flow
if uploaded_file is not None:
    # Display the uploaded file name
    st.write(f"Uploaded file: {uploaded_file.name}")
    col1, col2 = st.columns([1, 1], gap='large')

    with col1:
        pdf_bytes = uploaded_file.read()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1200" type="application/pdf"></iframe>', unsafe_allow_html=True)

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
                schema_path=SCHEMA_PATH, 
                config_path=CONFIG_PATH, 
                manifest=manifest
            )
            st.write("Got the results successfully!")
            # Apply CSS styling to table
            apply_table_styling()

            # Display results in separate tables for mandatory keys and clauses
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success("Extraction successful!")
                display_mandatory_and_clause(result)
