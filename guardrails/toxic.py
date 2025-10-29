if deduplicated_new_data.count() > 0:
                # 合并数据：现有数据 + 去重后的新数据
                final_silver_df = existing_table_df.unionByName(deduplicated_new_data)
                
                # 使用overwrite模式写入（因为我们已经合并了数据）
                final_silver_df.write.format("delta").mode("overwrite").saveAsTable(silver_table_name)
                
                LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 
                           f"Silver table updated with {deduplicated_new_data.count()} new records using cold_duplicate.")
            else:
                final_silver_df = existing_table_df
                LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 
                           "No new records to add to Silver table.")




import pyspark.sql.functions as func
from pyspark.sql.functions import col, concat_ws, monotonically_increasing_id
from pyspark.sql import Window
from RAGaaS.data_pipeline.chunking.chunking_methods import (
    recursive_character_split, fixed_size_split, paragraph_split, 
    sentence_split, token_split, identity_chunk_udf
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


def create(spark, gold_table_name, run_id, df_silver, config, chunk_col, chunk_flag, 
           deduplication_method="cold_duplicate", **kwargs):
    start_time = time.time()

    # 处理分块逻辑
    if chunk_flag:
        chunking_strategy = kwargs["chunking_strategy"]
        chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)
        if chunking_strategy in CHUNK_STRATEGY_MAP.keys():
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
            raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")
    else:
        # 如果不分块，直接使用原始内容
        df_gold = df_silver.withColumn("content_chunk", func.col(chunk_col))\
                          .withColumn("datetime", func.current_timestamp())

    # 根据去重策略处理
    if deduplication_method == "cold_duplicate":
        table_exists = spark.catalog.tableExists(gold_table_name)
        
        if table_exists:
            # 读取现有Gold表
            existing_gold_df = spark.table(gold_table_name)
            
            # 基于业务键进行去重 - 使用与Silver层相同的逻辑
            # 假设业务键是 risk_id 和 control_id，根据实际情况调整
            key_columns = ["risk_id", "control_id"]
            
            # 排除已存在的记录（基于业务键）
            deduplicated_new_records = df_gold.join(
                existing_gold_df.select(*key_columns),
                on=key_columns,
                how='left_anti'
            )
            
            if deduplicated_new_records.count() > 0:
                # 合并现有数据和新数据
                final_gold_df = existing_gold_df.unionByName(deduplicated_new_records)
                
                # 使用overwrite模式写入合并后的数据
                final_gold_df.write.format("delta").mode("overwrite").saveAsTable(gold_table_name)
                
                LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 
                           f"Gold table updated with {deduplicated_new_records.count()} new records using cold_duplicate.")
            else:
                final_gold_df = existing_gold_df
                LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 
                           "No new records to add to Gold table.")
        else:
            # 表不存在，直接创建
            df_gold.write.format("delta").mode("overwrite").saveAsTable(gold_table_name)
            final_gold_df = df_gold
            LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 
                       "Gold table created with all new records.")
            
    elif deduplication_method == "append":
        # 直接追加
        df_gold.write.format("delta").mode("append").saveAsTable(gold_table_name)
        final_gold_df = spark.table(gold_table_name)
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, 
                   f"Gold table appended with {df_gold.count()} records.")
    else:
        raise ValueError(f"Unsupported deduplication method: {deduplication_method}")

    # 设置表属性
    spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("gold_deduplication_method", deduplication_method)
        if chunk_flag:
            mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_metric("gold_walltime_seconds", walltime)
        mlflow.log_metric("gold_records_processed", df_gold.count())

    return final_gold_df
