from llm_guard.input_scanners import Gibberish
from llm_guard.input_scanners.gibberish import MatchType

# Initialize the scanner
scanner = Gibberish(match_type=MatchType.FULL)

# Prepare a test prompt
prompt = """
This is a test prompt containing some gibberish text asfdkjahf askldfhlaskdf.
"""

# Scan the prompt using the scanner
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# Print the results
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)
