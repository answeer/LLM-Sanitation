from pathlib import Path
import sys
script_path = Path(sys.argv[0])
ROOT = str(Path(script_path).parent)
sys.path.insert(0, str(Path(script_path).parent.parent.parent))

import mlflow
import os
from RAGaaS.utils.create_experiment import create_experiment
from RAGaaS.utils.create_spark_sess import get_spark, get_dbutils
spark = get_spark()
dbutils = get_dbutils(spark)

import argparse
from RAGaaS.utils.get_config import read_manifest, read_project_config, log_manifest, log_config, log_table, get_or_create_vol

class RAGInferencePipeline:
    def __init__(self, project_config):

        from RAGaaS.rag_chat import ServingEndpoint, ModelRegistry, LogModel

        run_id = create_experiment("ragaas_inference_pipeline_creation",  project_config)
        self.run_id = run_id
        self.log_model = LogModel(self.run_id, project_config)
        self.model_registry = ModelRegistry(self.run_id, project_config)
        self.serving_endpoint = ServingEndpoint(self.run_id, project_config)
        self.endpoint = ServingEndpoint(self.run_id, project_config)

        self.llm_endpoint_name = project_config["llm_model"]
        self.vs_index_name = project_config["project_artefacts"]["vs_index_name"]
        self.business_prompt = project_config["prompt_business"]
        self.fallback_message = project_config["prompt_fallback"]
        self.description = project_config["description"]

    def run(self):
        # Step 1: Log Model


        print("Logging model...")
        logged_agent_info = self.log_model.log_model(
            name="agent",
            python_model="./agent/rag_chat_agent.py",
            extra_code_paths=[
                os.path.join(ROOT,"agent","prompt_template.py"),
                os.path.join(ROOT,"agent","config.py"),
            ],
        )

        # Step 2: Register Model in UC
        print("Registering model in Unity Catalog...")
        uc_registered_model_info = self.model_registry.register_model(logged_agent_info)

        # Step 3: Create Serving Endpoint
        print("Creating serving endpoint...")
        self.endpoint.create_deployment(uc_registered_model_info)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-job_id", type=str, help="Databricks Job ID", required=True)
    parser.add_argument("-mf_path", "--manifest_location", required=False, default =None)

    # get arguments
    args = parser.parse_args()
    job_id = args.job_id
    manifest_path = args.manifest_location

    print("arguments")
    print("job_id:", job_id)
    print("manifest_path:", manifest_path)

    manifest = read_manifest(manifest_path)
    project_config = read_project_config(manifest)

    service_volume = project_config["project_artefacts"]["service_volume"]
    project_name = project_config["project_name"]
    version = project_config["version"]

    # log data for audit
    log_manifest(manifest, service_volume, job_id)
    log_config(project_config, service_volume, job_id)

    # create config.py
    llm_endpoint_name = project_config["llm_model"]
    vs_index_name = project_config["project_artefacts"]["vs_index_name"]
    business_prompt = project_config["prompt_business"]
    fallback_message = project_config["prompt_fallback"]
    description = project_config["description"]
    mlflow_experiment_nm = "ragaas"
    experiment_dir = "user"

    print("Writing configs...", os.path.join(ROOT, "agent", "config.py"))

    with open(os.path.join(ROOT, "agent", "config.py"), "w") as f:
        # f.write("llm_endpoint_name = '" + str(llm_endpoint_name) + "'\n")
        # f.write("vs_index_name = '" + str(vs_index_name) + "'\n")
        # f.write("business_prompt = '" + str(business_prompt) + "'\n")
        # f.write("fallback_message = '" + str(fallback_message) + "'\n")
        # f.write("description = '" + str(description) + "'\n")

        f.write(f"llm_endpoint_name = {repr(llm_endpoint_name)}\n")
        f.write(f"vs_index_name = {repr(vs_index_name)}\n")
        f.write("business_prompt = '''" + business_prompt + "'''\n")
        f.write("fallback_message = '''" + fallback_message + "'''\n")
        f.write("description = '''" + description + "'''\n")
        f.write("mlflow_experiment_nm = '''" + mlflow_experiment_nm + "'''\n")
        f.write("experiment_dir = '''" + experiment_dir + "'''\n")

    pipeline = RAGInferencePipeline(project_config)
    pipeline.run()
    print("RAG Inference Pipeline completed successfully.")
