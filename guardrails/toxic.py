import os

def get_all_pdf_files(root_folder):
    """
    获取文件夹及其子文件夹下所有的PDF文件
    """
    pdf_files = []
    
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(root, file)
                pdf_files.append(full_path)
    
    return pdf_files

# 使用示例
folder_path = "/path/to/your/folder"  # 替换为你的文件夹路径
pdf_files = get_all_pdf_files(folder_path)

# 打印结果
for pdf_file in pdf_files:
    print(pdf_file)

print(f"总共找到 {len(pdf_files)} 个PDF文件")
