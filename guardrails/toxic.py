import pyspark.sql.functions as func
from pyspark.sql import Window
from RAGaaS.data_pipeline.chunking.chunking_methods import recursive_character_split, fixed_size_split, paragraph_split, sentence_split, token_split
from RAGaaS.data_pipeline.medallian_tables.from_files.create_medallian_table import (
    create_gold
)
from RAGaaS.logs.logging_setup   import LogUtil, LogType, LogLevel
import mlflow
import time

CHUNK_STRATEGY_MAP = {
    "recursive_character_split": recursive_character_split,
    "fixed_size_split": fixed_size_split,
    "sentence_split": sentence_split,
    "paragraph_split": paragraph_split,
    "token_split": token_split,
}

def _prepare_chunking_column(df, chunk_col, merged_column_name="_merged_content"):
    """
    Prepare the column for chunking. If chunk_col is a list, merge the columns.
    
    Args:
        df: Input DataFrame
        chunk_col: Column name (str) or list of column names to merge
        merged_column_name: Name for the merged column when chunk_col is a list
    
    Returns:
        Tuple: (processed_df, actual_chunk_column_name)
    """
    if isinstance(chunk_col, list):
        # Merge multiple columns into one
        if len(chunk_col) == 0:
            raise ValueError("chunk_col list cannot be empty")
        
        # Handle case where some columns might be null - use coalesce and concat_ws
        from pyspark.sql.functions import concat_ws, coalesce, lit
        
        # Start with the first column
        merged_expr = coalesce(func.col(chunk_col[0]), lit(""))
        
        # Add remaining columns with separator
        for col_name in chunk_col[1:]:
            merged_expr = concat_ws(" ", merged_expr, coalesce(func.col(col_name), lit("")))
        
        df_with_merged = df.withColumn(merged_column_name, merged_expr)
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 
                   f"Merged columns {chunk_col} into '{merged_column_name}' for chunking")
        return df_with_merged, merged_column_name
    
    elif isinstance(chunk_col, str):
        # Single column case
        return df, chunk_col
    
    else:
        raise ValueError(f"chunk_col must be str or list, got {type(chunk_col)}")


def create(spark, gold_table_name, run_id, silver_delta_append_df, config, mode="append", delta_delete_names_df=None,**kwargs):
    start_time = time.time()
    create_gold(spark, gold_table_name, config)

    chunking_strategy = kwargs['chunking_strategy']
    chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)
    
    # Get chunk_col from kwargs, default to "page_content" for backward compatibility
    chunk_col = kwargs.get('chunk_col', 'page_content')

    if chunking_strategy in ["recursive_character_split", "fixed_size_split", "sentence_split", "paragraph_split", "token_split"]:
        # Prepare base args without column first
        args = {
            "chunk_size": kwargs["max_tokens"],
            "chunk_overlap": kwargs["chunk_overlap"],
            "explode": True,
        }
    else:
        raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")

    table_exists = spark.catalog.tableExists(gold_table_name)

    if delta_delete_names_df is not None and not delta_delete_names_df.limit(1).count() == 0 and table_exists:
        delta_delete_names_df.select("file_name").distinct().createOrReplaceTempView("_gold_to_delete_names")
        spark.sql(f"""
            DELETE FROM {gold_table_name}
            WHERE file_name IN (SELECT file_name FROM _gold_to_delete_names)
        """)
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold delete executed.")

    if silver_delta_append_df.limit(1).count() == 0:
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append empty.")
        gold_out = None
    else:
        # Prepare the DataFrame for chunking
        processed_df, actual_chunk_col = _prepare_chunking_column(silver_delta_append_df, chunk_col)
        
        # Add the actual column to args for chunking
        args["col"] = func.col(actual_chunk_col)
        
        df_to_write = (
            processed_df.withColumn("page_chunks", chunk_function(**args))
            .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
            .withColumn("datetime", func.current_timestamp())
            .drop("page_chunks")
        )
        
        # If we created a merged column, drop it from the final output
        if isinstance(chunk_col, list) and "_merged_content" in [col.name for col in df_to_write.schema]:
            df_to_write = df_to_write.drop("_merged_content")
        
        df_to_write.write.format("delta").option("mergeSchema", "true").mode("append").saveAsTable(gold_table_name)

        spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append executed.")
        gold_out = df_to_write

    walltime = round(time.time() - start_time, 2)
    chunk_col_info = str(chunk_col) if isinstance(chunk_col, list) else chunk_col
    
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("gold_mode", mode)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_param("chunk_column", chunk_col_info)
        mlflow.log_metric("gold_walltime_seconds", walltime)

    return gold_out
