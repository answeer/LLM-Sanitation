def create(spark, silver_table_name, run_id, bronze_df, config, delimiter="^", deduplication_method="cold_duplicate"):
    start_time = time.time()
    
    # 根据去重策略处理数据
    if deduplication_method == "cold_duplicate":
        # 冷去重：过滤掉已经处理过的文件
        table_exists = spark.catalog.tableExists(silver_table_name)
        if table_exists:
            existing_hashes_df = spark.table(silver_table_name).select("file_hash").distinct()
            bronze_rows = bronze_df.join(
                existing_hashes_df, on="file_hash", how="left_anti"
            ).select("input_file", "file_hash").collect()
        else:
            bronze_rows = bronze_df.select("input_file", "file_hash").collect()
    elif deduplication_method == "append":
        # 直接追加：处理所有文件
        bronze_rows = bronze_df.select("input_file", "file_hash").collect()
    else:
        raise ValueError(f"Unsupported deduplication method: {deduplication_method}")
    
    appended_dfs = []
    for row in bronze_rows:
        file_path = row['input_file']
        file_hash = row['file_hash']
        try:
            print("??????? file_path  ", file_path)
            data = read_file(spark, file_path, delimiter)
            print("--------> data ", data)

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
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, f"Silver table created successfully with {deduplication_method} strategy.")

        with mlflow.start_run(run_id=run_id):
            mlflow.log_param("silver_table_name", silver_table_name)
            mlflow.log_param("silver_deduplication_method", deduplication_method)
            mlflow.log_metric("silver_walltime_seconds", walltime)
            mlflow.log_metric("silver_files_processed", len(appended_dfs))
        return silver_df
    else:
        LogUtil.log(LogType.ERROR, LogLevel.ERROR, "No files processed for silver table.")
        return None






def create(spark, gold_table_name, run_id, df_silver, config, chunk_col, chunk_flag, 
           deduplication_method="cold_duplicate", **kwargs):
    start_time = time.time()

    # 处理分块逻辑
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

    # 根据去重策略处理数据
    if deduplication_method == "cold_duplicate":
        # 冷去重：基于内容哈希去重
        table_exists = spark.catalog.tableExists(gold_table_name)
        if table_exists:
            # 为当前批次生成内容哈希
            if chunk_flag:
                df_gold = df_gold.withColumn("content_hash", hash_text_udf(func.col("content_chunk")))
            else:
                df_gold = df_gold.withColumn("content_hash", hash_text_udf(func.col(chunk_col)))
            
            # 获取已存在的内容哈希
            existing_content_hashes = spark.table(gold_table_name).select("content_hash").distinct()
            
            # 过滤掉重复的内容
            df_gold = df_gold.join(
                existing_content_hashes, on="content_hash", how="left_anti"
            )
    
    # 写入数据
    df_gold.write.format("delta").option("mergeSchema", "true").mode("append").saveAsTable(gold_table_name)

    spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, f"Gold table created successfully with {deduplication_method} strategy.")

    walltime = round(time.time() - start_time, 2)
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("gold_table_name", gold_table_name)
        mlflow.log_param("chunking_strategy", chunking_strategy)
        mlflow.log_param("gold_deduplication_method", deduplication_method)
        mlflow.log_metric("gold_walltime_seconds", walltime)
        
        # 记录处理的数据量
        if chunk_flag:
            chunk_count = df_gold.count() if df_gold else 0
            mlflow.log_metric("gold_chunks_processed", chunk_count)
        else:
            record_count = df_gold.count() if df_gold else 0
            mlflow.log_metric("gold_records_processed", record_count)
            
    return df_gold
