from llm_guard.output_scanners import URLReachability

scanner = URLReachability(success_status_codes=[200, 201, 202, 301, 302], timeout=1)

model_output = "The site of llm-guard is : https://llm-guard.com"
sanitized_output, is_valid, risk_score = scanner.scan("", model_output)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)