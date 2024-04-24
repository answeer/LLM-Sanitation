from llm_guard.output_scanners import Sensitive

scanner = Sensitive(entity_types=["PERSON", "EMAIL"], redact=True)

model_output = "My email address is lijing@163.com, and my Name is Li Jing"
sanitized_output, is_valid, risk_score = scanner.scan("", model_output)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)