import pytest
from unittest.mock import MagicMock, patch


import src.RAGaaS.data_pipeline.chunking.chunking_methods as chunking_methods

@pytest.fixture
def mock_spark_col():
    # Mock PySpark Column and related methods
    mock_col = MagicMock()
    mock_col.__class__.__name__ = 'Column'
    mock_col.explode.return_value = mock_col
    mock_col.withColumn.return_value = mock_col
    mock_col.select.return_value = mock_col
    mock_col.collect.return_value = []
    return mock_col

@pytest.mark.parametrize("func_name", [
    "recursive_character_split",
    "fixed_size_split",
    "sentence_split",
    "paragraph_split",
    # "token_split"
])
def test_chunking_methods(func_name, mock_spark_col):
    func = getattr(chunking_methods, func_name)
    result = func(mock_spark_col, 100, 10, explode=True)
    
    # assert True



from typing import Iterator, Union, List, Dict
from pyspark.sql import Column
from pyspark.sql.types import ArrayType, StructType, StringType, StructField
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
import pyspark.sql.functions as func
import re
import tiktoken

def data_prep_udf(function, returnType):
    def _map_pandas_func(
        iterator: Iterator[Union[pd.Series, pd.DataFrame]],
    ) -> Iterator[pd.Series]:
        for x in iterator:
            if type(x) is pd.DataFrame:
                result = x.apply(lambda y: function(y), axis=1)
            else:
                result = x.map(lambda y: function(y))
            yield result

    return func.pandas_udf(f=_map_pandas_func, returnType=returnType)


def recursive_character_split(
    col: Column,
    chunk_size: int,
    chunk_overlap: int,
    explode=True,
):
    split_schema = ArrayType(
        StructType(
            [
                StructField("content_chunk", StringType(), False),
            ]
        )
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    def _split_char_recursive(content: str) -> List[Dict[str, Union[str, int]]]:
        chunks = text_splitter.split_text(content)
        return [{"content_chunk": doc} for doc in chunks]

    split_func = data_prep_udf(_split_char_recursive, split_schema)(col)
    if explode:
        return func.explode(split_func)
    return split_func


def fixed_size_split(
    col: Column,
    chunk_size: int,
    chunk_overlap: int,
    explode=True,
):
    split_schema = ArrayType(
        StructType([StructField("content_chunk", StringType(), False)])
    )

    def _split_fixed(content: str):
        if not content:
            return []
        return [
            {"content_chunk": content[i : i + chunk_size]}
            for i in range(0, len(content), chunk_size)
        ]

    split_func = data_prep_udf(_split_fixed, split_schema)(col)
    if explode:
        return func.explode(split_func)
    return split_func


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


def paragraph_split(
    col: Column,
    chunk_size: int,
    chunk_overlap: int,
    explode=True,
):
    split_schema = ArrayType(
        StructType([StructField("content_chunk", StringType(), False)])
    )

    def _split_paragraph(content: str):
        if not content:
            return []
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        return [{"content_chunk": p} for p in paragraphs]

    split_func = data_prep_udf(_split_paragraph, split_schema)(col)
    if explode:
        return func.explode(split_func)
    return split_func


def token_split(
    col: Column,
    chunk_size: int,
    chunk_overlap: int,
    explode=True,
):
    split_schema = ArrayType(
        StructType([StructField("content_chunk", StringType(), False)])
    )
    enc = tiktoken.get_encoding("cl100k_base")

    def _split_token(content: str):
        if not content:
            return []
        tokens = enc.encode(content)
        chunks = []
        for i in range(0, len(tokens), chunk_size - chunk_overlap):
            sub_tokens = tokens[i : i + chunk_size]
            chunks.append({"content_chunk": enc.decode(sub_tokens)})
        return chunks

    split_func = data_prep_udf(_split_token, split_schema)(col)
    if explode:
        return func.explode(split_func)
    return split_func
