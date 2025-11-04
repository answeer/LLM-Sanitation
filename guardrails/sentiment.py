import time
import mlflow
from pyspark.sql import functions as F
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
from RAGaaS.data_pipeline.data_reader.read_files import read_file


def _parse_delta_append(spark, delta_append_df, delimiter="^"):
    """
    Parse delta append files one by one into structured DataFrames and add file_name/file_hash fields.
    
    Uses toLocalIterator for streaming iteration instead of collect to avoid memory issues.
    
    Args:
        spark: Spark session object
        delta_append_df: DataFrame containing delta append records with input_file and file_hash columns
        delimiter: Delimiter used for file parsing (default: "^")
    
    Returns:
        Union[DataFrame, None]: Combined DataFrame of all parsed files with additional metadata columns,
                              or None if no files were successfully parsed
    """
    parsed_dfs = []
    # Stream through delta append records using iterator to avoid memory issues
    for row in delta_append_df.select("input_file", "file_hash").toLocalIterator():
        file_path = row["input_file"]
        file_hash = row["file_hash"]
        try:
            # Read and parse file into structured DataFrame
            data = read_file(spark, file_path, delimiter)
            # Add metadata columns to the parsed data
            data = (
                data
                .withColumn("input_file", F.lit(file_path))
                .withColumn("file_hash", F.lit(file_hash))
                .withColumn("datetime", F.current_timestamp())
            )
            parsed_dfs.append(data)
        except Exception as e:
            LogUtil.log(LogType.ERROR, LogLevel.ERROR, f"Silver read error for {file_path}: {e}")

    # Return None if no files were successfully parsed
    if not parsed_dfs:
        return None

    # Combine all parsed DataFrames
    df = parsed_dfs[0]
    for d in parsed_dfs[1:]:
        df = df.unionByName(d, allowMissingColumns=True)
    return df


def create(spark, silver_table_name, run_id, delta_append_df, delta_delete_names_df, config, delimiter="^", mode="append"):
    """
    Execute silver layer processing based on delta changes.
    
    Processes delta changes from bronze layer:
    - Parses and appends delta_append records to silver table
    - Deletes records based on delta_delete file names
    
    Args:
        spark: Spark session object
        silver_table_name: Name of the target silver table
        run_id: MLflow run ID for tracking
        delta_append_df: DataFrame containing files to append
        delta_delete_names_df: DataFrame containing files to delete
        config: Configuration object
        delimiter: Delimiter used for file parsing (default: "^")
        mode: Operation mode (only used for logging, actual operations determined by delta changes)
    
    Returns:
        Union[DataFrame, None]: DataFrame that was appended to silver table, or None if no append occurred
    """
    start_time = time.time()
    table_exists = spark.catalog.tableExists(silver_table_name)

    # 1) Handle deletions (only non-empty in cold update scenarios)
    if delta_delete_names_df is not None and not delta_delete_names_df.limit(1).count() == 0 and table_exists:
        delta_delete_names_df.select("input_file").distinct().createOrReplaceTempView("_silver_to_delete_names")
        spark.sql(f"DELETE FROM {silver_table_name} WHERE input_file IN (SELECT input_file FROM _silver_to_delete_names)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver delete executed.")

    # 2) Handle appends
    silver_append_df = _parse_delta_append(spark, delta_append_df, delimiter)
    if silver_append_df is not None:
        (silver_append_df.write
            .format("delta")
            .mode("append")
            .option("mergeSchema", "true")
            .saveAsTable(silver_table_name))
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver append executed.")
    else:
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver append empty.")

    # Log metrics to MLflow
    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("silver_table_name", silver_table_name)
        mlflow.log_param("silver_mode", mode)
        mlflow.log_metric("silver_walltime_seconds", walltime)

    return silver_append_df


import time
import mlflow
import pyspark.sql.functions as func
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
from RAGaaS.data_pipeline.chunking.chunking_methods import (
    recursive_character_split,
    fixed_size_split,
    paragraph_split,
    sentence_split,
    token_split,
    identity_chunk_udf,
)

# Mapping of chunking strategy names to their corresponding functions
CHUNK_STRATEGY_MAP = {
    "recursive_character_split": recursive_character_split,
    "fixed_size_split": fixed_size_split,
    "sentence_split": sentence_split,
    "paragraph_split": paragraph_split,
    "token_split": token_split,
    "identity_chunk_udf": identity_chunk_udf,
}


def create(spark, gold_table_name, run_id, silver_delta_append_df, delta_delete_names_df, config, chunk_col, chunk_flag, mode="append",**kwargs):
    """
    Execute gold layer processing with chunking on silver delta changes.
    
    Processes incremental changes from silver layer:
    - Applies chunking strategies to silver_delta_append_df and writes to gold table
    - Deletes records based on delta_delete file names
    - Enables Change Data Feed for the gold table
    
    Args:
        spark: Spark session object
        gold_table_name: Name of the target gold table
        run_id: MLflow run ID for tracking
        silver_delta_append_df: DataFrame containing silver layer changes to process
        delta_delete_names_df: DataFrame containing files to delete
        config: Configuration object
        chunk_col: Column name to apply chunking on
        chunk_flag: Boolean indicating whether to apply chunking
        mode: Operation mode (default: "append")
        **kwargs: Additional keyword arguments for chunking configuration
    
    Returns:
        Union[DataFrame, None]: DataFrame that was appended to gold table, or None if no append occurred
    """
    start_time = time.time()
    table_exists = spark.catalog.tableExists(gold_table_name)

    # Get chunking strategy and corresponding function
    chunking_strategy = kwargs["chunking_strategy"]
    chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)

    # 1) Handle deletions (only non-empty in cold update scenarios)
    if delta_delete_names_df is not None and not delta_delete_names_df.limit(1).count() == 0 and table_exists:
        delta_delete_names_df.select("input_file").distinct().createOrReplaceTempView("_gold_to_delete_names")
        spark.sql(f"DELETE FROM {gold_table_name} WHERE input_file IN (SELECT input_file FROM _gold_to_delete_names)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold delete executed.")

    # 2) Handle appends with optional chunking
    if silver_delta_append_df is None or silver_delta_append_df.limit(1).count() == 0:
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append empty.")
        gold_append_df = None
    else:
        if chunk_flag:
            if chunking_strategy in [
                "recursive_character_split",
                "fixed_size_split",
                "sentence_split",
                "paragraph_split",
                "token_split",
                "identity_chunk_udf"
            ]:
                # Prepare arguments for chunking function
                args = {
                    "col": func.col(chunk_col),
                    "chunk_size": kwargs["max_tokens"],
                    "chunk_overlap": kwargs["chunk_overlap"],
                    "explode": True,
                }
                # Apply chunking strategy and process results
                gold_append_df = (
                    silver_delta_append_df.withColumn("page_chunks", chunk_function(**args))
                    .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
                    .withColumn("datetime", func.current_timestamp())
                    .drop("page_chunks")
                )
            else:
                raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")
        else:
            # Pass through without chunking
            gold_append_df = silver_delta_append_df
        
        # Write to gold table with schema evolution enabled
        gold_append_df.write.format("delta").option("mergeSchema", "true").mode("append").saveAsTable(gold_table_name)

        # Enable Change Data Feed for downstream processing
        spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append executed.")

    # Log metrics to MLflow
    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("gold_mode", mode)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_metric("gold_walltime_seconds", walltime)

    return gold_append_df
