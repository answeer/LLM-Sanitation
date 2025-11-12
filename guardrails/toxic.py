import pyspark.sql.functions as func
from pyspark.sql import Window
from RAGaaS.data_pipeline.chunking.chunking_methods import (
    recursive_character_split,
    fixed_size_split,
    paragraph_split,
    sentence_split,
    token_split,
)
from RAGaaS.data_pipeline.medallian_tables.from_files.create_medallian_table import (
    create_gold,
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
}


def create(
    spark,
    gold_table_name,
    run_id,
    silver_delta_append_df,
    config,
    mode="append",
    delta_delete_names_df=None,
    chunk_col="page_content",
    **kwargs,
):
    """
    Gold 表构建 & 追加（带可配置 chunk 列）

    新增能力：
    - chunk_col 可以是:
        - str: 原行为（默认 "page_content"）
        - list/tuple[str]: 先将这些列拼成一个新列，再基于该新列做 chunk
    - 合并列名可通过 kwargs["merged_chunk_col"] 指定，未指定时默认 "_merged_chunk_content"，
      若重名会自动避让。
    """
    start_time = time.time()
    create_gold(spark, gold_table_name, config)

    # === 1) 校验 & 获取 chunking 策略 ===
    chunking_strategy = kwargs.get("chunking_strategy")
    if not chunking_strategy:
        raise ValueError("chunking_strategy is required.")

    chunk_function = CHUNK_STRATEGY_MAP.get(chunking_strategy)
    if not chunk_function:
        raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")

    if chunking_strategy not in [
        "recursive_character_split",
        "fixed_size_split",
        "sentence_split",
        "paragraph_split",
        "token_split",
    ]:
        raise ValueError(f"Unsupported chunking strategy: {chunking_strategy}")

    table_exists = spark.catalog.tableExists(gold_table_name)

    # === 2) 删除逻辑（可选）===
    if (
        delta_delete_names_df is not None
        and not delta_delete_names_df.limit(1).count() == 0
        and table_exists
    ):
        delta_delete_names_df.select("file_name").distinct().createOrReplaceTempView(
            "_gold_to_delete_names"
        )
        spark.sql(
            f"""
            DELETE FROM {gold_table_name}
            WHERE file_name IN (SELECT file_name FROM _gold_to_delete_names)
            """
        )
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold delete executed.")

    # === 3) 追加逻辑（含多列合并 chunk）===
    if silver_delta_append_df is None or silver_delta_append_df.limit(1).count() == 0:
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append empty.")
        gold_out = None
    else:
        # 3.1 确定用于 chunk 的有效列
        # 默认向后兼容：chunk_col="page_content" 时行为不变
        if isinstance(chunk_col, str):
            effective_chunk_col = chunk_col

        elif isinstance(chunk_col, (list, tuple)):
            if len(chunk_col) == 0:
                raise ValueError("chunk_col list cannot be empty.")

            merged_col_name = kwargs.get("merged_chunk_col", "_merged_chunk_content")

            # 避免与已有列名冲突
            if merged_col_name in silver_delta_append_df.columns:
                base = merged_col_name
                i = 1
                while merged_col_name in silver_delta_append_df.columns:
                    merged_col_name = f"{base}_{i}"
                    i += 1

            # 多列合并：空值转空串，用 \n\n 分隔，方便下游阅读/切块
            silver_delta_append_df = silver_delta_append_df.withColumn(
                merged_col_name,
                func.concat_ws(
                    "\n\n",
                    *[
                        func.coalesce(func.col(c).cast("string"), func.lit(""))
                        for c in chunk_col
                    ],
                ),
            )
            effective_chunk_col = merged_col_name

        else:
            raise TypeError(
                "chunk_col must be a string or a list/tuple of strings."
            )

        # 3.2 组装 chunk 函数参数
        # 沿用原始逻辑：始终对 effective_chunk_col 做 chunk
        args = {
            "col": func.col(effective_chunk_col),
            "chunk_size": kwargs["max_tokens"],
            "chunk_overlap": kwargs["chunk_overlap"],
            "explode": True,
        }

        # 3.3 执行 chunk + 补充字段
        df_to_write = (
            silver_delta_append_df.withColumn("page_chunks", chunk_function(**args))
            .withColumn("content_chunk", func.col("page_chunks.content_chunk"))
            .withColumn("datetime", func.current_timestamp())
            .drop("page_chunks")
        )

        # 3.4 写入 Gold 表
        df_to_write.write.format("delta") \
            .option("mergeSchema", "true") \
            .mode("append") \
            .saveAsTable(gold_table_name)

        # 启用 CDF
        spark.sql(
            f"ALTER TABLE {gold_table_name} "
            f"SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
        )
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Gold append executed.")

        gold_out = df_to_write

    # === 4) MLflow 记录 ===
    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("gold_mode", mode)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_metric("gold_walltime_seconds", walltime)

    return gold_out
