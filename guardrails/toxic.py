import streamlit as st
import pandas as pd
import json

def display_document_info(data):
    """Display document information in a structured way"""
    
    st.set_page_config(page_title="Document Information Viewer", layout="wide")
    st.title("📄 Document Information Viewer")
    
    # Basic Document Information
    st.header("📋 Basic Information")
    
    st.write(f"**Document ID:** {data.get('document_id', 'N/A')}")
    st.write(f"**Filename:** {data.get('filename', 'N/A')}")
    
    classification = data.get("classification", {})
    st.write(f"**Category:** {classification.get('category', 'N/A')}")
    st.write(f"**Document Type:** {classification.get('document_type', 'N/A')}")
    st.write(f"**Confidence:** {classification.get('confidence', 0)*100:.1f}%" if classification.get('confidence') else "**Confidence:** N/A")
    
    # Related Documents Section
    st.header("🔗 Related Documents")
    related_docs = data.get("related_document_ids", [])
    
    if related_docs:
        related_data = []
        for doc in related_docs:
            related_data.append({
                "Relation Type": doc.get("relation_type", "N/A"),
                "Document ID Reference": doc.get("document_id_reference", "N/A"),
                "Confidence": f"{doc.get('confidence', 0)*100:.1f}%" if doc.get('confidence') else "N/A"
            })
        
        related_df = pd.DataFrame(related_data)
        st.dataframe(related_df, use_container_width=True, hide_index=True)
    else:
        st.info("No related documents found")
    
    # Key Values Section
    st.header("🔑 Key Values")
    key_values = data.get("key_values", [])
    
    if key_values:
        key_data = []
        for item in key_values:
            key_data.append({
                "Key": item.get("key", "N/A"),
                "Value": item.get("value", "N/A"),
                "Normalized Value": item.get("value_normalized", "N/A"),
                "Confidence": f"{item.get('confidence', 0)*100:.1f}%" if item.get('confidence') else "N/A"
            })
        
        key_df = pd.DataFrame(key_data)
        st.dataframe(key_df, use_container_width=True, hide_index=True)
            
    else:
        st.warning("No key values found")

def load_json_data(uploaded_file):
    """Load JSON data from uploaded file"""
    try:
        data = json.load(uploaded_file)
        return data
    except Exception as e:
        st.error(f"Error loading JSON file: {e}")
        return None

def main():
    """Main function with file upload capability"""
    st.sidebar.header("📁 Data Input")
    
    # Option to upload JSON file
    uploaded_file = st.sidebar.file_uploader("Upload JSON file", type=['json'])
    
    if uploaded_file is not None:
        # Load data from uploaded file
        data = load_json_data(uploaded_file)
        if data:
            display_document_info(data)
    else:
        st.info("Please upload a JSON file to view document information")

if __name__ == "__main__":
    main()
