import csv
import yaml
import os
from llm_guard import scan_prompt, scan_output
from llm_guard.input_scanners import (
    Anonymize,
    BanCompetitors,
    BanTopics,
    Code,
    Gibberish,
    Language,
    PromptInjection,
    Toxicity,
    InvisibleText,
    Sentiment,
    TokenLimit,
    Secrets,
)
from llm_guard.output_scanners import (
    Bias,
    LanguageSame,
    NoRefusal,
    FactualConsistency,
    Relevance,
    URLReachability,
)
from llm_guard.vault import Vault

class LLMGuard:
    def __init__(self, input_file, output_path, config_file):
        self.input_file = input_file
        self.output_path = output_path
        self.config_file = config_file
        self.vault = Vault()
        os.makedirs(self.output_path,exist_ok=True)

    def run(self):
        self.load_config()
        self.scan_input()
        self.scan_output()

    def load_config(self):
        with open(self.config_file, 'r', encoding='utf-8') as config_file:
            self.config = yaml.safe_load(config_file)

    def scan_input(self):
        input_columns = self.config.get('input_columns', [])
        input_scanners = [
                Anonymize(self.vault),
                BanTopics(topics=self.config['ban_topics']),
                BanCompetitors(competitors=self.config['ban_competitors']),
                Toxicity(),
                Code(languages=self.config['code_languages']),
                Gibberish(),
                Language(valid_languages=self.config['valid_languages']),
                PromptInjection(),
                InvisibleText(),
                Sentiment(),
                TokenLimit(),
                Secrets(),
            ]
        with open(self.input_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                rows = list(reader)
        new_columns = [scanner.__class__.__name__ for scanner in input_scanners] + ['sanitized_prompt']

        for col in input_columns:
            output_file = os.path.join(self.output_path,f"{col}_output.csv")

            with open(output_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=reader.fieldnames + new_columns)
                writer.writeheader()

                for row in rows:
                    input_prompt = row[col]
                    sanitized_prompt, results_valid, _ = scan_prompt(input_scanners, input_prompt)
                    
                    for scanner in input_scanners:
                        scanner_name = scanner.__class__.__name__
                        row[scanner_name] = results_valid.get(scanner_name, None)
                    
                    row['sanitized_prompt'] = sanitized_prompt
                    writer.writerow(row)

    def scan_output(self):
        output_columns = self.config.get('output_columns', [])
        if len(output_columns) < 2:
            print("output scanner need at least tow contents")
            return

        output_scanners = [
            Bias(),
            LanguageSame(),
            NoRefusal(),
            FactualConsistency(),
            Relevance(),
            URLReachability(),
        ]

        with open(self.input_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)

        for i in range(len(output_columns) - 1):
            for j in range(i + 1, len(output_columns)):
                input_scanners = output_scanners[:]

                output_file = os.path.join(self.output_path,f"{output_columns[i]}_{output_columns[j]}_output.csv")

                with open(output_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=reader.fieldnames + [scanner.__class__.__name__ for scanner in input_scanners] + ['sanitized_prompt'])
                    writer.writeheader()

                    for row in rows:
                        input_prompt = row[output_columns[i]]
                        model_output = row[output_columns[j]]
                        sanitized_prompt, results_valid, _ = scan_output(input_scanners, input_prompt, model_output)
                        
                        for scanner in input_scanners:
                            scanner_name = scanner.__class__.__name__
                            row[scanner_name] = results_valid.get(scanner_name, None)
                        
                        row['sanitized_prompt'] = sanitized_prompt
                        writer.writerow(row)

# Usage
if __name__ == "__main__":
    llm_guard = LLMGuard(input_file='input.csv', output_path='output', config_file='config.yaml')
    llm_guard.run()
    print("Processed results saved to separate CSV files based on columns specified in the config.")
