Manifest Example 
 
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
 
output JSON example 
 
{
  "contract id": "C12345",
  "Contract Title": "Master Service Agreement for IT Support",
  "Contract Reference": "MSA-IT-2025-001",
  "msa linked contracts": ["MSA001"],
  "parties": ["Standard Chartered Bank Pvt Ltd", "Capgemini  "],
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
  "Bank Signatory Name": "Mr. De Giorgi, Diego ",
  "Bank Signatory Position": "CFO",
  "Bank Signatory Date": "2025-03-28",
  "Supplier signatory Name": "Ms. Jane Smith",
  "Supplier signatory position": "VP of Sales",
  "Supplier Signatory Date": "2025-03-29",
  "mandatory clause missing": false,
  "duplicate flag": false,
  "anomaly flag": false,
  "Contract Summary": "One-year agreement for comprehensive IT support and maintenance services.",
  "validation summary": "All mandatory clauses present"
}
"clause_analysis_results": {
    "force_majeure": {
      "is_present": true,
      "coverage_rating": 4,
      "verbatim_coverage_summary": "Covers 'act of god', 'war', and 'terrorism'. **Epidemic/pandemic** is explicitly listed, providing strong coverage."
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
      "key_metrics_summary": "Uptime SLA is 99.9%. Failure results in **service credits** capped at 10% of monthly fee."
    }
  },
  "validation_summary_output": {
    "status": "Conditional Pass",
    "notes": "All mandatory metadata extracted successfully. Critical clauses are generally favorable. **Condition**: Governing Law ('Delaware') deviates from standard policy ('New York'); requires manual legal sign-off for exception. SLA/Remedies are clearly defined and acceptable."
  }
}
 
