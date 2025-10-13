import pyspark.sql.functions as func
from pyspark.sql.types import StructType, StructField, StringType
from RAGaaS.data_pipeline.medallian_tables.create_medallian_table import (
    create_silver,
)
from RAGaaS.data_pipeline.data_reader.pdf_reader import read_pdf_spark
from RAGaaS.logs.logging_setup   import LogUtil, LogType, LogLevel
import mlflow
import time
import json

def extract_metadata_from_content(page_content, model):
    prompt = (
        "Extract the following metadata from the document text below. "
        "If not found, return 'N/A'.\n\nDocument text: " + page_content +
        "\n\nReturn as JSON: { 'article_id': ..., 'publication_date': ..., 'effective_date': ... }"
    )
    try:
        response = model.invoke(prompt)
        content = response.content.replace("json","").replace("\n","").replace("`","").replace("```","")
        print("------------")
        print(len(page_content))
        print("------------")

        # print("------------")
        # print(content)
        # print("------------")
       
        metadata = json.loads(content)
        article_id = metadata.get("article_id", "N/A")
        publication_date = metadata.get("publication_date", "N/A")
        effective_date = metadata.get("effective_date", "N/A")
        print(article_id, publication_date, effective_date)
        return article_id, publication_date, effective_date
        
    except Exception as e:
        print(f"Error calling Databricks LLM: {e}")
        return "N/A", "N/A", "N/A"

def file_cleaning():
    regular_expression = r".*\/([^\/]+)\/([^\/]+)\.pdf"
    silver_df = silver_df.withColumn(
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

def create(spark, silver_table_name, run_id, bronze_df):
    start_time = time.time()
    create_silver(spark, silver_table_name)
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
    # --- LLM Metadata Extraction on driver ---
    # Instantiate ChatDatabricks ONLY on the driver, not globally!
    from databricks_langchain.chat_models import ChatDatabricks
    model = ChatDatabricks(
        endpoint="databricks-claude-3-7-sonnet",
        extra_params={"temperature": 0.01, "max_tokens": 500}
    )

    # Group by input_file and aggregate page_content
    doc_df = silver_df.groupBy("input_file").agg(
    func.concat_ws(" ", func.collect_list("page_content")).alias("document_content"),
    func.count("page_content").alias("num_pages")
)
    
    doc_rows = doc_df.collect()
    metadata_results = []
    
    for doc_row in doc_rows:
        article_id, publication_date, effective_date = extract_metadata_from_content(doc_row.document_content, model)
        
        # Get the number of pages for the current document
        num_pages = silver_df.filter(silver_df.input_file == doc_row.input_file).count()

        print(doc_row.input_file)
        print("num_pages ", num_pages, doc_row.num_pages)
        
        # Append the metadata result for each page
        for pg_nr in range(doc_row.num_pages):
            metadata_results.append({
                "input_file": doc_row.input_file,
                "page_nr": str(pg_nr),
                "article_id": article_id or "N/A",
                "publication_date": publication_date or "N/A",
                "effective_date": effective_date or "N/A"
            })

    print("metadata_results  ", metadata_results)

    # Create metadata DataFrame
    metadata_schema = StructType([
        StructField("input_file", StringType(), False),
        StructField("page_nr", StringType(), False),
        StructField("article_id", StringType(), True),
        StructField("publication_date", StringType(), True),
        StructField("effective_date", StringType(), True),
    ])

    metadata_df = spark.createDataFrame(metadata_results, schema=metadata_schema)
    # Join metadata back to silver_df
    silver_df = silver_df.join(metadata_df, ["input_file", "page_nr"], "left")
    silver_df.write.mode("overwrite").saveAsTable(silver_table_name)
    walltime = round(time.time() - start_time, 2)
    silver_df.write.format("delta").mode("append").saveAsTable(silver_table_name)
    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Silver table created successfully.')
    with mlflow.start_run(run_id=run_id):
        mlflow.log_param("silver_table_name", silver_table_name)
        mlflow.log_metric("silver_walltime_seconds", walltime)
    return silver_df
