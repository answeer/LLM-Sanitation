import hashlib
import pyspark.sql.functions as func
from RAGaaS.data_pipeline.medallian_tables.from_files.create_medallian_table import (
    create_bronze,
)
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

    create_bronze(spark, bronze_table_name, config)

    bronze_df = (
        spark.read.format("binaryFile")
        .option("recursiveFileLookup", "true")
        .option("pathGlobFilter", "*.pdf")
        .load(source_folder)
        .withColumnRenamed("path", "input_file")
        .withColumn("datetime", func.current_timestamp())
        .withColumn("file_hash", hash_text_udf(func.col("content")))
    )
    # Read existing file_hashes from the bronze table
    existing_hashes_df = spark.table(bronze_table_name).select("file_hash")

    # Filter out duplicates from the new DataFrame
    bronze_df_filtered = bronze_df.join(
        existing_hashes_df, on="file_hash", how="left_anti"
    )
    # Write only non-duplicate records
    bronze_df_filtered.write.format("delta").mode("append").saveAsTable(bronze_table_name)

    #bronze_df.write.format("delta").mode("append").saveAsTable(bronze_table_name)
    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 'Bronze table created successfully.')
    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("bronze_table_name", bronze_table_name)
        mlflow.log_metric("bronze_walltime_seconds", walltime)
    return bronze_df
