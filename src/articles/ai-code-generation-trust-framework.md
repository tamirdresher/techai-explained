---
title: "AI Code Generation: When to Trust It and When to Rewrite"
description: "A practical framework for evaluating AI-generated code — covering the trust spectrum, the five categories where AI excels, and the red flags that mean you should rewrite from scratch."
date: 2026-03-09
tags: ["AI"]
readTime: "10 min read"
---

AI code generation has reached an inflection point. The tooling is good enough that rejecting it entirely makes you slower. But trusting it blindly fills your codebase with subtle bugs, security holes, and unmaintainable patterns. The skill that matters now isn't whether you use AI to generate code — it's knowing **when to accept, when to modify, and when to rewrite**.

This guide provides a practical decision framework based on real-world patterns.

## The Trust Spectrum

Not all AI-generated code deserves the same level of scrutiny. Place every generation on this spectrum:

<div class="diagram-box">
LOW RISK                                          HIGH RISK
────────────────────────────────────────────────────────────
Accept      Review       Modify       Scrutinize    Rewrite
as-is       quickly      parts        line-by-line   entirely

│           │            │            │              │
Boilerplate Tests        Business     Security       Crypto,
CRUD ops    Utilities    logic        Auth/AuthZ     Financial
Config      Adapters     API design   Data access    Compliance
Formatting  Conversions  State mgmt   Input parsing  Legal logic
</div>

## Category 1: Accept As-Is (Boilerplate & Config)

AI excels at generating code you'd copy from documentation or Stack Overflow anyway. There's minimal risk because the patterns are well-established and easily verified.

### Examples That AI Nails

```typescript
// Express server setup — accept as-is
import express from 'express';
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors({ origin: process.env.ALLOWED_ORIGINS?.split(',') }));
app.listen(process.env.PORT || 3000);
```

```yaml
# Docker Compose for local dev — accept as-is
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```csharp
// DTO mapping — accept as-is
public static OrderResponse ToResponse(this Order order) => new()
{
    Id = order.Id,
    CustomerName = order.Customer.Name,
    Items = order.Items.Select(i => new OrderItemResponse
    {
        ProductName = i.Product.Name,
        Quantity = i.Quantity,
        UnitPrice = i.UnitPrice,
    }).ToList(),
    Total = order.Total,
    CreatedAt = order.CreatedAt,
};
```

**Why it's safe:** These patterns are deterministic. There's one right way to set up an Express server or write a DTO mapper. The AI has seen millions of examples. Verify it compiles, move on.

## Category 2: Review Quickly (Tests & Utilities)

AI generates decent test code and utility functions, but common issues include: incomplete edge cases, wrong assertions, and outdated API usage.

```typescript
// AI-generated test — review for completeness
describe('calculateDiscount', () => {
  it('applies 10% discount for orders over $100', () => {
    expect(calculateDiscount(150)).toBe(15);
  });

  it('applies no discount for orders under $100', () => {
    expect(calculateDiscount(50)).toBe(0);
  });

  it('handles zero amount', () => {
    expect(calculateDiscount(0)).toBe(0);
  });

  // ⚠️ AI often MISSES these:
  // - Negative amounts
  // - Boundary value ($100 exactly)
  // - Non-numeric input
  // - Very large numbers (overflow)
});
```

**Review checklist for AI tests:**
- [ ] Boundary values tested (off-by-one is AI's most common bug)
- [ ] Error cases included (null, undefined, negative, overflow)
- [ ] Assertions are correct (not just `toBeTruthy()`)
- [ ] Test descriptions match what's actually being tested
- [ ] No hardcoded values that should be constants

## Category 3: Modify Parts (Business Logic)

AI can scaffold business logic, but it makes assumptions about your domain that are often wrong. Accept the structure, rewrite the details.

```typescript
// AI-generated order processing — NEEDS MODIFICATION
async function processOrder(order: Order): Promise<ProcessedOrder> {
  // ✅ Structure is good
  validateOrder(order);
  const inventory = await checkInventory(order.items);
  const payment = await chargePayment(order.total, order.paymentMethod);
  const shipment = await createShipment(order);

  return {
    orderId: order.id,
    status: 'completed',
    trackingNumber: shipment.tracking,
  };
}

// ⚠️ Problems:
// 1. No transaction/saga pattern — if shipment fails, payment isn't refunded
// 2. No idempotency check — processing the same order twice charges twice
// 3. Inventory check and reservation are separate — race condition
// 4. No partial fulfillment logic — what if only some items are in stock?
// 5. Error handling is missing entirely
```

**The fix pattern:** Keep the function signature and flow. Add the domain-specific error handling, transaction management, and edge cases that AI doesn't know about.

## Category 4: Scrutinize Line-by-Line (Security & Data Access)

AI-generated security code and database queries require the highest scrutiny. The code often **looks** correct but has subtle vulnerabilities.

### SQL Injection — AI Gets This Wrong More Than You'd Think

```python
# AI-generated — LOOKS fine but has issues
def search_users(query: str, role: str = None):
    sql = "SELECT * FROM users WHERE name ILIKE %s"
    params = [f"%{query}%"]

    if role:
        sql += f" AND role = '{role}'"  # 💀 SQL INJECTION!
        # AI parameterized the first value but not the second

    return db.execute(sql, params)
```

### Auth Logic — Subtle Bugs

```typescript
// AI-generated auth middleware — SCRUTINIZE CAREFULLY
async function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'No token' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid token' });
  }
}

// ⚠️ Issues AI commonly introduces:
// 1. No algorithm restriction — vulnerable to 'none' algorithm attack
// 2. No audience/issuer validation
// 3. Token from header only — what about cookies?
// 4. No token revocation check
// 5. Error message might leak information

// CORRECT version:
const decoded = jwt.verify(token, process.env.JWT_SECRET, {
  algorithms: ['HS256'],     // Restrict algorithms
  audience: 'my-app',        // Validate audience
  issuer: 'auth.my-app.com', // Validate issuer
});
```

### The Security Review Checklist for AI Code

- [ ] All user inputs are parameterized/escaped
- [ ] Authentication checks validate algorithm, audience, and issuer
- [ ] Authorization checks are present (not just authentication)
- [ ] Secrets are not hardcoded or logged
- [ ] Error messages don't leak internal details
- [ ] Rate limiting is applied to sensitive endpoints
- [ ] CORS is configured restrictively, not `*`

## Category 5: Rewrite Entirely (Crypto, Financial, Compliance)

Some code should never be accepted from AI generation. Period.

### Code You Should Always Write Yourself

1. **Cryptographic implementations** — AI will suggest patterns that look correct but have timing attacks, weak random number generation, or deprecated algorithms
2. **Financial calculations** — floating-point errors in currency math create real liability
3. **Compliance logic** — GDPR data retention, HIPAA access controls, SOX audit trails
4. **Security-critical parsers** — XML/JSON parsers that handle untrusted input
5. **Consensus algorithms** — distributed systems coordination logic

> If the bug causes a security breach, financial loss, or regulatory violation — don't trust AI-generated code. Write it. Review it. Test it. Then have someone else review it.

## The Decision Framework

When AI generates code, ask these five questions:

<div class="diagram-box">
1. BLAST RADIUS: If this code has a bug, what's the worst outcome?
   Low (UI glitch) ──────────────────── High (data breach)

2. DOMAIN SPECIFICITY: How unique is this to MY application?
   Generic (CRUD, config) ──────────── Specific (business rules)

3. VERIFIABILITY: Can I quickly verify this is correct?
   Easy (run tests) ────────────────── Hard (needs prod data)

4. SECURITY SURFACE: Does this handle untrusted input?
   No (internal service) ───────────── Yes (user-facing API)

5. REGULATORY IMPACT: Does this affect compliance?
   No ──────────────────────────────── Yes (audit, legal)

Score each 1-5. Total > 15? Rewrite. Total < 10? Accept.
</div>

## Practical Workflow

Here's the workflow that maximizes AI productivity while minimizing risk:

### Step 1: Generate with Context

Give the AI maximum context — relevant files, types, conventions. Vague prompts produce generic code.

```
❌ "Write a user service"
✅ "Write a UserService class that uses the existing UserRepository 
    (see src/repos/user.repo.ts) to implement getById, create, and 
    update. Follow the error handling pattern in OrderService. Use 
    Zod for input validation."
```

### Step 2: Categorize Before Reading

Before reading the generated code, determine which category it falls into. This sets your review depth.

### Step 3: Test First

Run the generated code against tests before reading it line by line. If tests pass, you've reduced the review surface. If they fail, you know exactly where to look.

### Step 4: Check for AI's Common Mistakes

Regardless of category, check for these patterns:
- **Hallucinated APIs** — methods or packages that don't exist
- **Outdated patterns** — training data cutoff means AI suggests deprecated approaches
- **Missing error handling** — AI optimizes for the happy path
- **Incorrect types** — especially in TypeScript, types are often `any` or wrong
- **Copy-paste-itis** — repeated code that should be abstracted

## The Bottom Line

AI code generation is a tool, not a teammate. It doesn't understand your business domain, your security requirements, or your production environment. It understands patterns.

Use it for patterns. Verify it for logic. Rewrite it for security. And always, always test what it gives you.

*Published by the TechAI Explained Team.*
