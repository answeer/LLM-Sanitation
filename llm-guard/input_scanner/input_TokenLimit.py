from llm_guard.input_scanners import TokenLimit

scanner = TokenLimit(limit=100, encoding_name="cl100k_base")

prompt = """
The tumultuous tempest of existential angst, swirling like a relentless vortex within the depths of my weary soul, engulfs me in an 
overwhelming deluge of despair and desolation, as if the very fabric of reality conspires to suffocate my hopes and dreams beneath 
its crushing weight, leaving me adrift in a vast and unforgiving sea of uncertainty and disillusionment, where every flicker of optimism 
is extinguished by the icy tendrils of doubt and regret, and every fleeting moment of solace is shattered by the relentless onslaught of 
existential dread, until I am left to wander aimlessly amidst the ruins of my shattered aspirations, haunted by the echoes of what could 
have been, but now shall never be, a mere specter of the person I once dared to imagine myself becoming, lost amidst the vast expanse of 
the abyss, forevermore.
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

print("Sanitized prompt: ", sanitized_prompt)
print("Is valid: ", is_valid)
print("Risk_score: ", risk_score)