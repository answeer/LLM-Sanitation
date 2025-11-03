import openai
import json

# Sample contract text (this would normally be loaded from an actual document)
contract_text = """
This is a sample contract for IT Support services.
The effective date is 2025-04-01, and it expires on 2026-03-31. 
The governing law is New York, USA. The total contract value is $500,000.00.
The parties involved are Standard Chartered Bank Pvt Ltd and Capgemini.
The parties' addresses are 123 Tech Lane, City A and 456 Business Blvd, City B.
The notice period for termination is 90 days.
Signature type: Digital. Bank signatory: Mr. De Giorgi, Diego, CFO, Date: 2025-03-28.
Supplier signatory: Ms. Jane Smith, VP of Sales, Date: 2025-03-29.
"""

# Manifest schema (as provided by you)
manifest = {
    "manifest_name": "LLM_Contract_Review_Schema_V1",
    "contract_type": "Master Service Agreement (MSA)",
    "review_agent_task": "Extraction_Validation_Analysis",
    "extraction_targets": {
        "mandatory_metadata": [
            {"field_key": "effective_date", "data_type": "date", "required": True, "description": "The date the contract becomes legally binding."},
            {"field_key": "expiration_date", "data_type": "date", "required": True, "description": "The date the contract term ends."},
            {"field_key": "governing_law", "data_type": "string", "required": True, "description": "The jurisdiction whose laws govern the contract."},
            {"field_key": "total_contract_value", "data_type": "currency", "required": False, "description": "Total monetary value of the contract."}
        ],
        "critical_clause_analysis": [
            {
                "clause_key": "force_majeure",
                "analysis_type": "verbatim_and_contextual",
                "check_details": {
                    "verbatim_keywords": ["act of god", "natural disaster", "war", "terrorism", "epidemic", "pandemic", "quarantine"],
                    "contextual_similarity_target": "Does the clause clearly excuse non-performance for events outside the parties' reasonable control?",
                    "extraction_output_format": {
                        "is_present": "boolean",
                        "coverage_rating": "scale 1-5 (1=poor, 5=excellent)",
                        "verbatim_coverage_summary": "string"
                    }
                }
            },
            # Add other clauses here...
        ]
    },
    "validation_summary_output": {
        "status": "string (Pass/Fail/Conditional)",
        "notes": "string (Summary of findings and next steps)"
    }
}

# OpenAI API Key (ensure you replace with your key)
openai.api_key = "your-api-key-here"

# Define the prompt
def generate_prompt(contract_text, manifest):
    prompt = f"""
    You are given the following contract text. Your task is to extract key contract metadata and perform analysis on critical clauses based on the following schema.
    
    Contract Text:
    {contract_text}
    
    The schema for extraction and analysis is as follows:
    - **Extract Mandatory Metadata**: Extract information for the fields: {', '.join([item['field_key'] for item in manifest['extraction_targets']['mandatory_metadata']])}
    - **Critical Clause Analysis**: Perform analysis for the following clauses:
        1. **Force Majeure**: Check for the presence of the clause and analyze using the provided keywords and contextual check: {manifest['extraction_targets']['critical_clause_analysis'][0]['check_details']}
        
    Output the results in the following JSON format:
    {
        "contract id": "C12345",
        "Contract Title": "Master Service Agreement for IT Support",
        "Contract Reference": "MSA-IT-2025-001",
        "msa linked contracts": ["MSA001"],
        "parties": ["Standard Chartered Bank Pvt Ltd", "Capgemini"],
        "parties Address": ["123 Tech Lane, City A", "456 Business Blvd, City B"],
        "effective date": "2025-04-01",
        "Expiration Date": "2026-03-31",
        "Term Type": "Fixed",
        "Goods/Services (Spend Category)": "Information Technology Services",
        "Total Contract Value": "500000.00",
        "Governing Law": "New York, USA",
        "Notice Period": "90 Days",
        "signature available": true,
        "signature type": "Digital",
        "Bank Signatory Name": "Mr. De Giorgi, Diego",
        "Bank Signatory Position": "CFO",
        "Bank Signatory Date": "2025-03-28",
        "Supplier signatory Name": "Ms. Jane Smith",
        "Supplier signatory position": "VP of Sales",
        "Supplier Signatory Date": "2025-03-29",
        "mandatory clause missing": false,
        "duplicate flag": false,
        "anomaly flag": false,
        "Contract Summary": "One-year agreement for comprehensive IT support and maintenance services.",
        "validation summary": "All mandatory clauses present",
        "clause_analysis_results": {
            "force_majeure": {
                "is_present": true,
                "coverage_rating": 4,
                "verbatim_coverage_summary": "Covers 'act of god', 'war', and 'terrorism'. Epidemic/pandemic is explicitly listed."
            }
        },
        "validation_summary_output": {
            "status": "Conditional Pass",
            "notes": "All mandatory metadata extracted successfully. Governing Law ('Delaware') deviates from standard policy ('New York')."
        }
    }
    """
    return prompt

# Generate prompt
prompt = generate_prompt(contract_text, manifest)

# Call OpenAI's API for text generation
response = openai.Completion.create(
    model="text-davinci-003",  # Use the appropriate model here
    prompt=prompt,
    max_tokens=1500
)

# Extract the model's response
extracted_data = response.choices[0].text.strip()

# Convert the output to JSON format (assuming it's valid JSON)
try:
    contract_json = json.loads(extracted_data)
    print(json.dumps(contract_json, indent=4))
except json.JSONDecodeError:
    print("Error parsing the response into JSON. Response was:", extracted_data)
