import os
import nbformat

def convert_to_notebook(py_file, notebook_folder):
    with open(py_file, 'r') as f:
        py_code = f.read()

    nb = nbformat.v4.new_notebook()
    nb['cells'] = [nbformat.v4.new_code_cell(py_code)]

    notebook_name = os.path.splitext(os.path.basename(py_file))[0] + ".ipynb"
    notebook_path = os.path.join(notebook_folder, notebook_name)

    with open(notebook_path, 'w') as f:
        nbformat.write(nb, f)

def batch_convert_to_notebook(python_files_folder, notebook_folder):
    # 创建存放Jupyter Notebook的目录
    if not os.path.exists(notebook_folder):
        os.makedirs(notebook_folder)

    # 遍历文件夹中的所有Python文件
    for file_name in os.listdir(python_files_folder):
        if file_name.endswith(".py"):
            py_file = os.path.join(python_files_folder, file_name)
            convert_to_notebook(py_file, notebook_folder)

# 指定存放Python文件的文件夹路径
python_files_folder = "guardrails"

# 指定存放Jupyter Notebook的文件夹路径
notebook_folder = "notebook/guardrails"

# 批量转换Python文件为Jupyter Notebook
batch_convert_to_notebook(python_files_folder, notebook_folder)
