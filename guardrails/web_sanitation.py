# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import WebSanitization

# Use the Guard with the validator
guard = Guard().use(WebSanitization, on_fail="exception")

# Test passing response
guard.validate(
    """MetaAI's Llama2 is the latest in their open-source LLM series. 
    It is a powerful language model."""
)

try:
    # Test failing response
    guard.validate(
        """MetaAI's Llama2 is the latest in their open-source LLM series. 
        It is a powerful language model. <script>alert('XSS')</script>"""
    )
except Exception as e:
    print(e)
