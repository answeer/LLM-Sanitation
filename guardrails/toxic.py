import os
import zipfile
import py7zr
import json
import pandas as pd
import base64
from PyPDF2 import PdfReader
from docx import Document
import requests
from pathlib import Path

# LLM API URL (use your actual LLM API endpoint)
LLM_API_URL = 'https://your-llm-api-endpoint.com/extract-metadata'

# Function to convert file content to Base64
def file_to_base64(file_path):
    try:
        with open(file_path, "rb") as file:
            # Read the file content as bytes and encode it to Base64
            encoded_content = base64.b64encode(file.read()).decode('utf-8')
        return encoded_content
    except Exception as e:
        print(f"Error converting file {file_path} to Base64: {e}")
        return None

# Read the contract content from PDF, DOCX, and image files
def read_file_content(file_path):
    content = ""
    if file_path.endswith('.pdf'):
        content = file_to_base64(file_path)
    elif file_path.endswith('.docx'):
        content = file_to_base64(file_path)
    elif file_path.lower().endswith(('png', 'jpg', 'jpeg')):
        content = file_to_base64(file_path)
    return content

# Call the LLM API to extract metadata from the contract
def extract_metadata_via_api(file_path, encoded_content):
    try:
        # Construct the prompt to ask LLM to extract metadata from contract text
        prompt = f"""
        Please extract all metadata from the following contract content (in Base64) and return it as a JSON object with key-value pairs.

        Contract content (Base64 encoded):
        {encoded_content}

        Return JSON format:
        {{
            "key1": "value1",
            "key2": "value2",
            ...
        }}
        """
        
        # Call LLM API
        response = requests.post(LLM_API_URL, json={"prompt": prompt})
        
        if response.status_code == 200:
            return response.json()  # Return the extracted metadata as JSON
        else:
            print(f"API error for file {file_path}: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error calling LLM API for {file_path}: {e}")
        return {}

# Process archive files (ZIP/7z)
def extract_files_from_archive(archive_path, extract_to):
    try:
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif archive_path.endswith('.7z'):
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                z.extractall(path=extract_to)
        else:
            return []
        extracted_files = [os.path.join(extract_to, f) for f in os.listdir(extract_to)]
        return extracted_files
    except Exception as e:
        print(f"Error extracting {archive_path}: {e}")
        return []

# Recursively process files to extract metadata
def process_file(file_path, output_json, output_csv, processed_files, extract_folder='extracted_files'):
    if file_path in processed_files:
        return
    file_type = get_file_type(file_path)

    metadata = {}
    if file_type == 'pdf' or file_type == 'docx' or file_type == 'image':
        # Read file content and convert to Base64
        encoded_content = read_file_content(file_path)
        if encoded_content:
            # Use LLM to extract contract metadata
            metadata = extract_metadata_via_api(file_path, encoded_content)
    elif file_type == 'archive':
        # Recursively process files inside archives (ZIP/7z)
        extract_folder_path = os.path.join(extract_folder, Path(file_path).stem)
        os.makedirs(extract_folder_path, exist_ok=True)
        extracted_files = extract_files_from_archive(file_path, extract_folder_path)
        for extracted_file in extracted_files:
            process_file(extracted_file, output_json, output_csv, processed_files, extract_folder)
        return

    # If metadata is successfully extracted
    if metadata:
        metadata['file_path'] = file_path
        output_json.append(metadata)

    # Update CSV records
    processed_files.append(file_path)
    output_csv.append({'file_path': file_path, 'status': 'processed'})

# Read processed files list from CSV
def load_processed_files(csv_file):
    processed_files = set()
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        processed_files = set(df['file_path'].tolist())
    return processed_files

# Scan folder and return all file paths
def get_all_files_in_directory(directory_path):
    all_files = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files

# Main function
def main(input_folder, output_json_file='output_metadata.json', output_csv_file='output_metadata.csv', extract_folder='extracted_files'):
    # Load already processed files from CSV
    processed_files = load_processed_files(output_csv_file)
    output_json = []
    output_csv = []

    # Get all files in the input folder
    input_files = get_all_files_in_directory(input_folder)

    # Process each file
    for file in input_files:
        if file not in processed_files:
            process_file(file, output_json, output_csv, processed_files, extract_folder)
    
    # Save JSON result
    with open(output_json_file, 'w', encoding='utf-8') as json_file:
        json.dump(output_json, json_file, ensure_ascii=False, indent=4)

    # Save CSV result
    df = pd.DataFrame(output_csv)
    df.to_csv(output_csv_file, index=False, encoding='utf-8')

# Execute the script
if __name__ == "__main__":
    input_folder = input("Please enter the folder path to process: ")  # Input folder path
    main(input_folder)
