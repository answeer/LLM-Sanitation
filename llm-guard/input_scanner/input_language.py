from llm_guard.input_scanners import Language
from llm_guard.input_scanners.language import MatchType

# Initialize the scanner
scanner = Language(valid_languages=["en"], match_type=MatchType.FULL)  # Add other valid language codes (ISO 639-1) as needed

# Prepare a test prompt
prompt = """
这是一段中文提示词。
"""

# Scan the prompt using the scanner
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# Print the results
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)
