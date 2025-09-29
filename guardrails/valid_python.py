from pathlib import Path
import sys
script_path = Path(sys.argv[0])
sys.path.insert(0, str(Path(script_path).parent.parent.parent))
import pandas as pd
import json
from RAGaaS.utils.create_spark_sess import spark,dbutils
# spark = get_spark()
# print("spark   ", spark)
# dbutils = get_dbutils(spark)

import argparse

from RAGaaS.data_pipeline.data_ingestion.filenet_connecter import FilenetConnector
from RAGaaS.data_pipeline.medallian_tables import (
    create_bronze,
    create_silver,
    create_gold,
)
import mlflow
from RAGaaS.data_pipeline.vector_index import VectorIndex
from RAGaaS.utils.create_experiment import create_experiment, set_run_failed
from RAGaaS.utils.get_config import read_manifest, read_project_config, log_manifest, log_config, log_table, get_or_create_vol
from RAGaaS.utils.get_cluster_params import get_akv_secrets, get_rag_cert
from RAGaaS.logs.logging_setup   import LogUtil, LogType, LogLevel
from RAGaaS.data_pipeline.medallian_tables.housekeeping import housekeeping

import traceback


class DataPipeline:
    def __init__(self,project_config, doc_id_path):
        
        LogUtil.log(LogType.APPLICATION, LogLevel.INFO,'DataPipeline started')
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Step 1: read cluster params')

        self.project_config = project_config
        self.doc_id_path = doc_id_path

        # Step 1: read cluster params
        self.project_name = self.project_config['project_name']
        self.version = self.project_config['version']
        # start mlflow experiment
        self.run_id, _ = create_experiment("ragaas_embedding_pipeline_creation", project_config)
        self.catalog_name = self.project_config['catalog_name']
        self.schema_name = self.project_config['schema_name']
        # self.fn_cert = "./FileNet.crt"
        # get volumes
        self.source_folder_volume = self.project_config["project_artefacts"]["source_folder_volume"]

        folders = self.source_folder_volume.split("/")
        catalog_name = folders[2]
        schema_name = folders[3]
        volume = folders[4]
        get_or_create_vol(catalog_name, schema_name, volume)
        self.service_volume = self.project_config["project_artefacts"]["service_volume"]

        self.rag_scope = "scaifactory_secret_scope"
        self.embedding_model = self.project_config['embedding_model']
        # self.rag_cert = get_rag_cert(self.rag_scope, "app--development--hcv--AppStaticSecret--key-store--aifactoryragdev--rag-client-cert", self.service_volume) #config['cert']# if we put it in manifest
        # self.rag_token_url = get_akv_secrets(self.rag_scope, "app--development--hcv--AppStaticSecret--key-store--aifactoryragdev--rag-token-url")
        # self.rag_client_id = get_akv_secrets(self.rag_scope, "app--development--hcv--AppStaticSecret--key-store--aifactoryragdev--rag-client-id")
        # self.rag_client_secret = get_akv_secrets(self.rag_scope, "app--development--hcv--AppStaticSecret--key-store--aifactoryragdev--rag-client-secret")

        # get medallian table names
        self.bronze_table_name = self.project_config["project_artefacts"]["bronze_table_name"]
        self.silver_table_name = self.project_config["project_artefacts"]["silver_table_name"]
        self.gold_table_name = self.project_config["project_artefacts"]["gold_table_name"]

        # get vs parameters
        self.vs_index_name = self.project_config["project_artefacts"]["vs_index_name"]
        self.vs_endpoint_name = self.project_config["project_artefacts"]["vs_endpoint_name"]

        self.embedding_model = self.project_config['embedding_model']
        self.chunking_strategy = self.project_config['chunking_strategy']
        self.chunk_overlap =  self.project_config['chunk_overlap']
        self.max_tokens =  self.project_config['max_tokens']


    def run(self):

        # Step 2: Data Ingestion
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Step 2: Data Ingestion')
        print("Starting data ingestion...")
        # Parse document_ids
        #parse document ids, doc class name, os name from excel right

        # try:

        #     self.csv_df = spark.read.format("csv") \
        #         .option("header", "true") \
        #         .option("inferSchema", "true") \
        #         .load(self.doc_id_path)
        # except Exception:
        #     print("Error in reading csv file")

        # fn_conn = FilenetConnector(
        #     self.rag_cert,
        #     self.rag_token_url,
        #     self.rag_client_id,
        #     self.rag_client_secret,
        #     self.csv_df,
        #     self.run_id
        # )


        # #call here fn get files
        # fn_conn.get_files(self.csv_df, self.source_folder_volume)

        # Step 3: Create bronze table
        print("Creating bronze table...")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Step 3: Creating bronze table')
        bronze_df = create_bronze(spark, self.bronze_table_name, self.run_id, self.source_folder_volume)

        # Step 4: Create silver table
        print("Creating silver table...")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Step 4: Creating silver table')
        silver_df = create_silver(spark, self.silver_table_name, self.run_id, bronze_df)

        # Step 5: Create gold table
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Step 5: Creating gold table')
        print("Creating gold table...")
        kwargs = {
            "embedding_model": self.embedding_model,
            "chunking_strategy": self.chunking_strategy,
            "chunk_overlap": self.chunk_overlap,
            "max_tokens": self.max_tokens
        }
        _ = create_gold(spark, self.gold_table_name, self.run_id, silver_df, **kwargs)

        # Step 6: Create vector search index
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Step 6: Create vector search index')
        print("Creating vector search index...")
        vcs_index = VectorIndex(self.run_id)
        vcs_index.create_vs_index(
            vs_index_name=self.vs_index_name,
            vs_endpoint_name=self.vs_endpoint_name,
            gold_table_name=self.gold_table_name,
            embedding_endpoint_name=self.embedding_model
        )

        # Step 7: Housekeeping tasks to delete medallian tables
        print("Housekeeping...")
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,'Step 7: Housekeeping')
        # housekeeping(spark, dbutils,self.bronze_table_name, self.silver_table_name)
        LogUtil.log(LogType.APPLICATION, LogLevel.INFO,'Pipeline completed successfully')

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-job_id", type=str, help="Databricks Job ID", required=True)
        parser.add_argument("-doc_path", "--docid_csv_path", required=True)
        parser.add_argument("-mf_path", "--manifest_location", required=False, default =None)

        # get arguments
        args = parser.parse_args()
        job_id = args.job_id
        doc_id_path = args.docid_csv_path
        manifest_path = args.manifest_location

        print("arguments")
        print("job_id:", job_id)
        print("doc_id_path:", doc_id_path)
        print("manifest_path:", manifest_path)

        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,"Job_id:" + str(job_id))
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,"Doc_id_path:" + str(doc_id_path))
        LogUtil.log(LogType.TRANSACTION, LogLevel.INFO,"Manifest_path:" + str(manifest_path))
        # read data
        doc_id = pd.read_csv(doc_id_path)
        manifest = read_manifest(manifest_path)
        project_config = read_project_config(manifest)

        service_volume = project_config["project_artefacts"]["service_volume"]
        project_name = project_config["project_name"]
        version = project_config["version"]

        # log data for audit
        log_manifest(manifest, service_volume, job_id)
        log_config(project_config, service_volume, job_id)
        log_table(doc_id, service_volume, job_id)

        # start Data piepline
        print("Starting data pipeline...")
        data_pipeline = DataPipeline(project_config, doc_id_path)
        data_pipeline.run()

    except Exception as e:
        traceback.print_exc()
        set_run_failed(data_pipeline.run_id)
        print(f"Error occurred: {e}")
        LogUtil.log(LogType.APPLICATION, LogLevel.ERROR,"Error occurred:" + str(e))
        raise Exception("An error occurred, failing the pipeline. Check logs for details.\n", f"Error occurred: {e}")
