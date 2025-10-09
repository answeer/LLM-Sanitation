def structured_chunk(
    col: Column,
    chunk_size: int = 0,
    chunk_overlap: int = 0,
    explode: bool = True,
) -> Column:
    """
    Splits markdown text into logical chunks based on headings.
    Returns chunks with unified content_chunk field.
    
    Args:
        col: Input column containing markdown text
        chunk_size: Not used in this implementation (for API consistency)
        chunk_overlap: Not used in this implementation (for API consistency) 
        explode: Whether to explode the array into multiple rows
    
    Returns:
        Column with chunked structure using content_chunk field
    """
    # Define the schema for the output chunks - unified format
    chunk_schema = ArrayType(
        StructType([
            StructField("content_chunk", StringType(), False)
        ])
    )

    @udf(chunk_schema)
    def _structured_chunk_udf(text: str) -> List[Dict[str, str]]:
        """
        UDF function that processes markdown text and chunks by headings
        Returns unified format with content_chunk field
        """
        if not text or not text.strip():
            return []
        
        lines = text.split('\n')
        chunks = []
        current_heading = None
        current_content = []

        # 匹配 markdown 标题 (# 标题, ## 标题 等)
        heading_pattern = re.compile(r'^(#{1,6})\s+(.*)')

        for line in lines:
            match = heading_pattern.match(line)
            if match:
                # 保存前一个块（如果有内容）
                if current_heading is not None or current_content:
                    chunk_content = "\n".join(current_content).strip()
                    if chunk_content:  # 只添加非空内容
                        # 统一格式：如果有标题，将标题和内容组合
                        if current_heading:
                            full_content = f"{current_heading}\n{chunk_content}"
                        else:
                            full_content = chunk_content
                        chunks.append({
                            "content_chunk": full_content
                        })
                
                # 开始新块
                current_heading = match.group(2).strip()
                current_content = []
            else:
                # 非标题行，添加到当前内容
                if line.strip():  # 只添加非空行
                    current_content.append(line)
        
        # 处理最后一个块
        if current_heading is not None or current_content:
            chunk_content = "\n".join(current_content).strip()
            if chunk_content:
                # 统一格式：如果有标题，将标题和内容组合
                if current_heading:
                    full_content = f"{current_heading}\n{chunk_content}"
                else:
                    full_content = chunk_content
                chunks.append({
                    "content_chunk": full_content
                })
        
        return chunks

    # 应用 UDF
    chunked_col = _structured_chunk_udf(col)
    
    # 根据 explode 参数决定返回格式
    if explode:
        return func.explode(chunked_col)
    else:
        return chunked_col
