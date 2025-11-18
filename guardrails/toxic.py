import os
import zipfile
import py7zr
import json
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import io
import requests
from pathlib import Path

# 假设 LLM API 的 URL
LLM_API_URL = 'https://your-llm-api-endpoint.com/extract-metadata'

# 检查文件类型
def get_file_type(file_path):
    if file_path.endswith('.pdf'):
        return 'pdf'
    elif file_path.endswith('.docx'):
        return 'docx'
    elif file_path.endswith(('.zip', '.7z')):
        return 'archive'
    elif file_path.lower().endswith(('png', 'jpg', 'jpeg')):
        return 'image'
    return 'unknown'

# 提取 PDF 元数据
def extract_pdf_metadata(file_path):
    try:
        reader = PdfReader(file_path)
        metadata = reader.metadata
        return metadata
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return {}

# 提取 DOCX 元数据
def extract_docx_metadata(file_path):
    try:
        doc = Document(file_path)
        core_props = doc.core_properties
        metadata = {
            'title': core_props.title,
            'author': core_props.author,
            'subject': core_props.subject,
            'keywords': core_props.keywords
        }
        return metadata
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
        return {}

# 提取图片元数据
def extract_image_metadata(file_path):
    try:
        with Image.open(file_path) as img:
            metadata = img.info  # 获取图片元数据
        return metadata
    except Exception as e:
        print(f"Error reading image {file_path}: {e}")
        return {}

# 调用 LLM API 提取元数据
def extract_metadata_via_api(file_path):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(LLM_API_URL, files=files)
            if response.status_code == 200:
                return response.json()  # 返回API提取的元数据
            else:
                print(f"API error for file {file_path}: {response.status_code}")
                return {}
    except Exception as e:
        print(f"Error calling LLM API for {file_path}: {e}")
        return {}

# 处理压缩包文件（ZIP/7z）
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

# 递归提取元数据
def process_file(file_path, output_json, output_csv, processed_files, extract_folder='extracted_files'):
    if file_path in processed_files:
        return
    file_type = get_file_type(file_path)

    metadata = {}
    if file_type == 'pdf':
        metadata = extract_pdf_metadata(file_path)
    elif file_type == 'docx':
        metadata = extract_docx_metadata(file_path)
    elif file_type == 'image':
        metadata = extract_image_metadata(file_path)
    elif file_type == 'archive':
        # 对压缩包内的文件递归处理
        extract_folder_path = os.path.join(extract_folder, Path(file_path).stem)
        os.makedirs(extract_folder_path, exist_ok=True)
        extracted_files = extract_files_from_archive(file_path, extract_folder_path)
        for extracted_file in extracted_files:
            process_file(extracted_file, output_json, output_csv, processed_files, extract_folder)
        return
    elif file_type == 'unknown':
        metadata = extract_metadata_via_api(file_path)
    
    # 保存元数据到JSON文件
    if metadata:
        metadata['file_path'] = file_path
        output_json.append(metadata)

    # 更新CSV记录文件
    processed_files.append(file_path)
    output_csv.append({'file_path': file_path, 'status': 'processed'})

# 主函数
def main(input_files, output_json_file='output_metadata.json', output_csv_file='output_metadata.csv', extract_folder='extracted_files'):
    processed_files = []
    output_json = []
    output_csv = []

    # 处理每个文件
    for file in input_files:
        process_file(file, output_json, output_csv, processed_files, extract_folder)
    
    # 保存JSON结果
    with open(output_json_file, 'w', encoding='utf-8') as json_file:
        json.dump(output_json, json_file, ensure_ascii=False, indent=4)

    # 保存CSV结果
    df = pd.DataFrame(output_csv)
    df.to_csv(output_csv_file, index=False, encoding='utf-8')

# 执行示例
if __name__ == "__main__":
    input_files = ['file1.pdf', 'file2.docx', 'file3.zip']  # 输入文件列表
    main(input_files)
