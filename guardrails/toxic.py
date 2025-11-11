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


def create(spark, gold_table_name, run_id, silver_delta_append_df, delta_delete_names_df, config, chunk_col, chunk_flag, mode="cold_update",**kwargs):
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

    if chunking_strategy in ["recursive_character_split", "fixed_size_split", "sentence_split", "paragraph_split", "token_split"]:
        args = {
            "col": func.col(chunk_col),
            "chunk_size": kwargs["max_tokens"],
            "chunk_overlap": kwargs["chunk_overlap"],
            "explode": True,
        }

    else:
        raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")

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
                # Apply chunking strategy and process results
            gold_append_df = (
                silver_delta_append_df.withColumn("page_chunks", chunk_function(**args))
                .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
                .withColumn("datetime", func.current_timestamp())
                .drop("page_chunks")
            )
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
