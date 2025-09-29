import pyspark.sql.functions as func
from pyspark.sql import Window
from RAGaaS.data_pipeline.chunking.chunking_methods import recursive_character_split, fixed_size_split, paragraph_split, sentence_split, token_split
from RAGaaS.data_pipeline.medallian_tables.create_medallian_table import (
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
        df_gold.withColumn("rn", func.row_number().over(w)).filter("rn == 1").drop("rn")
    )

def create(spark, gold_table_name, run_id,  df_silver, **kwargs):
    start_time = time.time()

    print("gold_table_name",gold_table_name)
    spark.sql('select current_version()').show()
    create_gold(spark, gold_table_name)

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
