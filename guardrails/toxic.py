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

def create(spark, gold_table_name, run_id, silver_delta_append_df, config, mode="append", delta_delete_names_df=None,**kwargs):
    start_time = time.time()
    create_gold(spark, gold_table_name, config)

    chunking_strategy = kwargs['chunking_strategy']
    chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)

    if chunking_strategy in ["recursive_character_split", "fixed_size_split", "sentence_split", "paragraph_split", "token_split"]:
        args = {
            "col": func.col("page_content"),
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
        df_to_write =(
        silver_delta_append_df.withColumn("page_chunks", chunk_function(**args))
        .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
        .withColumn("datetime", func.current_timestamp())
        .drop("page_chunks")
    )
        
        df_to_write.write.format("delta").option("mergeSchema", "true").mode("append").saveAsTable(gold_table_name)

        spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append executed.")
        gold_out = df_to_write

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("gold_mode", mode)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_metric("gold_walltime_seconds", walltime)

    return gold_out
