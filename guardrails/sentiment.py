import streamlit as st
import pandas as pd

# 示例JSON数据
json_data = {
    "contacts": [
        {"type": "email", "value": "alice@example.com"},
        {"type": "phone", "value": "+123456789"}
    ]
}

# 将 JSON 数据转换为 DataFrame
df = pd.DataFrame(json_data["contacts"])

# 显示 DataFrame
edited_df = st.dataframe(df)

# 在用户编辑后可以进行处理
