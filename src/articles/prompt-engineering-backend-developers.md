---
title: "Prompt Engineering for Backend Developers"
description: "A practical guide to prompt engineering for developers who work with LLM APIs — system prompts, few-shot patterns, structured outputs, and the techniques that produce reliable results in production code."
date: 2026-03-05
tags: ["AI"]
readTime: "11 min read"
---

Prompt engineering for backend developers is different from the creative prompting you see on social media. You're not trying to write poems — you're trying to get structured, reliable, deterministic outputs from an API that's fundamentally probabilistic. This guide covers the patterns that work in production code.

## The Three Layers of a Prompt

Every production prompt has three layers: the system prompt, the context, and the user instruction.

<div class="diagram-box">
┌─────────────────────────────────────────────────┐
│  SYSTEM PROMPT (sets behavior and constraints)  │
│  "You are a JSON API that classifies support    │
│   tickets. Always respond with valid JSON."     │
├─────────────────────────────────────────────────┤
│  CONTEXT (domain data, examples, retrieved docs)│
│  "Categories: billing, technical, account,      │
│   feature-request. Priority: low, medium, high" │
│  "Example: 'Can't login' → technical, high"     │
├─────────────────────────────────────────────────┤
│  USER INSTRUCTION (the actual task)             │
│  "Classify this ticket: 'My invoice shows       │
│   the wrong amount for March'"                  │
└─────────────────────────────────────────────────┘
</div>

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{context}\n\n{instruction}"},
    ],
    temperature=0,          # Deterministic output
    response_format={"type": "json_object"},
)
```

## Pattern 1: System Prompt as a Contract

The system prompt is your API contract. It defines what the model does and — critically — what it doesn't do.

```python
SYSTEM_PROMPT = """You are a ticket classification API.

ROLE: Classify customer support tickets into categories and priorities.

OUTPUT FORMAT: Always respond with valid JSON matching this schema:
{
  "category": "billing" | "technical" | "account" | "feature-request",
  "priority": "low" | "medium" | "high",
  "confidence": 0.0 to 1.0,
  "reasoning": "one sentence explaining the classification"
}

RULES:
- If the ticket mentions money, billing, charges, or invoices → category: billing
- If the ticket mentions login, errors, crashes, or bugs → category: technical
- If the ticket is ambiguous, choose the most likely category and set confidence < 0.7
- Never invent categories outside the four listed above
- Never include information not present in the ticket
"""
```

**Key principles:**
- **Be explicit about output format** — JSON schema, field names, valid values
- **Define edge cases** — what happens with ambiguous input?
- **Set boundaries** — "never invent categories," "never include information not present"
- **Keep it focused** — one task per system prompt

## Pattern 2: Few-Shot Examples

Show the model what correct output looks like. This is the single most effective technique for improving reliability.

```python
FEW_SHOT_EXAMPLES = """
EXAMPLE 1:
Ticket: "I was charged twice for my subscription this month"
Output: {"category": "billing", "priority": "high", "confidence": 0.95, "reasoning": "Double charge is a billing issue requiring urgent resolution"}

EXAMPLE 2:
Ticket: "The dashboard loads slowly when I have more than 100 items"
Output: {"category": "technical", "priority": "medium", "confidence": 0.9, "reasoning": "Performance issue in the dashboard with large datasets"}

EXAMPLE 3:
Ticket: "Can you add dark mode to the mobile app?"
Output: {"category": "feature-request", "priority": "low", "confidence": 0.95, "reasoning": "User requesting a new UI feature for the mobile application"}

EXAMPLE 4:
Ticket: "My account settings page doesn't show my updated email"
Output: {"category": "account", "priority": "medium", "confidence": 0.8, "reasoning": "Account data not reflecting recent changes, could also be technical"}
"""
```

**Guidelines for examples:**
- **3-5 examples** is the sweet spot — fewer is insufficient, more wastes tokens
- **Cover edge cases** — include an ambiguous example with lower confidence
- **Show the exact output format** — the model mirrors the pattern precisely
- **Vary the inputs** — different lengths, different vocabularies, different categories

## Pattern 3: Structured Output Enforcement

Don't hope the model returns valid JSON. **Force it.**

```python
from pydantic import BaseModel, Field
from enum import Enum

class Category(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature-request"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TicketClassification(BaseModel):
    category: Category
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(max_length=200)

# OpenAI structured outputs
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": ticket_text},
    ],
    response_format=TicketClassification,
)

result = response.choices[0].message.parsed
# result.category is guaranteed to be a valid Category enum
```

With structured outputs, invalid JSON is **impossible**. The model is constrained to only produce valid tokens matching your schema.

## Pattern 4: Chain of Thought for Complex Reasoning

When the task requires reasoning, ask the model to think step-by-step before giving the final answer.

```python
SYSTEM_PROMPT = """You are a code review assistant that identifies security vulnerabilities.

For each code snippet, follow this process:
1. IDENTIFY what the code does (2-3 sentences)
2. LIST potential security concerns (bullet points)
3. CLASSIFY each concern as: critical, warning, or info
4. PROVIDE a fixed version of the code if critical issues exist

Format your response as JSON:
{
  "summary": "what the code does",
  "concerns": [
    {"issue": "description", "severity": "critical|warning|info", "line": 0}
  ],
  "fixed_code": "corrected code or null if no critical issues",
  "overall_risk": "low|medium|high"
}
"""
```

The explicit step-by-step process produces more accurate analysis than "find security vulnerabilities."

## Pattern 5: Prompt Templates with Variables

Build prompts programmatically. Never concatenate strings manually.

```python
from string import Template

REVIEW_TEMPLATE = Template("""
Review the following $language code for $review_type issues.

File: $filename
Context: This file is part of a $project_type that handles $domain.

```
$code
```

Focus on:
$focus_areas

Respond with JSON matching the review schema.
""")

prompt = REVIEW_TEMPLATE.substitute(
    language="Python",
    review_type="security",
    filename="auth/login.py",
    project_type="web API",
    domain="user authentication",
    code=file_content,
    focus_areas="- SQL injection\n- Authentication bypass\n- Credential handling",
)
```

## Pattern 6: Retry with Reformulation

When the model fails, don't just retry — reformulate.

```python
async def classify_with_retry(ticket: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = await classify_ticket(ticket)
            parsed = TicketClassification.model_validate_json(result)
            return parsed
        except ValidationError as e:
            if attempt == max_retries - 1:
                raise

            # Reformulate with the error
            result = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": ticket},
                    {"role": "assistant", "content": result},
                    {"role": "user", "content":
                        f"Your response had validation errors: {e}. "
                        f"Please fix and respond with valid JSON."},
                ],
            )
```

## Temperature and Sampling

| Temperature | Behavior | Use Case |
|------------|----------|----------|
| 0 | Deterministic (same input → same output) | Classification, extraction, structured data |
| 0.3-0.5 | Slight variation, mostly consistent | Summarization, code review |
| 0.7-1.0 | Creative, varied responses | Content generation, brainstorming |

**For backend APIs, use temperature 0.** You want the same ticket to get the same classification every time.

## Common Mistakes

1. **Vague system prompts** — "You are a helpful assistant" tells the model nothing useful
2. **No output format specification** — hoping for JSON without specifying the schema
3. **Temperature too high** — creative randomness is the enemy of reliable APIs
4. **No input validation** — sending empty strings or 100K-token documents
5. **Not measuring quality** — prompt engineering without evaluation is guessing
6. **Prompt in production without tests** — create a test suite of 50+ input/expected-output pairs

## Evaluation: The Missing Step

```python
test_cases = [
    {
        "input": "I was charged $99 instead of $49",
        "expected_category": "billing",
        "expected_priority": "high",
    },
    {
        "input": "App crashes when uploading files over 10MB",
        "expected_category": "technical",
        "expected_priority": "high",
    },
]

results = []
for case in test_cases:
    output = classify_ticket(case["input"])
    results.append({
        "correct_category": output.category == case["expected_category"],
        "correct_priority": output.priority == case["expected_priority"],
    })

accuracy = sum(r["correct_category"] for r in results) / len(results)
print(f"Category accuracy: {accuracy:.1%}")
```

Run this eval suite every time you change a prompt. Prompts are code — they need tests.

*Published by the TechAI Explained Team.*
