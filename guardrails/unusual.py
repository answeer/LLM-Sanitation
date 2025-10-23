def create_bronze(spark, bronze_table_name, config):
    spark.sql(
        f"""
    CREATE TABLE IF NOT EXISTS {bronze_table_name} (
    input_file STRING,
    modificationTime TIMESTAMP,
    length BIGINT,
    content BINARY,
    datetime TIMESTAMP,
    file_hash STRING
    ) TBLPROPERTIES (delta.enableChangeDataFeed = true)
            """
    )

    spark.sql(
        f"""
    alter table {bronze_table_name}
    set tags ('createdBy'='{config['created_by']}','managedby' ='{config['managedby']}' ,'lob'='{config['lob']}','supportedby'='{config['supportedby']}','ito_unit'='{config['ito_unit']}','business_unit'='{config['business_unit']}',"project_costcenter_id"='{config['project_costcenter_id']}','bau_costcenter_id'='{config['bau_costcenter_id']}','clarity_id' ='{config['clarity_id']}','app_id'='{config['app_id']}',"rag_serving_endpoint_name"='{config['rag_serving_endpoint_name']}')
            """
    )

    LogUtil.log(LogType.TRANSACTION, LogLevel.INFO, "Bronze table created successfully")
