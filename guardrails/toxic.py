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
