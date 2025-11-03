import openai
import json
import re

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
                    "contextual_similarity_target": "Does the clause clearly excuse non-performance for events outside the parties' reasonable control, particularly those impacting global supply/service delivery?",
                    "extraction_output_format": {
                        "is_present": "boolean",
                        "coverage_rating": "scale 1-5 (1=poor, 5=excellent)",
                        "verbatim_coverage_summary": "string"
                    }
                }
            },
            {
                "clause_key": "termination_rights",
                "analysis_type": "contextual_similarity",
                "check_details": {
                    "verbatim_keywords": ["termination for convenience", "termination for cause"],
                    "contextual_similarity_target": "Does the contract allow for termination for convenience, and are the notice periods and penalties clearly defined for both convenience and breach (cause)?",
                    "extraction_output_format": {
                        "convenience_present": "boolean",
                        "notice_period_days": "number",
                        "cause_breach_defined": "boolean"
                    }
                }
            },
            {
                "clause_key": "indemnification_liability_limits",
                "analysis_type": "contextual_similarity",
                "check_details": {
                    "contextual_similarity_target": "Are the indemnification obligations mutual, and is the limitation of liability (LoL) clearly stated, with any exclusions (e.g., fraud, gross negligence) explicitly carved out? Is the LoL cap acceptable (e.g., TCV or 2x TCV)?",
                    "extraction_output_format": {
                        "is_mutual": "boolean",
                        "limit_cap_extracted": "string",
                        "carve_outs_acceptable": "boolean"
                    }
                }
            },
            {
                "clause_key": "sla_performance_metrics",
                "analysis_type": "presence_and_contextual",
                "check_details": {
                    "contextual_similarity_target": "Are specific performance metrics (SLAs) defined, and are remedies (e.g., service credits/penalties) for failure to meet those metrics clearly articulated?",
                    "extraction_output_format": {
                        "is_present": "boolean",
                        "has_remedies_or_credits": "boolean",
                        "key_metrics_summary": "string"
                    }
                }
            }
        ]
    },
    "validation_summary_output": {
        "status": "string (Pass/Fail/Conditional)",
        "notes": "string (Summary of findings and next steps)"
    }
}

# OpenAI API Key (ensure you replace with your key)
openai.api_key = "your-api-key-here"

# Helper function to extract metadata
def extract_metadata(contract_text, field_key):
    # For each field, use a regular expression or logic to extract the corresponding value
    if field_key == "effective_date":
        match = re.search(r"(effective date|effective\s*date)\s*[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})", contract_text, re.IGNORECASE)
        return match.group(2) if match else None
    elif field_key == "expiration_date":
        match = re.search(r"(expiration date|end\s*date)\s*[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})", contract_text, re.IGNORECASE)
        return match.group(2) if match else None
    elif field_key == "governing_law":
        match = re.search(r"governing law\s*[:\s]*([A-Za-z\s,]+)", contract_text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    elif field_key == "total_contract_value":
        match = re.search(r"total contract value\s*[:\s]*\$(\d[\d,]*)", contract_text, re.IGNORECASE)
        return match.group(1) if match else None
    return None

# Helper function to analyze critical clauses
def analyze_clause(contract_text, clause):
    result = {}
    check_details = clause['check_details']
    
    # Check for verbatim keywords
    found_keywords = []
    for keyword in check_details['verbatim_keywords']:
        if re.search(rf"\b{re.escape(keyword)}\b", contract_text, re.IGNORECASE):
            found_keywords.append(keyword)

    result['is_present'] = bool(found_keywords)

    # Perform contextual analysis based on the clause's description
    # For simplicity, this is a basic check of keywords and context
    if clause['clause_key'] == "force_majeure":
        if found_keywords:
            result['coverage_rating'] = 5  # Example, assuming perfect match
            result['verbatim_coverage_summary'] = "Covers 'act of god', 'war', 'terrorism', and 'epidemic'."
        else:
            result['coverage_rating'] = 1
            result['verbatim_coverage_summary'] = "No significant coverage of force majeure events."
    
    # Other clauses would follow similarly (e.g., termination_rights, indemnification, SLA metrics)
    # For brevity, we're assuming here that results are filled based on keywords

    return result

# Function to generate the prompt for OpenAI API
def generate_prompt(contract_text, manifest):
    prompt = f"""
    You are given the following contract text. Your task is to extract key contract metadata and perform analysis on critical clauses based on the following schema.
    
    Contract Text:
    {contract_text}
    
    The schema for extraction and analysis is as follows:
    - **Extract Mandatory Metadata**: Extract information for the fields: {', '.join([item['field_key'] for item in manifest['extraction_targets']['mandatory_metadata']])}
    
    - **Critical Clause Analysis**: Perform analysis for the following clauses:
    """
    
    for clause in manifest['extraction_targets']['critical_clause_analysis']:
        clause_key = clause['clause_key']
        check_details = clause['check_details']
        prompt += f"""
        1. **{clause_key.capitalize()}**:
           - **Analysis Type**: {clause['analysis_type']}
           - **Verbatim Keywords**: {', '.join(check_details.get('verbatim_keywords', []))}
           - **Contextual Check**: {check_details['contextual_similarity_target']}
           - **Expected Output**: {json.dumps(check_details['extraction_output_format'], indent=2)}
        """
    
    prompt += """
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
            },
            "termination_rights": {
                "convenience_present": true,
                "notice_period_days": 90,
                "cause_breach_defined": true
            },
            "indemnification_liability_limits": {
                "is_mutual": true,
                "limit_cap_extracted": "Limited to Total Contract Value (TCV)",
                "carve_outs_acceptable": true
            },
            "sla_performance_metrics": {
                "is_present": true,
                "has_remedies_or_credits": true,
                "key_metrics_summary": "Uptime SLA is 99.9%. Failure results in service credits capped at 10% of monthly fee."
            }
        },
        "validation_summary_output": {
            "status": "Conditional Pass",
            "notes": "All mandatory metadata extracted successfully. Governing Law ('Delaware') deviates from standard policy ('New York')."
        }
    }
    """
    return prompt

# Now generate the prompt for OpenAI API
prompt = generate_prompt(contract_text, manifest)

# Call OpenAI's API for text generation (simulating the task, replace with OpenAI API call)
# Assuming response is a JSON output from LLM
response = openai.Completion.create(
    model="text-davinci-003",  # Use the appropriate model
    prompt=prompt,
    max_tokens=1500
)

# Extract and display the JSON response (in reality, you should handle the response from OpenAI)
extracted_data = response.choices[0].text.strip()

# Print output
print(extracted_data)
