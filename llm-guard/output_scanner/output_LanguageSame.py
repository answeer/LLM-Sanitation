from llm_guard.output_scanners import LanguageSame

scanner = LanguageSame()

prompt = "这是一段中文提示词。"
model_output = "This is the English output."
sanitized_output, is_valid, risk_score = scanner.scan(prompt, model_output)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)