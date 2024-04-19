import pyperclip
def convert_to_tag_chars(input_string):
 return ''.join(chr(0xE0000 + ord(ch)) for ch in input_string)

# Example usage:
user_input = input("Enter a string to convert to tag characters: ")
tagged_output = convert_to_tag_chars(user_input)
print("Tagged output:", tagged_output)
pyperclip.copy(tagged_output)




from llm_guard.input_scanners import InvisibleText

scanner = InvisibleText()
prompt = tagged_output
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)