---
title: "Distributed Tracing: Following a Request Across 12 Services"
description: "A video script demonstrating how distributed tracing works in production — trace propagation, span hierarchies, and using traces to debug real incidents across a microservice architecture."
date: 2026-03-10
tags: ["Video Script"]
---

## Video Metadata

- **Target Duration:** 9 minutes
- **Format:** Animated trace diagrams + live Jaeger/Grafana Tempo demo + architecture walkthrough
- **Audience:** Backend developers working with microservices who need to debug cross-service issues
- **Thumbnail Concept:** A glowing line threading through 12 connected service boxes — text "Follow ONE Request Through 12 Services"

---

## Script Outline

### INTRO (0:00 - 1:00)

**Hook (0:00 - 0:25)**

> "A user clicks 'Place Order.' That single click triggers 12 services, 3 databases, 2 message queues, and an external payment API. When it fails, where do you look? Logs from 12 services? Good luck. Distributed tracing lets you follow that ONE request across every service it touches. Let me show you how."

**Visual:** Animated request entering the system, bouncing through 12 service boxes with a glowing trace line connecting them all.

---

### SECTION 1: What Is a Distributed Trace? (1:00 - 2:30)

**Core concepts:**

> "A trace is the complete journey of a single request. It's made up of spans — each span represents one operation in one service. Spans have parent-child relationships that form a tree."

**Visual — trace waterfall:**

```
TRACE: Place Order (trace_id: abc123)
│
├─ api-gateway ──────────────────────────────── 450ms
│  │
│  ├─ auth-service: verify-token ──── 12ms
│  │
│  └─ order-service: create-order ─────────── 430ms
│     │
│     ├─ inventory: check-stock ────── 35ms
│     │  └─ postgres: SELECT ──── 8ms
│     │
│     ├─ pricing: calculate-total ──── 22ms
│     │  └─ redis: GET cache ──── 1ms
│     │
│     ├─ payment: charge ──────────── 285ms
│     │  └─ stripe-api: POST ──── 280ms
│     │
│     ├─ notification: send-email ──── 45ms
│     │  └─ sendgrid: POST ──── 40ms
│     │
│     └─ analytics: track-event ──── 5ms
│        └─ kafka: produce ──── 2ms
```

**Key terms:**
- **Trace** = the entire journey (one trace ID)
- **Span** = one operation within one service
- **Context propagation** = passing the trace ID between services

---

### SECTION 2: How Context Propagation Works (2:30 - 4:00)

> "The magic of tracing is context propagation. When Service A calls Service B, it passes a special header — `traceparent` — that contains the trace ID and the current span ID. Service B creates a child span under that parent."

**Visual — header propagation:**

```
Service A                    Service B
─────────                    ─────────
Creates span (id: span-1)
                    HTTP Request ──►
                    Headers:
                    traceparent: 00-abc123-span1-01
                                    │        │
                                    │        └─ parent span
                                    └─ trace ID

                    Service B reads traceparent
                    Creates child span (id: span-2, parent: span-1)
                    ◄── HTTP Response
```

**The W3C Trace Context standard:**

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             │   │                                │                 │
             │   trace-id (128-bit)               parent-id        flags
             version                              (64-bit)         (sampled)
```

> "This header travels with every HTTP call, message queue event, and gRPC call. Every service adds its own span to the trace. When you view the trace in Jaeger, you see the complete picture."

---

### SECTION 3: Live Demo — Debugging a Slow Request (4:00 - 6:00)

> "Let me show you a real trace from a production-like system."

**Demo walkthrough:**

**Step 1:** Open Jaeger UI, search for traces on the order service, filter by duration > 2 seconds.

**Step 2:** Click on a slow trace — 3.2 seconds total.

**Step 3:** Walk through the waterfall:

> "Look at this trace. The total request took 3.2 seconds. Let's find the bottleneck. API gateway — 5ms, fine. Auth service — 10ms, fine. Order service — it called inventory, pricing, payment, and notification. Inventory — 30ms. Pricing — 15ms. Payment — 2.8 SECONDS. There's our problem."

> "Drill into the payment span. It called Stripe's API. The Stripe call took 2.8 seconds. Check the span attributes — retry count: 3. The first two attempts timed out, the third succeeded. Now we know: Stripe had a latency spike, our retry logic worked but made the overall request slow."

**Step 4:** Show how to set an alert for payment latency > 1 second.

---

### SECTION 4: Instrumenting Your Services (6:00 - 7:30)

**Auto-instrumentation:**

> "Most frameworks have auto-instrumentation. In Node.js, one package captures HTTP, database, and cache spans automatically. In .NET, AddOpenTelemetry with ASP.NET Core instrumentation does the same."

**Custom spans for business logic:**

```python
from opentelemetry import trace

tracer = trace.get_tracer("order-service")

def process_order(order):
    with tracer.start_as_current_span("process-order") as span:
        span.set_attribute("order.id", order.id)
        span.set_attribute("order.total", order.total)

        with tracer.start_as_current_span("validate-order"):
            validate(order)

        with tracer.start_as_current_span("reserve-inventory"):
            reserve(order.items)

        with tracer.start_as_current_span("charge-payment"):
            charge(order.payment_method, order.total)
```

> "Auto-instrumentation gives you the infrastructure view — HTTP calls, database queries, cache hits. Custom spans give you the BUSINESS view — order processing, inventory reservation, payment charging."

---

### SECTION 5: Production Tips (7:30 - 8:30)

**Sampling:**

> "Don't trace 100% of requests in production. Use tail-based sampling: capture all traces, but only STORE the interesting ones — errors, slow requests, and a random sample of normal traffic."

**Span attributes:**

> "Add business context to spans: order ID, customer tier, product category. When debugging, you don't just want to know WHICH service was slow — you want to know which ORDER, which CUSTOMER, which PRODUCT caused the issue."

**Connecting traces to logs:**

> "Include the trace ID in your log messages. When you find a problematic trace, you can search your logs for that trace ID and get the full picture — structured logs PLUS the visual trace timeline."

```json
{
  "timestamp": "2026-03-10T14:22:01Z",
  "level": "ERROR",
  "message": "Payment failed: card declined",
  "trace_id": "abc123def456",
  "span_id": "span789",
  "order_id": "ORD-4521",
  "service": "payment-service"
}
```

---

### OUTRO (8:30 - 9:00)

> "Distributed tracing turns a 'something is slow' mystery into a 'the Stripe API had a latency spike at 2:14 PM and our retry logic added 2.8 seconds to order processing' answer. Start with auto-instrumentation, add custom spans for your business logic, and connect your traces to your logs. Subscribe for the next video where we build a complete observability stack from scratch."

**End Screen:** Two suggested videos.

---

## Production Notes

- **B-Roll:** Jaeger waterfall view, Grafana Tempo trace search, code editor with span instrumentation
- **Live demo:** Use a pre-built demo environment with intentional latency injected into one service
- **Graphics:** Trace waterfall animations, context propagation flow, W3C header breakdown
- **Music:** Investigative, detective-style — we're following clues
- **SEO Tags:** distributed tracing, OpenTelemetry, Jaeger, observability, microservices debugging, trace context, span, tracing tutorial

*Script by the TechAI Explained Team.*
