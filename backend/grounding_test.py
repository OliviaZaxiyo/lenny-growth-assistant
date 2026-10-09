from grounding import unverified_quotes

results = [{"content": "Madhavan: pricing is an ongoing journey. It is not like you just solve it in day one."}]
good = 'He said "pricing is an ongoing journey. It is not like you just solve it" clearly.'
bad = 'He said "If you cannot explain your pricing in one sentence it is too complex" clearly.'
print("good ->", unverified_quotes(good, results))
print("bad  ->", unverified_quotes(bad, results))