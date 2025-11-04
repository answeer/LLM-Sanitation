import time
import mlflow
from pyspark.sql import functions as F
from RAGaaS.logs.logging_setup import LogUtil, LogType, LogLevel
from RAGaaS.data_pipeline.data_reader.read_files import read_file

def _parse_delta_append(spark, delta_append_df, delimiter="^"):
    """
    把 delta append 文件逐个解析为结构化 DF，并补充 file_name/file_hash 字段。
    不使用 collect；使用 toLocalIterator 流式遍历。
    """
    parsed_dfs = []
    for row in delta_append_df.select("input_file", "file_hash").toLocalIterator():
        file_path = row["input_file"]
        file_hash = row["file_hash"]
        try:
            data = read_file(spark, file_path, delimiter) # 返回结构化 DF（列名由你的 reader 决定）
            data = (
                data
                .withColumn("input_file", F.lit(file_path))
                .withColumn("file_hash", F.lit(file_hash))
                .withColumn("datetime", F.current_timestamp())
            )
            parsed_dfs.append(data)
        except Exception as e:
            LogUtil.log(LogType.ERROR, LogLevel.ERROR, f"Silver read error for {file_path}: {e}")

    if not parsed_dfs:
        return None

    df = parsed_dfs[0]
    for d in parsed_dfs[1:]:
        df = df.unionByName(d, allowMissingColumns=True)
    return df

# mode 只用于记录；真正的增删已从 Bronze 传递为 delta_append/delta_delete
def create(spark, silver_table_name, run_id, delta_append_df, delta_delete_names_df, config, delimiter="^", mode="append"):
    """
    仅根据 delta 执行：
      - 解析 delta_append 并 append 到 silver 表
      - 对 delta_delete 的 file_name 执行删除
    返回：本次 append 到 silver 的 DataFrame（可能为 None）
    """
    start_time = time.time()
    table_exists = spark.catalog.tableExists(silver_table_name)

    # 1) 删除（只在 cold update 下非空）
    if delta_delete_names_df is not None and not delta_delete_names_df.limit(1).count() == 0 and table_exists:
        delta_delete_names_df.select("input_file").distinct().createOrReplaceTempView("_silver_to_delete_names")
        spark.sql(f"DELETE FROM {silver_table_name} WHERE input_file IN (SELECT input_file FROM _silver_to_delete_names)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver delete executed.")

    # 2) 追加
    silver_append_df = _parse_delta_append(spark, delta_append_df, delimiter)
    if silver_append_df is not None:
        (silver_append_df.write
            .format("delta")
            .mode("append")
            .option("mergeSchema", "true")
            .saveAsTable(silver_table_name))
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver append executed.")
    else:
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver append empty.")

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("silver_table_name", silver_table_name)
        mlflow.log_param("silver_mode", mode)
        mlflow.log_metric("silver_walltime_seconds", walltime)

    return silver_append_df



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

CHUNK_STRATEGY_MAP = {
    "recursive_character_split": recursive_character_split,
    "fixed_size_split": fixed_size_split,
    "sentence_split": sentence_split,
    "paragraph_split": paragraph_split,
    "token_split": token_split,
    "identity_chunk_udf": identity_chunk_udf,
}


def create(spark, gold_table_name, run_id, silver_delta_append_df, delta_delete_names_df, config, chunk_col, chunk_flag, mode="append",**kwargs):
    """
    仅对 silver_delta_append_df 做增量切块并写入 Gold；
    对 delta_delete_names_df 做基于 input_file 的删除（替换旧版本）。
    返回：本次 append 的 gold DataFrame（可能为 None）
    """
    start_time = time.time()
    table_exists = spark.catalog.tableExists(gold_table_name)

    chunking_strategy = kwargs["chunking_strategy"]
    chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)

    # 1) 删除（仅在 cold update 下非空）
    if delta_delete_names_df is not None and not delta_delete_names_df.limit(1).count() == 0 and table_exists:
        delta_delete_names_df.select("input_file").distinct().createOrReplaceTempView("_gold_to_delete_names")
        spark.sql(f"DELETE FROM {gold_table_name} WHERE input_file IN (SELECT input_file FROM _gold_to_delete_names)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold delete executed.")

    # 2) 追加
    if silver_delta_append_df is None or silver_delta_append_df.limit(1).count() == 0:
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append empty.")
        gold_append_df = None
    else:
        if chunk_flag:
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
                gold_append_df  = (
                    silver_delta_append_df.withColumn("page_chunks", chunk_function(**args))
                    .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
                    .withColumn("datetime", func.current_timestamp())
                    .drop("page_chunks")
                )
            else:
                raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")
        else:
            gold_append_df  = silver_delta_append_df
        
        gold_append_df.write.format("delta").option("mergeSchema", "true").mode("append").saveAsTable(gold_table_name)

        spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append executed.")

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("gold_mode", mode)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_metric("gold_walltime_seconds", walltime)

    return gold_append_df
