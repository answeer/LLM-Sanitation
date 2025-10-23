def create_silver(spark, silver_table_name, config, manifest_config):
    metadata_fields = []
    if (manifest_config and 
        "extract_metadata" in manifest_config):
        metadata_fields = list(manifest_config["extract_metadata"]["entities"].keys()) if manifest_config["extract_metadata"] else []

    metadata_columns = ""
    for field in metadata_fields:
        metadata_columns += f",\n {field} STRING"

    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'metadata_columns'+ str(metadata_columns))
    spark.sql(
        f"""
    CREATE TABLE IF NOT EXISTS {silver_table_name} (
    input_file STRING,
    file_hash STRING,
    page_nr STRING,
    page_content STRING,
    document_name STRING,
    datetime TIMESTAMP
    {metadata_columns}
    ) TBLPROPERTIES (delta.enableChangeDataFeed = true)
            """
    )

    spark.sql(
        f"""
    alter table {silver_table_name}
    set tags ('createdBy'='{config['created_by']}','managedby' ='{config['managedby']}' ,'lob'='{config['lob']}','supportedby'='{config['supportedby']}','ito_unit'='{config['ito_unit']}','business_unit'='{config['business_unit']}',"project_costcenter_id"='{config['project_costcenter_id']}','bau_costcenter_id'='{config['bau_costcenter_id']}','clarity_id' ='{config['clarity_id']}','app_id'='{config['app_id']}',"rag_serving_endpoint_name"='{config['rag_serving_endpoint_name']}')
            """
    )
    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Silver table created successfully")
