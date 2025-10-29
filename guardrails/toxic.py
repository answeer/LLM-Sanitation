import hashlib
import pyspark.sql.functions as func
import mlflow
import time
from RAGaaS.logs.logging_setup   import LogUtil, LogType, LogLevel

def hash_text(text: str) -> str:
    """Hash text using SHA-256"""
    if isinstance(text, bytearray):
        text = text.decode(errors='replace')  # Convert bytearray to string
    return hashlib.sha256(text.encode()).hexdigest()


hash_text_udf = func.udf(hash_text)

def create(spark, bronze_table_name, run_id, source_folder,config):
    start_time = time.time()

    bronze_df = (
        spark.read.format("binaryFile")
        .option("recursiveFileLookup", "true")
        .option("pathGlobFilter", "*.{csv,xls,xlsx,parquet}")
        .load(source_folder)
        .withColumnRenamed("path", "input_file")
        .withColumn("datetime", func.current_timestamp())
        .withColumn("file_hash", hash_text_udf(func.col("content")))
    )
    # Check if table exists
    table_exists = spark.catalog.tableExists(bronze_table_name)
    print("table_exists   -- > ",table_exists)

    if table_exists:
        # Read existing file_hashes from the bronze table
        existing_hashes_df = spark.table(bronze_table_name).select("file_hash")
        # Filter out duplicates from the new DataFrame
        bronze_df_filtered = bronze_df.join(
            existing_hashes_df, on="file_hash", how="left_anti"
        )
    else:
        # If table does not exist, use all records
        bronze_df_filtered = bronze_df

    # Write only non-duplicate records
    bronze_df_filtered.write.format("delta").mode("append").option("overwrite", "false").saveAsTable(bronze_table_name)

    #bronze_df.write.format("delta").mode("append").saveAsTable(bronze_table_name)
    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 'Bronze table created successfully.')
    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("bronze_table_name", bronze_table_name)
        mlflow.log_metric("bronze_walltime_seconds", walltime)
    return bronze_df



import pandas as pd
from RAGaaS.data_pipeline.data_reader.read_files import read_file
import pyspark.sql.functions as func
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
import mlflow
import time


def create(spark, silver_table_name, run_id, bronze_df, config, delimiter="^"):
    start_time = time.time()
    appended_dfs = []
    bronze_rows = bronze_df.select("input_file", "file_hash").collect()
    for row in bronze_rows:
        file_path = row['input_file']
        file_hash = row['file_hash']
        try:
            print("??????? file_path  ", file_path)
            data = read_file(spark, file_path, delimiter)
            print("--------> data ", data)

            # df = spark.createDataFrame(pdf)
            data = data.withColumn("input_file", func.lit(file_path))
            data = data.withColumn("file_hash", func.lit(file_hash))
            appended_dfs.append(data)
        except Exception as e:
            LogUtil.log(LogType.ERROR, LogLevel.ERROR, f"Error reading {file_path}: {e}")

    if appended_dfs:
        silver_df = appended_dfs[0]
        for df in appended_dfs[1:]:
            silver_df = silver_df.unionByName(df)

        silver_df.write.format("delta").mode("append").option("overwrite", "false").saveAsTable(silver_table_name)

        walltime = round(time.time() - start_time, 2)
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver table created successfully.")

        with mlflow.start_run(run_id=run_id):
            mlflow.log_param("silver_table_name", silver_table_name)
            mlflow.log_metric("silver_walltime_seconds", walltime)
        return silver_df

    else:
        LogUtil.log(LogType.ERROR, LogLevel.ERROR, "No files processed for silver table.")
        return None



import pyspark.sql.functions as func
from pyspark.sql import Window
from RAGaaS.data_pipeline.chunking.chunking_methods import (
    recursive_character_split,
    fixed_size_split,
    paragraph_split,
    sentence_split,
    token_split,
    identity_chunk_udf,
)
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
import mlflow
import time

CHUNK_STRATEGY_MAP = {
    "recursive_character_split": recursive_character_split,
    "fixed_size_split": fixed_size_split,
    "sentence_split": sentence_split,
    "paragraph_split": paragraph_split,
    "token_split": token_split,
    "identity_chunk_udf": identity_chunk_udf,
}


def create(spark, gold_table_name, run_id, df_silver, config, chunk_col, chunk_flag, **kwargs):
    start_time = time.time()

    if chunk_flag:
        chunking_strategy = kwargs["chunking_strategy"]
        chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)
        if chunking_strategy in [
            "recursive_character_split",
            "fixed_size_split",
            "sentence_split",
            "paragraph_split",
            "token_split",
            "identity_chunk_udf"
        ]:
            args = {
                "col": func.col(chunk_col),
                "chunk_size": kwargs["max_tokens"],
                "chunk_overlap": kwargs["chunk_overlap"],
                "explode": True,
            }
            df_gold = (
                df_silver.withColumn("page_chunks", chunk_function(**args))
                .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
                .withColumn("datetime", func.current_timestamp())
                .drop("page_chunks")
            )
        else:
            raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")
    else:
        df_gold = df_silver

    df_gold.write.format("delta").option("mergeSchema", "true").mode(
        "append"
    ).saveAsTable(gold_table_name)

    spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold table created successfully.")

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_metric("gold_walltime_seconds", walltime)
    return df_gold
