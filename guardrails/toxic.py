from pypdf import PdfReader
import os
from pathlib import Path

def read_pdf(pdf_path):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from all pages, or None if error occurs
    """
    try:
        with open(pdf_path, "rb") as file:
            reader = PdfReader(file)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                print(f"Warning: PDF '{os.path.basename(pdf_path)}' is encrypted and cannot be read")
                return None
            
            text = ""
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num} ---\n{page_text}\n"
            
            return text
            
    except FileNotFoundError:
        print(f"Error: File not found at {pdf_path}")
        return None
    except Exception as e:
        print(f"Error reading PDF '{os.path.basename(pdf_path)}': {str(e)}")
        return None

def batch_pdf_to_txt(input_folder, output_folder=None):
    """
    Convert all PDF files in input folder to TXT files.
    
    Args:
        input_folder (str): Path to folder containing PDF files
        output_folder (str): Path to output folder (optional, defaults to input_folder)
    """
    input_path = Path(input_folder)
    
    # Set output folder
    if output_folder is None:
        output_path = input_path
    else:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
    
    # Check if input folder exists
    if not input_path.exists():
        print(f"Error: Input folder '{input_folder}' does not exist")
        return
    
    # Find all PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in '{input_folder}'")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process...")
    
    success_count = 0
    failed_count = 0
    
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        
        # Extract text from PDF
        content = read_pdf(pdf_file)
        
        if content is not None:
            # Create output filename (same name but with .txt extension)
            output_filename = output_path / f"{pdf_file.stem}.txt"
            
            try:
                # Save to text file
                with open(output_filename, 'w', encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✓ Successfully converted to: {output_filename.name}")
                success_count += 1
                
            except Exception as e:
                print(f"  ✗ Error saving {output_filename.name}: {str(e)}")
                failed_count += 1
        else:
            failed_count += 1
    
    # Print summary
    print(f"\n=== Conversion Summary ===")
    print(f"Total PDF files processed: {len(pdf_files)}")
    print(f"Successfully converted: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Output folder: {output_path}")

def main():
    # 配置路径
    input_folder = r"C:\Users\1657820\Documents\Downloads\1\20251021"  # 输入文件夹路径
    output_folder = None  # 设置为None则输出到同一文件夹，或指定其他文件夹路径
    
    # 执行批量转换
    batch_pdf_to_txt(input_folder, output_folder)

if __name__ == "__main__":
    main()
