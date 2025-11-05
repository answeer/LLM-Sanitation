{
  "manifest_name": "LLM_Contract_Review_Schema_V1",
  "contract_type": "Master Service Agreement (MSA)",
  "review_agent_task": "Extraction_Validation_Analysis",
  "extraction_targets": {
    "mandatory_metadata": [
      {
        "field_key": "effective_date",
        "data_type": "date",
        "required": true,
        "description": "The date the contract becomes legally binding."
      },
      {
        "field_key": "expiration_date",
        "data_type": "date",
        "required": true,
        "description": "The date the contract term ends."
      },
      {
        "field_key": "governing_law",
        "data_type": "string",
        "required": true,
        "description": "The jurisdiction whose laws govern the contract."
      },
      {
        "field_key": "total_contract_value",
        "data_type": "currency",
        "required": false,
        "description": "Total monetary value of the contract."
      },
      {
        "field_key": "contract_id",
        "data_type": "string",
        "required": true,
        "description": "Unique identifier for the contract."
      },
      {
        "field_key": "contract_title",
        "data_type": "string",
        "required": true,
        "description": "Title of the contract."
      },
      {
        "field_key": "contract_reference",
        "data_type": "string",
        "required": true,
        "description": "Reference number or code for the contract."
      },
      {
        "field_key": "msa_linked_contracts",
        "data_type": "list",
        "required": false,
        "description": "List of contracts linked to the Master Service Agreement (MSA)."
      },
      {
        "field_key": "parties",
        "data_type": "list",
        "required": true,
        "description": "List of parties involved in the contract."
      },
      {
        "field_key": "parties_address",
        "data_type": "list",
        "required": true,
        "description": "Addresses of the parties involved in the contract."
      },
      {
        "field_key": "term_type",
        "data_type": "string",
        "required": false,
        "description": "Type of term for the contract (e.g., fixed, rolling)."
      },
      {
        "field_key": "goods_services_spend_category",
        "data_type": "string",
        "required": false,
        "description": "Category of goods or services covered by the contract."
      },
      {
        "field_key": "notice_period",
        "data_type": "string",
        "required": false,
        "description": "Notice period defined in the contract."
      },
      {
        "field_key": "signature_available",
        "data_type": "boolean",
        "required": false,
        "description": "Indicates whether signatures are available for the contract."
      },
      {
        "field_key": "signature_type",
        "data_type": "string",
        "required": false,
        "description": "Type of signature used (e.g., electronic, physical)."
      },
      {
        "field_key": "bank_signatory_name",
        "data_type": "string",
        "required": false,
        "description": "Name of the bank's signatory."
      },
      {
        "field_key": "bank_signatory_position",
        "data_type": "string",
        "required": false,
        "description": "Position of the bank's signatory."
      },
      {
        "field_key": "bank_signatory_date",
        "data_type": "string",
        "required": false,
        "description": "Date of the bank's signatory."
      },
      {
        "field_key": "supplier_signatory_name",
        "data_type": "string",
        "required": false,
        "description": "Name of the supplier's signatory."
      },
      {
        "field_key": "supplier_signatory_position",
        "data_type": "string",
        "required": false,
        "description": "Position of the supplier's signatory."
      },
      {
        "field_key": "supplier_signatory_date",
        "data_type": "string",
        "required": false,
        "description": "Date of the supplier's signatory."
      },
      {
        "field_key": "mandatory_clause_missing",
        "data_type": "boolean",
        "required": false,
        "description": "Indicates whether any mandatory clause is missing in the contract."
      },
      {
        "field_key": "contract_summary",
        "data_type": "string",
        "required": false,
        "description": "Summary of the contract."
      }
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
        "applies_to_contract_types": ["Master Service Agreement (MSA)", "Statement of Work (SOW)", "Managed Services"],
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


{ 
"madatory_key":{
  "contract id": "string",
  "Contract Title": "string",
  "Contract Reference": "string",
  "msa linked contracts": "list",
  "parties": "list",
  "parties Address": "list",
  "effective date": "string",
  "Expiration Date": "string",
  "Term Type": "string",
  "Goods/Services (Spend Category)": "string",
  "Total Contract Value": "string",
  "Governing Law": "string",
  "Notice Period": "string",
  "signature available":"boolean",
  "signature type": "string",
  "Bank Signatory Name": "string",
  "Bank Signatory Position": "string",
  "Bank Signatory Date": "string",
  "Supplier signatory Name": "string",
  "Supplier signatory position": "string",
  "Supplier Signatory Date": "string",
  "mandatory clause missing": "boolean",
  "Contract Summary": "string"
},
  "clause_analysis_results": {
    "force_majeure": {
      "is_present": "boolean",
      "coverage_rating": "number",
      "verbatim_coverage_summary": "string"
    },
    "termination_rights": {
      "convenience_present": "boolean",
      "notice_period_days": "number",
      "cause_breach_defined": "boolean"
    },
    "indemnification_liability_limits": {
      "is_mutual": "boolean",
      "limit_cap_extracted": "string",
      "carve_outs_acceptable": "boolean"
    },
    "sla_performance_metrics": {
      "is_present": "boolean",
      "has_remedies_or_credits": "boolean",
      "key_metrics_summary": "string"
    }
  },
  "validation_summary_output": {
    "status": "string",
    "notes": "string"
  }
}
