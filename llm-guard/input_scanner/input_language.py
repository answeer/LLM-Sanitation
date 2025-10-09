def sentence_split(
    col: Column,
    chunk_size: int,
    chunk_overlap: int,
    explode=True,
):
    split_schema = ArrayType(
        StructType([StructField("content_chunk", StringType(), False)])
    )

    def _split_sentence(content: str):
        if not content:
            return []
        sentences = re.split(r'(?<=[。！？.!?])', content)
        return [{"content_chunk": s.strip()} for s in sentences if s.strip()]

    split_func = data_prep_udf(_split_sentence, split_schema)(col)
    if explode:
        return func.explode(split_func)
    return split_func



def structured_chunk(text):
    """
    Splits text into logical chunks, grouping headings with their following paragraphs.
    Returns a list of dicts: {"heading": ..., "content": ...}
    """
    lines = text.split('\n')
    chunks = []
    current_heading = None
    current_content = []

    heading_pattern = re.compile(r'^(#{1,6})\s+(.*)')

    for line in lines:
        match = heading_pattern.match(line)
        if match:
            # Save previous chunk if exists
            if current_heading or current_content:
                chunks.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content).strip()
                })
            # Start new chunk
            current_heading = match.group(2)
            current_content = []
        else:
            current_content.append(line)
    # Add last chunk
    if current_heading or current_content:
        chunks.append({
            "heading": current_heading,
            "content": "\n".join(current_content).strip()
        })
    # Remove empty chunks
    return [chunk for chunk in chunks if chunk["content"]]
