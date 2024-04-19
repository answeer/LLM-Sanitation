from llm_guard.input_scanners import BanTopics

# Initialize the scanner
scanner = BanTopics(topics=["violence"], threshold=0.5)

# Prepare a test prompt
prompt = """
The movie depicts a scene of intense violence where the protagonist fights against the antagonist.
"""

# Scan the prompt using the scanner
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# Print the results
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)
