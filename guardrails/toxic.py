import hashlib
import pyspark.sql.functions as func
import mlflow
import time
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel


def hash_text(text: str) -> str:
    """Hash text using SHA-256"""
    if isinstance(text, bytearray):
        text = text.decode(errors="replace")
    return hashlib.sha256(text.encode()).hexdigest()


hash_text_udf = func.udf(hash_text)


def create(
    spark,
    bronze_table_name,
    run_id,
    source_folder,
    config,
    duplication_type="append_mode",  # append_mode or cold_update
):
    start_time = time.time()

    # Step 1: 读取文件并计算哈希
    bronze_df = (
        spark.read.format("binaryFile")
        .option("recursiveFileLookup", "true")
        .option("pathGlobFilter", "*.{csv,xls,xlsx,parquet}")
        .load(source_folder)
        .withColumnRenamed("path", "input_file")
        .withColumn("datetime", func.current_timestamp())
        .withColumn("file_hash", hash_text_udf(func.col("content")))
    )

    table_exists = spark.catalog.tableExists(bronze_table_name)
    delta_append_df, delta_delete_df = None, None

    if table_exists:
        existing_df = spark.table(bronze_table_name).select("input_file", "file_hash")

        # 找出 delta append（新文件）
        delta_append_df = bronze_df.join(existing_df, on="file_hash", how="left_anti")

        # 找出 delta delete（同名但hash不同）
        delta_delete_df = bronze_df.join(
            existing_df, on=["input_file"], how="inner"
        ).filter(bronze_df.file_hash != existing_df.file_hash)

        if duplication_type == "append_mode":
            # 仅追加新文件
            final_df = delta_append_df

        elif duplication_type == "cold_update":
            # 删除重复文件记录
            delete_files = [r["input_file"] for r in delta_delete_df.collect()]
            for f in delete_files:
                spark.sql(
                    f"DELETE FROM {bronze_table_name} WHERE input_file = '{f}'"
                )
            final_df = delta_append_df

        else:
            raise ValueError(f"Unknown duplication_type: {duplication_type}")

    else:
        # 初次创建表
        final_df = bronze_df
        delta_append_df = bronze_df
        delta_delete_df = spark.createDataFrame([], bronze_df.schema)

    # Step 2: 写入表
    if final_df is not None and final_df.count() > 0:
        final_df.write.format("delta").mode("append").saveAsTable(bronze_table_name)

    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Bronze table processed successfully.")
    walltime = round(time.time() - start_time, 2)

    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("bronze_table_name", bronze_table_name)
        mlflow.log_param("duplication_type", duplication_type)
        mlflow.log_metric("bronze_walltime_seconds", walltime)

    return {
        "bronze_df": bronze_df,
        "delta_append": delta_append_df,
        "delta_delete": delta_delete_df,
    }






import pyspark.sql.functions as func
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
import mlflow
import time
from RAGaaS.data_pipeline.data_reader.read_files import read_file


def create(
    spark,
    silver_table_name,
    run_id,
    delta_append_df,
    delta_delete_df,
    config,
    duplication_type="append_mode",
    delimiter="^",
):
    start_time = time.time()
    appended_dfs = []

    # Step 1: cold_update 模式需要删除旧数据
    if duplication_type == "cold_update" and delta_delete_df is not None:
        delete_files = [r["input_file"] for r in delta_delete_df.collect()]
        for f in delete_files:
            spark.sql(f"DELETE FROM {silver_table_name} WHERE input_file = '{f}'")

    # Step 2: 读取 delta append 文件
    if delta_append_df is not None and delta_append_df.count() > 0:
        bronze_rows = delta_append_df.select("input_file", "file_hash").collect()
        for row in bronze_rows:
            file_path = row["input_file"]
            file_hash = row["file_hash"]
            try:
                data = read_file(spark, file_path, delimiter)
                data = data.withColumn("input_file", func.lit(file_path))
                data = data.withColumn("file_hash", func.lit(file_hash))
                appended_dfs.append(data)
            except Exception as e:
                LogUtil.log(
                    LogType.ERROR,
                    LogLevel.ERROR,
                    f"Error reading {file_path}: {e}",
                )

    if appended_dfs:
        silver_df = appended_dfs[0]
        for df in appended_dfs[1:]:
            silver_df = silver_df.unionByName(df)

        silver_df.write.format("delta").mode("append").saveAsTable(silver_table_name)

        walltime = round(time.time() - start_time, 2)
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver table updated successfully.")

        with mlflow.start_run(run_id=run_id):
            mlflow.log_param("silver_table_name", silver_table_name)
            mlflow.log_param("duplication_type", duplication_type)
            mlflow.log_metric("silver_walltime_seconds", walltime)
        return silver_df
    else:
        LogUtil.log(LogType.ERROR, LogLevel.ERROR, "No files processed for silver table.")
        return None





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


def create(
    spark,
    gold_table_name,
    run_id,
    delta_append_df,
    delta_delete_df,
    config,
    duplication_type="append_mode",
    chunk_col="content",
    chunk_flag=True,
    **kwargs,
):
    start_time = time.time()

    # Step 1: cold_update 模式下先删除旧记录
    if duplication_type == "cold_update" and delta_delete_df is not None:
        delete_files = [r["input_file"] for r in delta_delete_df.collect()]
        for f in delete_files:
            spark.sql(f"DELETE FROM {gold_table_name} WHERE input_file = '{f}'")

    # Step 2: chunk 处理
    if delta_append_df is None or delta_append_df.count() == 0:
        LogUtil.log(LogType.ERROR, LogLevel.ERROR, "No new data for gold table.")
        return None

    df_silver = delta_append_df

    if chunk_flag:
        chunking_strategy = kwargs.get("chunking_strategy", "fixed_size_split")
        chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)

        if not chunk_function:
            raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")

        args = {
            "col": func.col(chunk_col),
            "chunk_size": kwargs.get("max_tokens", 512),
            "chunk_overlap": kwargs.get("chunk_overlap", 50),
            "explode": True,
        }

        df_gold = (
            df_silver.withColumn("page_chunks", chunk_function(**args))
            .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
            .withColumn("datetime", func.current_timestamp())
            .drop("page_chunks")
        )
    else:
        df_gold = df_silver

    # Step 3: 写入表
    df_gold.write.format("delta").option("mergeSchema", "true").mode("append").saveAsTable(
        gold_table_name
    )

    # 启用 CDC
    spark.sql(
        f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
    )

    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold table updated successfully.")
    walltime = round(time.time() - start_time, 2)

    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("duplication_type", duplication_type)
        mlflow.log_param("chunking_strategy", kwargs.get("chunking_strategy", ""))
        mlflow.log_metric("gold_walltime_seconds", walltime)

    return df_gold
