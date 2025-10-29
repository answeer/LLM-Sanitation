from pyspark.sql.functions import col,concat_ws,monotonically_increasing_id

# Read existing table
table_df = spark.table("control_details")
filtered_table_df = table_df.select(
    "risk_id",
    "control_id",
    "control_name",
    "control_description",
    "control_info"
)


# Read new file
file_df = (
    spark.read
    .format("csv")
    .option("header", True)
    .option("inferSchema", True)
    .option("delimiter","")
    .load('rag_knowledge_base_update.csv')
)

# Trim column names
file_df = file_df.toDF(*[c.strip() for c in file_df.columns])
filtered_df = file_df.select(
    "risk_id",
    "control_id",
    "control_name",
    "control_description",
    concat_ws(": ", col("control_name"), col("control_description")).alias("control_info")
)

merged_df = (
    filtered_table_df.join(
        file_df.select('risk_id', 'control_id'),
        on=['risk_id', 'control_id'],
        how='left_anti'
    )
    .unionByName(filtered_df)
)
merged_df_with_index = merged_df.withColumn("index", monotonically_increasing_id())
display(merged_df_with_index)
merged_df.write.format("delta").mode("overwrite").saveAsTable("control_details")
