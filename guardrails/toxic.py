import json
import csv
import os
import glob
from pathlib import Path

def json_to_csv(json_folder_path, output_csv_path):
    """
    将文件夹中的JSON文件转换为CSV文件，每个文件对应一行
    
    参数:
    json_folder_path: 包含JSON文件的文件夹路径
    output_csv_path: 输出的CSV文件路径
    """
    
    # 获取所有JSON文件
    json_files = glob.glob(os.path.join(json_folder_path, "*.json"))
    
    if not json_files:
        print(f"在文件夹 {json_folder_path} 中没有找到JSON文件")
        return
    
    # 为了确定所有可能的条款名称，先扫描所有文件
    all_clause_names = set()
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            clause_analysis = data.get("clause_analysis_results", {})
            all_clause_names.update(clause_analysis.keys())
        except Exception as e:
            print(f"扫描文件 {json_file} 时出错: {str(e)}")
    
    # 准备CSV文件的列头
    headers = [
        "Contract Name",
        "Effective Date", "Expiration Date", "Governing Law", "Total Contract Value",
        "Contract Id", "Contract Title", "Contract Reference", "Term Type",
        "Goods Services Spend Category", "Notice Period", "Signature Available",
        "Signature Type", "Bank Signatory Name", "Bank Signatory Position", "Bank Signatory Date",
        "Supplier Signatory Name", "Supplier Signatory Position", "Supplier Signatory Date",
        "Mandatory Clause Missing", "Contract Summary",
        "Validation Status", "Validation Notes"
    ]
    
    # 为每个条款添加6个字段
    for clause_name in sorted(all_clause_names):
        headers.extend([
            f"{clause_name} - Priority",
            f"{clause_name} - Coverage Status", 
            f"{clause_name} - Risk Level",
            f"{clause_name} - Confidence",
            f"{clause_name} - Gap Analysis and Recommendations"
        ])
    
    # 打开CSV文件准备写入
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 写入表头
        writer.writerow(headers)
        
        # 处理每个JSON文件
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 获取合同名称（文件名去掉.json后缀）
                contract_name = Path(json_file).stem
                
                # 提取mandatory_key部分的基本信息
                mandatory = data.get("mandatory_key", {})
                row_data = [
                    contract_name,
                    mandatory.get("Effective Date", ""),
                    mandatory.get("Expiration Date", ""),
                    mandatory.get("Governing Law", ""),
                    mandatory.get("Total Contract Value", ""),
                    mandatory.get("Contract Id", ""),
                    mandatory.get("Contract Title", ""),
                    mandatory.get("Contract Reference", ""),
                    mandatory.get("Term Type", ""),
                    mandatory.get("Goods Services Spend Category", ""),
                    mandatory.get("Notice Period", ""),
                    mandatory.get("Signature Available", ""),
                    mandatory.get("Signature Type", ""),
                    mandatory.get("Bank Signatory Name", ""),
                    mandatory.get("Bank Signatory Position", ""),
                    mandatory.get("Bank Signatory Date", ""),
                    mandatory.get("Supplier Signatory Name", ""),
                    mandatory.get("Supplier Signatory Position", ""),
                    mandatory.get("Supplier Signatory Date", ""),
                    mandatory.get("Mandatory Clause Missing", ""),
                    mandatory.get("Contract Summary", "")
                ]
                
                # 提取validation_summary_output
                validation = data.get("validation_summary_output", {})
                row_data.extend([
                    validation.get("status", ""),
                    validation.get("notes", "")
                ])
                
                # 提取clause_analysis_results并添加到行中
                clause_analysis = data.get("clause_analysis_results", {})
                
                # 为每个可能的条款名称添加数据
                for clause_name in sorted(all_clause_names):
                    if clause_name in clause_analysis:
                        clause_data = clause_analysis[clause_name]
                        row_data.extend([
                            clause_data.get("Priority", ""),
                            clause_data.get("Coverage_status", ""),
                            clause_data.get("Risk_level", ""),
                            clause_data.get("Confidence", ""),
                            clause_data.get("Gap Analysis and Recommendations", "")
                        ])
                    else:
                        # 如果该合同没有这个条款，添加空值
                        row_data.extend(["", "", "", "", ""])
                
                # 写入完整的一行
                writer.writerow(row_data)
                print(f"成功处理文件: {json_file}")
                
            except Exception as e:
                print(f"处理文件 {json_file} 时出错: {str(e)}")
    
    print(f"转换完成！CSV文件已保存到: {output_csv_path}")
    print(f"总共处理了 {len(json_files)} 个文件")
    print(f"发现了 {len(all_clause_names)} 种不同的条款类型")

def main():
    # 配置路径
    json_folder = input("请输入包含JSON文件的文件夹路径: ").strip()
    
    if not json_folder:
        json_folder = "."  # 默认当前文件夹
    
    output_csv = input("请输入输出的CSV文件路径 (默认为 contracts_analysis.csv): ").strip()
    
    # 如果用户没有输入输出文件路径，使用默认值
    if not output_csv:
        output_csv = "contracts_analysis.csv"
    
    # 确保输出文件以.csv结尾
    if not output_csv.endswith('.csv'):
        output_csv += '.csv'
    
    # 执行转换
    json_to_csv(json_folder, output_csv)

if __name__ == "__main__":
    main()
