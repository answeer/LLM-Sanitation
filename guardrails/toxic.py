from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
import json
import sys
from datetime import datetime

script_path = Path(sys.argv[0])
ROOT = str(Path(script_path).parent)
sys.path.insert(0, str(Path(script_path).parent.parent))

from prompt_engineering.prompt_builder import load_config, render_prompt
from utils.schema_loader import load_extraction_schema
from llm.llm_client import LLMClient
from utils.json_utils import coerce_to_json
from utils.read_pdf import read_pdf
from contract_extractor.logs.logging_setup import LogUtil, LogType, LogLevel
from databricks_langchain.chat_models import ChatDatabricks

def extract_single_file(contract_path: str | Path, schema_path: str | Path, config_path: str | Path) -> Dict[str, Any]:
    """
    Extract information from a single contract file
    """
    try:
        LogUtil.log(LogType.APPLICATION, LogLevel.INFO, f'Processing file: {contract_path}')
        
        # Load config and schema
        config = load_config(str(config_path))
        schema = load_extraction_schema(str(schema_path))

        # Read contract content
        contract_content = Path(contract_path).read_text(encoding="utf-8")
        
        if not contract_content.strip():
            LogUtil.log(LogType.APPLICATION, LogLevel.WARNING, f'Empty file: {contract_path}')
            return {"error": "Empty file", "filename": str(contract_path)}

        # Build prompt
        rendered = render_prompt(config.prompt_template, schema, contract_content)
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
        
        # Add metadata
        data["_metadata"] = {
            "source_file": str(contract_path),
            "model_used": config.model,
            "extraction_timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
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

def extract_from_folder(
    input_folder: str | Path,
    output_folder: str | Path,
    schema_path: str | Path,
    config_path: str | Path,
    file_extensions: List[str] = None
) -> Dict[str, Any]:
    """
    Extract information from all files in a folder and save results to another folder
    
    Args:
        input_folder: Path to folder containing contract files
        output_folder: Path to folder where results will be saved
        schema_path: Path to extraction schema file
        config_path: Path to config file
        file_extensions: List of file extensions to process (e.g., ['.txt', '.pdf'])
    
    Returns:
        Dictionary with processing summary
    """
    if file_extensions is None:
        file_extensions = ['.txt']  # Default to text files
    
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Validate inputs
    if not input_path.exists():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    if not Path(schema_path).exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    LogUtil.log(LogType.APPLICATION, LogLevel.INFO, f'Starting batch processing from {input_folder}')
    
    # Find all files with specified extensions
    contract_files = []
    for ext in file_extensions:
        contract_files.extend(input_path.glob(f"*{ext}"))
        contract_files.extend(input_path.glob(f"*{ext.upper()}"))
    
    # Remove duplicates and sort
    contract_files = sorted(set(contract_files))
    
    if not contract_files:
        LogUtil.log(LogType.APPLICATION, LogLevel.WARNING, f"No files found with extensions: {file_extensions}")
        return {"processed_files": 0, "successful": 0, "failed": 0}
    
    LogUtil.log(LogType.APPLICATION, LogLevel.INFO, f'Found {len(contract_files)} files to process')
    
    # Process each file
    results_summary = {
        "processed_files": 0,
        "successful": 0,
        "failed": 0,
        "files": []
    }
    
    for i, contract_file in enumerate(contract_files, 1):
        LogUtil.log(LogType.APPLICATION, LogLevel.INFO, f'Processing file {i}/{len(contract_files)}: {contract_file.name}')
        
        try:
            # Extract data from current file
            result = extract_single_file(contract_file, schema_path, config_path)
            
            # Determine output filename
            output_filename = f"{contract_file.stem}_extracted.txt"
            output_filepath = output_path / output_filename
            
            # Save result to file
            with open(output_filepath, 'w', encoding='utf-8') as f:
                if isinstance(result, dict):
                    json.dump(result, f, indent=2, ensure_ascii=False)
                else:
                    f.write(str(result))
            
            # Update summary
            results_summary["processed_files"] += 1
            file_result = {
                "input_file": str(contract_file),
                "output_file": str(output_filepath),
                "status": result.get("_metadata", {}).get("status", "unknown")
            }
            
            if file_result["status"] == "success":
                results_summary["successful"] += 1
            else:
                results_summary["failed"] += 1
                file_result["error"] = result.get("error", "Unknown error")
            
            results_summary["files"].append(file_result)
            
            LogUtil.log(LogType.APPLICATION, LogLevel.INFO, f'Successfully processed: {contract_file.name}')
            
        except Exception as e:
            LogUtil.log(LogType.APPLICATION, LogLevel.ERROR, f"Failed to process {contract_file.name}: {str(e)}")
            results_summary["processed_files"] += 1
            results_summary["failed"] += 1
            results_summary["files"].append({
                "input_file": str(contract_file),
                "status": "failed",
                "error": str(e)
            })
    
    # Save summary report
    summary_file = output_path / "processing_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    
    LogUtil.log(LogType.APPLICATION, LogLevel.INFO, 
               f'Batch processing completed. Success: {results_summary["successful"]}, '
               f'Failed: {results_summary["failed"]}, Total: {results_summary["processed_files"]}')
    
    return results_summary

def main():
    """
    Example usage and CLI interface
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract information from contract files in a folder')
    parser.add_argument('--input', required=True, help='Path to input folder containing contract files')
    parser.add_argument('--output', required=True, help='Path to output folder for results')
    parser.add_argument('--schema', required=True, help='Path to extraction schema file')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--extensions', nargs='+', default=['.txt'], 
                       help='File extensions to process (e.g., .txt .pdf)')
    
    args = parser.parse_args()
    
    try:
        results = extract_from_folder(
            input_folder=args.input,
            output_folder=args.output,
            schema_path=args.schema,
            config_path=args.config,
            file_extensions=args.extensions
        )
        
        print(f"Processing completed:")
        print(f"  Total files processed: {results['processed_files']}")
        print(f"  Successful: {results['successful']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Results saved to: {args.output}")
        
    except Exception as e:
        LogUtil.log(LogType.APPLICATION, LogLevel.ERROR, f"Batch processing failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)

# Keep the original function for backward compatibility
def extract(contract_path: str | Path, schema_path: str | Path, config_path: str | Path) -> Dict[str, Any]:
    """
    Original single-file extraction function for backward compatibility
    """
    return extract_single_file(contract_path, schema_path, config_path)

if __name__ == "__main__":
    main()
