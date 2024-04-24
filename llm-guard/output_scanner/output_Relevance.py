from llm_guard.output_scanners import Relevance

scanner = Relevance(threshold=0.5)

prompt = "what is the LLM guardrails?"
model_output1 = """
The term "LLM guardrails" likely refers to the set of ethical and safety measures put in place for Large Language Models (LLMs) like GPT-3, 
such as ensuring that they generate content that is aligned with ethical principles, doesn't promote harm, and respects user privacy. 
These guardrails typically involve a combination of technical measures, content moderation, and adherence to guidelines set by the developers and 
platform providers. They're essential for mitigating potential risks associated with the misuse of LLMs while maximizing their positive impact.
"""
model_output2 = """
After pushing, go to your GitHub repository's page in your web browser to verify that your changes have been pushed successfully.
Remember, always pull changes from the remote repository (git pull) before pushing to avoid conflicts with changes made by others.
If there are conflicts, resolve them locally before attempting to push again.
"""
sanitized_output, is_valid, risk_score = scanner.scan(prompt, model_output2)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)