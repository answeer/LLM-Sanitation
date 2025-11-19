import streamlit as st
import pandas as pd
import json

def display_document_info(data):
    """Display document information in a structured way"""
    
    st.set_page_config(page_title="Document Information Viewer", layout="wide")
    st.title("📄 Document Information Viewer")
    
    # Basic Document Information
    st.header("📋 Basic Information")
    
    # Display basic info in a linear fashion
    st.write(f"**Document ID:** {data.get('document_id', 'N/A')}")
    st.write(f"**Filename:** {data.get('filename', 'N/A')}")
    
    classification = data.get("classification", {})
    st.write(f"**Category:** {classification.get('category', 'N/A')}")
    st.write(f"**Document Type:** {classification.get('document_type', 'N/A')}")
    
    confidence = classification.get("confidence", 0)
    st.write(f"**Confidence:** {confidence*100:.1f}%" if confidence else "**Confidence:** N/A")
    
    # Related Documents Section
    st.header("🔗 Related Documents")
    related_docs = data.get("related_document_ids", [])
    
    if related_docs:
        # Create a clean dataframe for display
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
        # Create main dataframe for all key values
        key_data = []
        for item in key_values:
            key_data.append({
                "Key": item.get("key", "N/A"),
                "Value": item.get("value", "N/A"),
                "Normalized Value": item.get("value_normalized", "N/A"),
                "Confidence": f"{item.get('confidence', 0)*100:.1f}%" if item.get('confidence') else "N/A"
            })
        
        key_df = pd.DataFrame(key_data)
        
        # Add search functionality
        search_term = st.text_input("Search key values:", placeholder="Enter keyword to search...")
        
        items_per_page = st.selectbox("Items per page:", [10, 25, 50, 100], index=1)
        
        # Filter data if search term is provided
        display_df = key_df
        if search_term:
            mask = (key_df['Key'].str.contains(search_term, case=False, na=False) | 
                   key_df['Value'].str.contains(search_term, case=False, na=False) | 
                   key_df['Normalized Value'].str.contains(search_term, case=False, na=False))
            display_df = key_df[mask]
            
            if len(display_df) == 0:
                st.warning("No matching results found")
                return
        
        # Pagination
        total_items = len(display_df)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page_number = st.number_input("Page:", min_value=1, max_value=total_pages, value=1)
            start_idx = (page_number - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_df = display_df.iloc[start_idx:end_idx]
            
            st.write(f"Showing items {start_idx + 1}-{min(end_idx, total_items)} of {total_items}")
            st.dataframe(page_df, use_container_width=True, hide_index=True)
        else:
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
    else:
        st.warning("No key values found")
    
    # Statistics Section
    st.sidebar.header("📊 Statistics")
    
    if key_values:
        total_keys = len(key_values)
        high_confidence = len([item for item in key_values if item.get("confidence", 0) > 0.95])
        medium_confidence = len([item for item in key_values if 0.9 <= item.get("confidence", 0) <= 0.95])
        low_confidence = len([item for item in key_values if item.get("confidence", 0) < 0.9])
        
        st.sidebar.metric("Total Key Fields", total_keys)
        st.sidebar.metric("High Confidence Fields", high_confidence)
        st.sidebar.metric("Medium Confidence Fields", medium_confidence)
        st.sidebar.metric("Low Confidence Fields", low_confidence)
        
        # Confidence distribution chart
        if total_keys > 0:
            chart_data = pd.DataFrame({
                'Confidence Level': ['High (>95%)', 'Medium (90-95%)', 'Low (<90%)'],
                'Count': [high_confidence, medium_confidence, low_confidence]
            })
            st.sidebar.bar_chart(chart_data.set_index('Confidence Level'))

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
        
        # Example of expected format
        with st.expander("Expected JSON Format"):
            st.json("""
            {
                "document_id": "string",
                "filename": "string", 
                "classification": {
                    "category": "string",
                    "document_type": "string",
                    "confidence": number
                },
                "related_document_ids": [
                    {
                        "relation_type": "string",
                        "document_id_reference": "string", 
                        "confidence": number
                    }
                ],
                "key_values": [
                    {
                        "key": "string",
                        "value": "string",
                        "value_normalized": "string",
                        "confidence": number
                    }
                ]
            }
            """)

if __name__ == "__main__":
    main()
