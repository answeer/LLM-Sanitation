from llm_guard.input_scanners import BanCompetitors

# Define a list of competitors
competitor_list = ["Competitor1", "CompetitorOne", "C1", ...]  # Extensive list of competitors
# Initialize the scanner
scanner = BanCompetitors(competitors=competitor_list, redact=False, threshold=0.5)

# Prepare a test prompt
prompt = """
Our product has significant advantages compared to Competitor1's product. Not only is the price lower, but also the performance is better.
"""

# Scan the prompt using the scanner
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# Print the results
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)
