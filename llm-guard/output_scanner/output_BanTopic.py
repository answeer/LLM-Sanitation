from llm_guard.output_scanners import BanTopics

scanner = BanTopics(topics=["violence"], threshold=0.5)

model_output = "Discuss the portrayal of violence in contemporary cinema and its effects on society's perception of aggression and conflict resolution."
sanitized_output, is_valid, risk_score = scanner.scan('', model_output)


print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)