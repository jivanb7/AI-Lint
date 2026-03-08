"""Example file with various AI/ML anti-patterns for AI-Lint to catch."""

import openai
import time


# AIL005: Exposed API key
api_key = "sk-abc123def456ghi789jkl012mno345pqr678"

# AIL003: Hardcoded model name + AIL006: Missing error handling
# AIL002: Unbounded tokens + AIL009: Missing timeout + AIL011: No temperature
# AIL004: Missing retry
def get_completion(user_input):
    client = openai.OpenAI(api_key=api_key)
    # AIL001: Prompt injection (user_input flows in unsanitized)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize: {user_input}"}],
    )
    return response


# AIL010: Sync in async
async def async_handler(query):
    client = openai.OpenAI()
    time.sleep(1)
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}],
        max_tokens=2000,
    )
    return response


# AIL012: No streaming for large response
def long_response():
    client = openai.OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Write a long essay"}],
            max_tokens=4000,
            temperature=0.7,
        )
        return response
    except Exception:
        pass
