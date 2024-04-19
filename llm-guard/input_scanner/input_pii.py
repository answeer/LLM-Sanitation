from llm_guard.vault import Vault

vault = Vault()

from llm_guard.input_scanners import Anonymize
from llm_guard.input_scanners.anonymize_helpers import BERT_LARGE_NER_CONF

scanner = Anonymize(vault, preamble="Insert before prompt", allowed_names=["John Doe"], hidden_names=["Test LLC"],
                    recognizer_conf=BERT_LARGE_NER_CONF, language="en")

prompt= """
Dear Mr. John Doe,

We are pleased to inform you that your account balance with Test LLC has been updated. As of April 18, 2024, your balance is $5,000. Please let us know if you have any questions or concerns.

Sincerely,
Standard Chartered
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

print("Sanitized prompt: ", sanitized_prompt)
print("Is valid: ", is_valid)
print("Risk_score: ", risk_score)
