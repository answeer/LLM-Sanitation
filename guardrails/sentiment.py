# bronze_csv_excel.py
import time
import mlflow
from pyspark.sql import functions as F
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
from RAGaaS.data_pipeline.medallian_tables.from_files.create_medallian_table import create_bronze

def _df_is_empty(df):
    return df is None or df.limit(1).count() == 0

# mode: "append" | "cold_update"
def create(spark, bronze_table_name, run_id, source_folder, config, mode="append"):
    start_time = time.time()
    create_bronze(spark, bronze_table_name, config)

    # 读取 CSV/Excel，作为二进制仅用于计算 hash；不把 content 落表、不传给下游
    src_df = (
        spark.read.format("binaryFile")
        .option("recursiveFileLookup", "true")
        .option("pathGlobFilter", "*.{csv,CSV,xls,XLS,xlsx,XLSX}")
        .load(source_folder)
        .withColumnRenamed("path", "input_file")
        .withColumn("file_name", F.regexp_extract(F.col("input_file"), r"([^/\\]+)$", 1))
        .withColumn("file_hash", F.sha2(F.col("content"), 256))  # 对二进制内容计算 SHA-256
        .withColumn("datetime", F.current_timestamp())
        .select("input_file", "file_name", "file_hash", "modificationTime", "length", "datetime")
    )

    table_exists = spark.catalog.tableExists(bronze_table_name)

    if not table_exists:
        delta_append_df = src_df
        delta_delete_names_df = spark.createDataFrame([], src_df.select("file_name").schema)

        if not _df_is_empty(delta_append_df):
            (delta_append_df.write.format("delta").mode("append").saveAsTable(bronze_table_name))

    else:
        existing = spark.table(bronze_table_name).select("file_name", "file_hash")
        # 新来但未出现过的 (file_name, file_hash)
        nondupe_src = src_df.join(existing, on=["file_name", "file_hash"], how="left_anti")

        if mode == "append":
            delta_append_df = nondupe_src
            delta_delete_names_df = spark.createDataFrame([], src_df.select("file_name").schema)

            if not _df_is_empty(delta_append_df):
                delta_append_df.write.format("delta").mode("append").saveAsTable(bronze_table_name)

        elif mode == "cold_update":
            existing_names = spark.table(bronze_table_name).select("file_name").distinct()
            same_name_new = nondupe_src.join(existing_names, on="file_name", how="inner")     # 同名新 hash
            brand_new     = nondupe_src.join(existing_names, on="file_name", how="left_anti") # 全新文件名

            to_delete_names = same_name_new.select("file_name").distinct()
            if not _df_is_empty(to_delete_names):
                to_delete_names.createOrReplaceTempView("_bronze_to_delete_names")
                spark.sql(f"""
                    DELETE FROM {bronze_table_name}
                    WHERE file_name IN (SELECT file_name FROM _bronze_to_delete_names)
                """)
                delta_delete_names_df = to_delete_names.select("file_name")
            else:
                delta_delete_names_df = spark.createDataFrame([], src_df.select("file_name").schema)

            delta_append_df = same_name_new.unionByName(brand_new)
            if not _df_is_empty(delta_append_df):
                delta_append_df.write.format("delta").mode("append").saveAsTable(bronze_table_name)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, f"Bronze delta computed. mode={mode}")
    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("bronze_table_name", bronze_table_name)
        mlflow.log_param("bronze_mode", mode)
        mlflow.log_metric("bronze_walltime_seconds", walltime)

    # 返回给 Silver 的 delta：append（路径+键），delete（仅 file_name）
    return (
        delta_append_df.select("input_file", "file_name", "file_hash"),
        delta_delete_names_df.select("file_name").distinct(),
    )



# silver_pdf.py
import time
import mlflow
from pyspark.sql import functions as F
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
from RAGaaS.data_pipeline.medallian_tables.from_files.create_medallian_table import create_silver
from RAGaaS.data_pipeline.data_reader.pdf_reader import read_pdf_spark
from RAGaaS.data_pipeline.medallian_tables.from_files.extract_matadata import MetadataExtractor

def _df_is_empty(df):
    return df is None or df.limit(1).count() == 0

def file_cleaning(silver_df):
    regular_expression = r".*\/([^\/]+)\/([^\/]+)\.pdf"
    return (
        silver_df.withColumn(
            "document_name",
            F.concat(
                F.regexp_replace(F.lower(F.regexp_extract("input_file", regular_expression, 1)), " ", "_"),
                F.lit("/"),
                F.regexp_replace(F.lower(F.regexp_extract("input_file", regular_expression, 2)), " ", "_"),
            ),
        )
        .withColumn("datetime", F.current_timestamp())
    )

def create(
    spark,
    silver_table_name,
    run_id,
    delta_append_df,              # 来自 Bronze（含 content）
    config,
    manifest_config,
    mode="append",
    delta_delete_names_df=None,   # 来自 Bronze（仅 file_name），cold_update 才会传
):
    start_time = time.time()
    create_silver(spark, silver_table_name, config)

    table_exists = spark.catalog.tableExists(silver_table_name)

    # 1) 删除（仅 cold_update 有值）
    if delta_delete_names_df is not None and not _df_is_empty(delta_delete_names_df) and table_exists:
        delta_delete_names_df.select("file_name").distinct().createOrReplaceTempView("_silver_to_delete_names")
        spark.sql(f"""
            DELETE FROM {silver_table_name}
            WHERE file_name IN (SELECT file_name FROM _silver_to_delete_names)
        """)
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver delete executed.")

    # 2) 追加（解析 PDF）
    if _df_is_empty(delta_append_df):
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver append empty.")
        silver_out = None
    else:
        # 逐行调用 UDF（列向量化）：read_pdf_spark("content") -> array<struct<key,value>>
        df_parsed = delta_append_df.select(
            F.col("input_file"),
            F.col("file_name"),
            F.col("file_hash"),
            read_pdf_spark("content").alias("parsed_pdf_pages"),
        )

        silver_df = (
            df_parsed
            .select("*", F.explode("parsed_pdf_pages"))
            .withColumnRenamed("key", "page_nr")
            .withColumnRenamed("value", "page_content")
            .drop("parsed_pdf_pages")
        )

        # 可选：抽取元数据
        if manifest_config.get("extract_metadata"):
            metadata_extractor = MetadataExtractor(manifest_config)
            metadata_df = metadata_extractor.create_metadata_dataframe(spark, silver_df)
            if metadata_extractor.fields:
                silver_df = silver_df.join(metadata_df, ["input_file", "page_nr"], "left")

        silver_df = file_cleaning(silver_df)

        (silver_df.write
            .format("delta")
            .mode("append")
            .option("mergeSchema", "true")
            .saveAsTable(silver_table_name))

        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver append executed.")
        silver_out = silver_df

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("silver_table_name", silver_table_name)
        mlflow.log_param("silver_mode", mode)
        mlflow.log_metric("silver_walltime_seconds", walltime)

    return silver_out



# gold_pdf.py
import time
import mlflow
from pyspark.sql import functions as F
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
from RAGaaS.data_pipeline.medallian_tables.from_files.create_medallian_table import create_gold
from RAGaaS.data_pipeline.chunking.chunking_methods import (
    recursive_character_split,
    fixed_size_split,
    paragraph_split,
    sentence_split,
    token_split,
    identity_chunk_udf,
)

def _df_is_empty(df):
    return df is None or df.limit(1).count() == 0

CHUNK_STRATEGY_MAP = {
    "recursive_character_split": recursive_character_split,
    "fixed_size_split": fixed_size_split,
    "sentence_split": sentence_split,
    "paragraph_split": paragraph_split,
    "token_split": token_split,
    "identity_chunk_udf": identity_chunk_udf,
}

def _chunk_df(df, chunk_col, chunking_strategy, max_tokens, chunk_overlap):
    fn = CHUNK_STRATEGY_MAP.get(chunking_strategy)
    if fn is None:
        raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")

    # 统一在这里 explode，避免依赖 UDF 内部是否 explode
    page_chunks = fn(
        col=F.col(chunk_col),
        chunk_size=max_tokens,
        chunk_overlap=chunk_overlap,
        explode=False,
    )
    return (
        df.withColumn("page_chunks", page_chunks)
          .withColumn("page_chunk", F.explode_outer("page_chunks"))
          .withColumn("content_chunk", F.col("page_chunk.content_chunk"))
          .withColumn("chunk_index", F.col("page_chunk.idx"))
          .withColumn("datetime", F.current_timestamp())
          .drop("page_chunks", "page_chunk")
    )

def create(
    spark,
    gold_table_name,
    run_id,
    silver_delta_append_df,        # 仅本次新增/更新的银层数据（须含 file_name, page_content）
    config,
    mode="append",
    delta_delete_names_df=None,    # 来自 Bronze（仅 file_name）
    chunk_col="page_content",
    chunk_flag=True,
    chunking_strategy="recursive_character_split",
    max_tokens=512,
    chunk_overlap=50,
):
    start_time = time.time()
    create_gold(spark, gold_table_name, config)

    table_exists = spark.catalog.tableExists(gold_table_name)

    # 1) 删除（仅 cold_update 有值）
    if delta_delete_names_df is not None and not _df_is_empty(delta_delete_names_df) and table_exists:
        delta_delete_names_df.select("file_name").distinct().createOrReplaceTempView("_gold_to_delete_names")
        spark.sql(f"""
            DELETE FROM {gold_table_name}
            WHERE file_name IN (SELECT file_name FROM _gold_to_delete_names)
        """)
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold delete executed.")

    # 2) 追加（针对 silver delta）
    if _df_is_empty(silver_delta_append_df):
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append empty.")
        gold_out = None
    else:
        df_to_write = (
            _chunk_df(silver_delta_append_df, chunk_col, chunking_strategy, max_tokens, chunk_overlap)
            if chunk_flag else
            silver_delta_append_df.withColumn("datetime", F.current_timestamp())
        )

        (df_to_write.write
            .format("delta")
            .option("mergeSchema", "true")
            .mode("append")
            .saveAsTable(gold_table_name))

        # 启用 CDF，若已启用不会报错
        spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append executed.")
        gold_out = df_to_write

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("gold_mode", mode)
        mlflow.log_param("chunk_flag", chunk_flag)
        mlflow.log_param("chunking_strategy", chunking_strategy if chunk_flag else "disabled")
        mlflow.log_metric("gold_walltime_seconds", walltime)

    return gold_out
