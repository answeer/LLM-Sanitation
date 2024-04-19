from llm_guard.input_scanners import Regex
from llm_guard.input_scanners.regex import MatchType

# Initialize the Regex scanner
scanner = Regex(
    patterns=[r"Bearer [A-Za-z0-9-._~+/]+"],  # List of regex patterns
    is_blocked=True,  # If True, patterns are treated as 'bad'; if False, as 'good'
    match_type=MatchType.SEARCH,  # Can be SEARCH or FULL_MATCH
    redact=True,  # Enable or disable redaction
)

# Scan a prompt
prompt = """
Bearer ssdf._!
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

print("Sanitized prompt: ", sanitized_prompt)
print("Is valid: ", is_valid)
print("Risk_score: ", risk_score)