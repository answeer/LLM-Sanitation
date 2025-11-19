import csv
from pathlib import Path

def append_json_row_fixed(path, row, fieldnames, encoding="utf-8-sig"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    need_header = (not p.exists()) or (p.stat().st_size == 0)

    with p.open("a", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if need_header:
            writer.writeheader()
        writer.writerow(row)

# 用法
fieldnames = ["name", "age", "city"]  # 预定义列
append_json_row_fixed("people.csv", {"name": "Alice", "age": 30, "city": "Shanghai"}, fieldnames)
