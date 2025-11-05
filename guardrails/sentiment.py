import streamlit as st
import json

data = {
    "name": "Alice",
    "age": 30,
    "address": {
        "street": "123 Main St",
        "city": "New York"
    },
    "hobbies": ["Reading", "Hiking", "Traveling"]
}

# 将 JSON 数据转换为格式化的字符串
json_data = json.dumps(data, indent=4)

# 自定义 HTML 样式
st.markdown(f"<pre style='color: #4CAF50; font-family: Consolas, monospace;'>{json_data}</pre>", unsafe_allow_html=True)
