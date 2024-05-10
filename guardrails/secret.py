# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import SecretsPresent

# Setup Guard
guard = Guard().use(SecretsPresent, on_fail="fix")

# response = guard.validate(
#     """
#     def hello():
#         name = "James"
#         age = 25
#         return {"name": name, "age": age}
#     """
# )  # Validator passes

# try:
#     response = guard.validate(
#         """
#         def hello():
#             user_id = "1234"
#             user_pwd = "password1234"
#             user_api_key = "sk-xhdfgtest"
#         """
#     )  # Validator fails
# except Exception as e:
#     print(e)

text = """
red_herring = 'DEADBEEF'
id = 'YW1pYWx3YXlzZ2VuZXJhdGluZ3BheWxvYWRzd2hlbmltaHVuZ3J5b3JhbWlhbHdheXNodW5ncnk'

base64_secret = 'c2VjcmV0IG1lc3NhZ2Ugc28geW91J2xsIG5ldmVyIGd1ZXNzIG15IHBhc3N3b3Jk'
hex_secret = '8b1118b376c313ed420e5133ba91307817ed52c2'
basic_auth = 'http://username:whywouldyouusehttpforpasswords@example.com'

aws_access_key = 'AKIAIOSFODNN7EXAMPLE'
aws_secret_access_key = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
"""
# Test with a given text
output = guard.parse(
    llm_output=text,
    metadata={},
)

print(output)