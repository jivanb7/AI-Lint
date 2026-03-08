# AI-Lint Rules Reference

Complete guide to all 12 rules with code examples showing what each rule catches and how to fix it.

## Table of Contents

### Security (CRITICAL)
- [AIL001: Prompt Injection](#ail001-prompt-injection)
- [AIL005: Exposed API Keys](#ail005-exposed-api-keys)

### Reliability (ERROR)
- [AIL006: Missing Error Handling](#ail006-missing-error-handling)
- [AIL010: Sync Calls in Async Context](#ail010-sync-calls-in-async-context)

### Best Practices (WARNING)
- [AIL002: Unbounded Token Usage](#ail002-unbounded-token-usage)
- [AIL003: Hardcoded Model Names](#ail003-hardcoded-model-names)
- [AIL004: Missing Retry Logic](#ail004-missing-retry-logic)
- [AIL007: No Input Validation](#ail007-no-input-validation)
- [AIL008: RAG Anti-Patterns](#ail008-rag-anti-patterns)
- [AIL009: Missing Timeout](#ail009-missing-timeout)
- [AIL012: No Streaming for Long Responses](#ail012-no-streaming-for-long-responses)

### Code Hygiene (INFO)
- [AIL011: Temperature Not Set](#ail011-temperature-not-set)

---

## Security (CRITICAL)

### AIL001: Prompt Injection

User input flowing directly into LLM prompts without sanitization. This is the #1 security risk in LLM applications.

```python
# Bad -- user_input goes straight into the prompt
def summarize(user_input):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize this: {user_input}"}],
    )

# Good -- sanitize first
def summarize(user_input):
    user_input = user_input[:5000]  # Limit length
    user_input = html.escape(user_input)  # Strip injection attempts
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize this: {user_input}"}],
    )
```

### AIL005: Exposed API Keys

Hardcoded API keys, tokens, or secrets in source code. Detects OpenAI, Anthropic, xAI, Groq, and generic key patterns.

```python
# Bad -- secret in plain text
api_key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901"
client = openai.OpenAI(api_key=api_key)

# Good -- load from environment
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

---

## Reliability (ERROR)

### AIL006: Missing Error Handling

LLM API calls that aren't wrapped in `try/except`. These APIs throw `RateLimitError`, `APIError`, `Timeout`, `AuthenticationError`, and more.

```python
# Bad -- any API hiccup crashes your app
def get_answer(question):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content

# Good -- handle the inevitable failures
def get_answer(question):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": question}],
        )
        return response.choices[0].message.content
    except openai.RateLimitError:
        return "Rate limited. Please try again shortly."
    except openai.APIError as e:
        logger.error(f"API error: {e}")
        return "Something went wrong."
```

### AIL010: Sync Calls in Async Context

Synchronous blocking calls (like `time.sleep()` or sync LLM clients) inside `async` functions. This silently kills your throughput by blocking the event loop.

```python
# Bad -- blocks the entire event loop
async def handle_request(query):
    time.sleep(1)  # Freezes all concurrent requests
    response = client.chat.completions.create(  # Sync client in async context
        model="gpt-4o",
        messages=[{"role": "user", "content": query}],
    )

# Good -- use async equivalents
async def handle_request(query):
    await asyncio.sleep(1)
    response = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": query}],
    )
```

---

## Best Practices (WARNING)

### AIL002: Unbounded Token Usage

LLM calls without `max_tokens`. Without a cap, a single runaway request can burn through your entire API budget.

```python
# Bad -- no limit on response length (or cost)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
)

# Good -- explicit limit
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1024,
)
```

### AIL003: Hardcoded Model Names

Model names like `"gpt-4o"` or `"claude-sonnet-4-20250514"` scattered across your codebase. When you need to switch models, you're doing find-and-replace across dozens of files.

```python
# Bad -- hardcoded everywhere
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
)

# Good -- single source of truth
MODEL = os.getenv("MODEL_NAME", "gpt-4o")

response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
)
```

### AIL004: Missing Retry Logic

LLM API calls without any retry or backoff mechanism. Rate limits and transient failures are normal -- your code should handle them gracefully.

```python
# Bad -- one 429 and you're done
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
)

# Good -- automatic retries with backoff
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(3))
def call_llm(messages):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
```

### AIL007: No Input Validation

User input passed to LLM calls without any length or content checks. A user could send 100,000 characters and blow out your token budget.

```python
# Bad -- no validation at all
def chat(user_message):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_message}],
    )

# Good -- validate before calling
def chat(user_message):
    if not user_message or len(user_message) > 10_000:
        raise ValueError("Message must be between 1 and 10,000 characters")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_message}],
    )
```

### AIL008: RAG Anti-Patterns

Vector store retrieval calls missing result limits (`k`/`top_k`), score thresholds, or document chunking. Without these, your RAG pipeline returns too many irrelevant results and wastes tokens.

```python
# Bad -- no limit, no filtering
docs = vectorstore.similarity_search(query)

# Good -- bounded and filtered
docs = vectorstore.similarity_search(query, k=5, score_threshold=0.7)
```

### AIL009: Missing Timeout

HTTP or LLM calls without a `timeout` parameter. A hanging request can block your server indefinitely.

```python
# Bad -- waits forever if the API is slow
response = requests.post(url, json=payload)
client = openai.OpenAI()

# Good -- fail fast
response = requests.post(url, json=payload, timeout=30)
client = openai.OpenAI(timeout=60)
```

### AIL012: No Streaming for Long Responses

LLM calls with large `max_tokens` (1000+) but no `stream=True`. The user stares at a blank screen while the full response generates.

```python
# Bad -- user waits 10+ seconds for a wall of text
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    max_tokens=4000,
)

# Good -- tokens stream to the user as they're generated
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    max_tokens=4000,
    stream=True,
)
```

---

## Code Hygiene (INFO)

### AIL011: Temperature Not Set

LLM calls without an explicit `temperature` parameter. The default varies across providers, and implicit behavior leads to inconsistent results.

```python
# Bad -- relying on provider defaults (which change)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
)

# Good -- explicit about what you want
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    temperature=0.7,  # Or 0 for deterministic outputs
)
```
