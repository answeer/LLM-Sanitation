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



Error occurred: [UNRESOLVED_COLUMN.WITH_SUGGESTION] A column, variable, or function parameter with name `content_chunk` cannot be resolved. Did you mean one of the following? [`control_id`, `control_name`, `control_status`, `input_file`, `coverage`]. SQLSTATE: 42703;\n'Project [risk_id#14954, control_id#14955, control_name#14956, key_control#14957, control_standard#14958, control_description#14959, preventive_detective_flag#14960, manual_automated_flag#14961, coverage#14962, control_frequency#14963, control_status#14964, business_function_name#14965, total_risks_with_active_controls#14966, total_active_controls_mapped#14967, risk_with_most_controls_count#14968, original_risk_count#14969, original_relationship_count#14970, excluded_expired_controls_count#14971, cob#14972, input_file#15033, file_hash#15075, 'explode(_map_pandas_func('content_chunk)#16079) AS page_chunks#16102]\n+- Project [risk_id#14954, control_id#14955, control_name#14956, key_control#14957, control_standard#14958, control_description#14959, preventive_detective_flag#14960, manual_automated_flag#14961, coverage#14962, control_frequency#14963, control_status#14964, business_function_name#14965, total_risks_with_active_controls#14966, total_active_controls_mapped#14967, risk_with_most_controls_count#14968, original_risk_count#14969, original_relationship_count#14970, excluded_expired_controls_count#14971, cob#14972, input_file#15033, 7e30e64c798749981f87460fad56e25edb92771dd09eab081a362224793012d7 AS file_hash#15075]\n  
