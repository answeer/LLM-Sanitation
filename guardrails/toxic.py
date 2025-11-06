import csv
import json
import os

def csv_row_to_json(csv_file_path, contract_name, output_json_path=None):
    """
    从CSV文件中读取指定合同名称的行，并转换回JSON格式
    
    参数:
    csv_file_path: CSV文件路径
    contract_name: 要查找的合同名称
    output_json_path: 输出的JSON文件路径（可选）
    
    返回:
    转换后的JSON数据字典
    """
    
    if not os.path.exists(csv_file_path):
        print(f"CSV文件不存在: {csv_file_path}")
        return None
    
    # 读取CSV文件
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # 查找指定合同名称的行
        target_row = None
        for row in reader:
            if row['Contract Name'] == contract_name:
                target_row = row
                break
        
        if not target_row:
            print(f"未找到合同名称 '{contract_name}' 在CSV文件中")
            return None
        
        # 构建JSON结构
        json_data = {}
        
        # 1. 构建mandatory_key部分
        mandatory_key = {
            "Effective Date": target_row.get("Effective Date", ""),
            "Expiration Date": target_row.get("Expiration Date", ""),
            "Governing Law": target_row.get("Governing Law", ""),
            "Total Contract Value": target_row.get("Total Contract Value", ""),
            "Contract Id": target_row.get("Contract Id", ""),
            "Contract Title": target_row.get("Contract Title", ""),
            "Contract Reference": target_row.get("Contract Reference", ""),
            "Msa Linked Contracts": [],
            "Parties": [],  # 注意：原CSV中没有这些字段，需要根据实际情况调整
            "Parties Address": [],  # 注意：原CSV中没有这些字段，需要根据实际情况调整
            "Term Type": target_row.get("Term Type", ""),
            "Goods Services Spend Category": target_row.get("Goods Services Spend Category", ""),
            "Notice Period": target_row.get("Notice Period", ""),
            "Signature Available": target_row.get("Signature Available", ""),
            "Signature Type": target_row.get("Signature Type", ""),
            "Bank Signatory Name": target_row.get("Bank Signatory Name", ""),
            "Bank Signatory Position": target_row.get("Bank Signatory Position", ""),
            "Bank Signatory Date": target_row.get("Bank Signatory Date", ""),
            "Supplier Signatory Name": target_row.get("Supplier Signatory Name", ""),
            "Supplier Signatory Position": target_row.get("Supplier Signatory Position", ""),
            "Supplier Signatory Date": target_row.get("Supplier Signatory Date", ""),
            "Mandatory Clause Missing": target_row.get("Mandatory Clause Missing", ""),
            "Contract Summary": target_row.get("Contract Summary", "")
        }
        
        # 处理布尔值和None值
        for key in ["Signature Available", "Mandatory Clause Missing"]:
            if mandatory_key[key] == "True":
                mandatory_key[key] = True
            elif mandatory_key[key] == "False":
                mandatory_key[key] = False
            elif mandatory_key[key] == "":
                mandatory_key[key] = None
        
        if mandatory_key["Total Contract Value"] == "":
            mandatory_key["Total Contract Value"] = None
        
        json_data["mandatory_key"] = mandatory_key
        
        # 2. 构建clause_analysis_results部分
        clause_analysis_results = {}
        
        # 获取所有列名
        all_columns = list(target_row.keys())
        
        # 找出所有条款相关的列
        clause_columns = {}
        for col in all_columns:
            if " - " in col:
                clause_name, field = col.split(" - ", 1)
                if clause_name not in clause_columns:
                    clause_columns[clause_name] = {}
                clause_columns[clause_name][field] = target_row[col]
        
        # 构建每个条款的数据
        for clause_name, fields in clause_columns.items():
            if any(fields.values()):  # 只有当至少有一个字段有值时
                clause_data = {
                    "Priority": fields.get("Priority", ""),
                    "Coverage_status": fields.get("Coverage Status", ""),
                    "Risk_level": fields.get("Risk Level", ""),
                    "Confidence": fields.get("Confidence", ""),
                    "Gap Analysis and Recommendations": fields.get("Gap Analysis and Recommendations", "")
                }
                clause_analysis_results[clause_name] = clause_data
        
        json_data["clause_analysis_results"] = clause_analysis_results
        
        # 3. 构建validation_summary_output部分
        validation_summary_output = {
            "status": target_row.get("Validation Status", ""),
            "notes": target_row.get("Validation Notes", "")
        }
        json_data["validation_summary_output"] = validation_summary_output
        
        # 4. 输出JSON文件（如果指定了输出路径）
        if output_json_path:
            with open(output_json_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, ensure_ascii=False, indent=2)
            print(f"JSON文件已保存到: {output_json_path}")
        
        return json_data

def main():
    """
    主函数，用于测试csv_row_to_json函数
    """
    csv_file = input("请输入CSV文件路径: ").strip()
    contract_name = input("请输入要查找的合同名称: ").strip()
    output_json = input("请输入输出的JSON文件路径（可选）: ").strip()
    
    if not output_json:
        output_json = None
    
    result = csv_row_to_json(csv_file, contract_name, output_json)
    
    if result:
        print("转换成功！")
        print("JSON数据结构:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("转换失败！")

if __name__ == "__main__":
    main()
