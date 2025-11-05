import json
from typing import Dict, Any

def generate_contract_review_template(manifest_path: str = None, manifest_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    根据manifest文件生成合同审查的JSON模板
    
    Args:
        manifest_path: manifest文件的路径
        manifest_data: 直接传入的manifest数据字典
    
    Returns:
        生成的合同审查JSON模板
    """
    # 读取manifest数据
    if manifest_data is None:
        if manifest_path is None:
            raise ValueError("必须提供manifest_path或manifest_data参数")
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = manifest_data
    
    # 构建mandatory_key部分
    mandatory_key = {}
    for field in manifest["extraction_targets"]["mandatory_metadata"]:
        field_name = field["field_key"].replace('_', ' ').title()
        # 根据数据类型设置默认值
        if field["data_type"] == "string":
            mandatory_key[field_name] = ""
        elif field["data_type"] == "date":
            mandatory_key[field_name] = ""
        elif field["data_type"] == "currency":
            mandatory_key[field_name] = ""
        elif field["data_type"] == "boolean":
            mandatory_key[field_name] = False
        elif field["data_type"] == "list":
            mandatory_key[field_name] = []
    
    # 构建clause_analysis_results部分
    clause_analysis_results = {}
    for clause in manifest["extraction_targets"]["critical_clause_analysis"]:
        clause_key = clause["clause_key"]
        output_format = clause["check_details"]["extraction_output_format"]
        
        clause_result = {}
        for field, field_type in output_format.items():
            if "boolean" in field_type:
                clause_result[field] = False
            elif "number" in field_type or "scale" in field_type:
                clause_result[field] = 0
            elif "string" in field_type:
                clause_result[field] = ""
        
        clause_analysis_results[clause_key] = clause_result
    
    # 构建validation_summary_output部分
    validation_summary_output = {
        "status": "",
        "notes": ""
    }
    
    # 返回完整的模板
    return {
        "mandatory_key": mandatory_key,
        "clause_analysis_results": clause_analysis_results,
        "validation_summary_output": validation_summary_output
    }

# 使用示例
if __name__ == "__main__":
    # 方法1: 从文件读取
    # template = generate_contract_review_template("manifest.json")
    
    # 方法2: 直接使用提供的manifest数据
    manifest_data = {
        "manifest_name": "LLM_Contract_Review_Schema_V1",
        "contract_type": "Master Service Agreement (MSA)",
        "review_agent_task": "Extraction_Validation_Analysis",
        "extraction_targets": {
            "mandatory_metadata": [
                # ... 您的metadata数据
            ],
            "critical_clause_analysis": [
                # ... 您的clause分析数据
            ]
        },
        "validation_summary_output": {
            "status": "string (Pass/Fail/Conditional)",
            "notes": "string (Summary of findings and next steps)"
        }
    }
    
    template = generate_contract_review_template(manifest_data=manifest_data)
    
    # 打印结果
    print(json.dumps(template, indent=2, ensure_ascii=False))
