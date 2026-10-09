from llm import LLMError, current_config, stream_chat

print("Config:", current_config())
messages = [{"role": "user", "content": "Say hello in one short sentence."}]
try:
    for piece in stream_chat(messages):
        print(piece, end="", flush=True)
    print()
except LLMError as e:
    print("LLM error:", e)