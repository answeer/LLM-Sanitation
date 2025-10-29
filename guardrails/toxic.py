import pyspark.sql.functions as func
from RAGaaS.data_pipeline.medallian_tables.from_files.create_medallian_table import (
    create_silver,
)
import pyspark.sql.functions as func
from RAGaaS.data_pipeline.data_reader.pdf_reader import read_pdf_spark
from RAGaaS.data_pipeline.medallian_tables.from_files.extract_matadata import MetadataExtractor
from RAGaaS.logs.logging_setup   import LogUtil, LogType, LogLevel
import mlflow
import time
##

def file_cleaning(silver_df):
    regular_expression = r".*\/([^\/]+)\/([^\/]+)\.pdf"
    return silver_df.withColumn(
        "document_name",
        func.concat(
            func.regexp_replace(
                func.lower(func.regexp_extract("input_file", regular_expression, 1)),
                " ",
                "_",
            ),
            func.lit("/"),
            func.concat(
                func.regexp_replace(
                    func.lower(
                        func.regexp_extract("input_file", regular_expression, 2)
                    ),
                    " ",
                    "_",
                )
            ),
        ),
    ).withColumn("datetime", func.current_timestamp())


def create(spark, silver_table_name, run_id, bronze_df,config, manifest_config):
    start_time = time.time()

    create_silver(spark, silver_table_name,config) # pragma: no cover

    df_parsed = bronze_df.select(
        func.col("input_file"),
        func.col("file_hash"),
        read_pdf_spark("content").alias("parsed_pdf_pages"),
    )

    silver_df = (
        df_parsed.select("*", func.explode("parsed_pdf_pages"))
        .withColumnRenamed("key", "page_nr")
        .withColumnRenamed("value", "page_content")
        .drop("parsed_pdf_pages")
    )

    # Extract meta data only if specified in manifest
    if manifest_config["extract_metadata"]:
        metadata_extractor = MetadataExtractor(manifest_config)
        metadata_df = metadata_extractor.create_metadata_dataframe(spark, silver_df)

        if metadata_extractor.fields:
            silver_df = silver_df.join(metadata_df, ["input_file", "page_nr"], "left")

    silver_df = file_cleaning(silver_df)

    silver_df.write.format("delta").mode("overwrite").saveAsTable(silver_table_name)

    walltime = round(time.time() - start_time, 2)
    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 'Silver table created successfully.')

    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("silver_table_name", silver_table_name)
        mlflow.log_metric("silver_walltime_seconds", walltime)

    return silver_df

















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

def clean_gold(spark, gold_table_name):
    df_gold = spark.table(gold_table_name)
    w = Window.partitionBy("input_file","page_nr").orderBy(func.col("datetime").desc())

    df_latest = (
        df_gold.withColumn("rn", func.row_number().over(w)).filter(func.col("rn") == 1).drop("rn")
    ) # pragma: no cover
    df_latest.write.mode("overwrite").saveAsTable(gold_table_name)

def create(spark, gold_table_name, run_id,  df_silver,config,**kwargs):
    start_time = time.time()

    print("gold_table_name",gold_table_name)
    spark.sql('select current_version()').show()
    create_gold(spark, gold_table_name,config) # pragma: no cover

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

    df_gold = (
        df_silver.withColumn("page_chunks", chunk_function(**args))
        .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
        .withColumn("datetime", func.current_timestamp())
        .drop("page_chunks")
    )

    #print("table empty",is_delta_table_empty(spark,gold_table_name))
    print("df_gold",df_gold)
    print("gold_table_name",gold_table_name)


    df_gold.write.format("delta").option("mergeSchema", "true").mode("append").saveAsTable(gold_table_name)

    ## remove duplicates
    clean_gold(spark, gold_table_name)
    
    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Gold table created successfully.')
    walltime = round(time.time() - start_time, 2)

    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_metric("gold_walltime_seconds", walltime)

