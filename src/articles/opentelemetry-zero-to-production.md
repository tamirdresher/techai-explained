---
title: "OpenTelemetry from Zero to Production"
description: "A hands-on guide to instrumenting your applications with OpenTelemetry — auto-instrumentation, custom spans and metrics, collector pipelines, and deploying a full observability stack with Grafana, Prometheus, and Jaeger."
date: 2026-03-08
tags: ["DevOps"]
readTime: "14 min read"
---

OpenTelemetry (OTel) is the universal standard for observability. It gives you traces, metrics, and logs — vendor-neutral, language-agnostic, and supported by every major observability platform. But going from "install the SDK" to "debug a production incident in 30 seconds" requires understanding the full pipeline.

This guide takes you from zero instrumentation to a production-ready observability stack.

## The OpenTelemetry Architecture

<div class="diagram-box">
YOUR APPLICATION                    BACKEND
──────────────                      ───────

┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│  OTel SDK       │    │  OTel        │    │  Jaeger     │
│                 │───►│  Collector   │───►│  (Traces)   │
│  Auto-instrument│    │              │    ├─────────────┤
│  Custom spans   │    │  Receives    │    │ Prometheus  │
│  Custom metrics │    │  Processes   │───►│  (Metrics)  │
│                 │    │  Exports     │    ├─────────────┤
└─────────────────┘    └──────────────┘    │  Loki       │
                                      ───►│  (Logs)     │
                                           └──────┬──────┘
                                                  │
                                           ┌──────┴──────┐
                                           │  Grafana    │
                                           │ (Dashboards)│
                                           └─────────────┘
</div>

Three components:
1. **SDK** — instruments your code and collects telemetry
2. **Collector** — receives, processes, and exports telemetry data
3. **Backends** — store and visualize the data (Jaeger, Prometheus, Grafana)

## Step 1: Auto-Instrumentation (Node.js)

Auto-instrumentation captures traces from HTTP frameworks, database clients, and other libraries without changing your code.

```bash
npm install @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-trace-otlp-http \
  @opentelemetry/exporter-metrics-otlp-http
```

Create the instrumentation file — loaded before your app:

```typescript
// instrumentation.ts
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { Resource } from '@opentelemetry/resources';
import {
  ATTR_SERVICE_NAME,
  ATTR_SERVICE_VERSION,
} from '@opentelemetry/semantic-conventions';

const sdk = new NodeSDK({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: 'order-api',
    [ATTR_SERVICE_VERSION]: '1.2.0',
    'deployment.environment': process.env.NODE_ENV || 'development',
  }),
  traceExporter: new OTLPTraceExporter({
    url: 'http://otel-collector:4318/v1/traces',
  }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: 'http://otel-collector:4318/v1/metrics',
    }),
    exportIntervalMillis: 15000,
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': { enabled: true },
      '@opentelemetry/instrumentation-express': { enabled: true },
      '@opentelemetry/instrumentation-pg': { enabled: true },
      '@opentelemetry/instrumentation-redis': { enabled: true },
    }),
  ],
});

sdk.start();

process.on('SIGTERM', () => {
  sdk.shutdown().then(() => process.exit(0));
});
```

Start your app with instrumentation:

```bash
node --require ./instrumentation.js dist/index.js
```

That's it. Every HTTP request, database query, and Redis call is now traced automatically.

## Step 2: Auto-Instrumentation (.NET)

```bash
dotnet add package OpenTelemetry.Extensions.Hosting
dotnet add package OpenTelemetry.Instrumentation.AspNetCore
dotnet add package OpenTelemetry.Instrumentation.Http
dotnet add package OpenTelemetry.Instrumentation.SqlClient
dotnet add package OpenTelemetry.Exporter.OpenTelemetryProtocol
```

```csharp
// Program.cs
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r
        .AddService("order-api", serviceVersion: "1.2.0")
        .AddAttributes(new Dictionary<string, object>
        {
            ["deployment.environment"] = builder.Environment.EnvironmentName,
        }))
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddSqlClientInstrumentation(o => o.SetDbStatementForText = true)
        .AddOtlpExporter(o =>
        {
            o.Endpoint = new Uri("http://otel-collector:4317");
        }))
    .WithMetrics(metrics => metrics
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddRuntimeInstrumentation()
        .AddOtlpExporter(o =>
        {
            o.Endpoint = new Uri("http://otel-collector:4317");
        }));
```

## Step 3: Custom Spans and Metrics

Auto-instrumentation captures infrastructure-level telemetry. Custom instrumentation captures your business logic.

### Custom Spans (Traces)

```typescript
import { trace, SpanStatusCode } from '@opentelemetry/api';

const tracer = trace.getTracer('order-service');

async function processOrder(order: Order): Promise<ProcessedOrder> {
  return tracer.startActiveSpan('process-order', async (span) => {
    span.setAttribute('order.id', order.id);
    span.setAttribute('order.item_count', order.items.length);
    span.setAttribute('order.total', order.total);

    try {
      // Child span for inventory check
      const inventory = await tracer.startActiveSpan(
        'check-inventory',
        async (childSpan) => {
          childSpan.setAttribute('inventory.warehouse', 'us-east-1');
          const result = await inventoryService.check(order.items);
          childSpan.setAttribute('inventory.available', result.allAvailable);
          childSpan.end();
          return result;
        }
      );

      // Child span for payment
      const payment = await tracer.startActiveSpan(
        'process-payment',
        async (childSpan) => {
          childSpan.setAttribute('payment.method', order.paymentMethod);
          const result = await paymentService.charge(order.total);
          childSpan.setAttribute('payment.transaction_id', result.txId);
          childSpan.end();
          return result;
        }
      );

      span.setStatus({ code: SpanStatusCode.OK });
      return { orderId: order.id, status: 'completed' };
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
      span.recordException(error);
      throw error;
    } finally {
      span.end();
    }
  });
}
```

### Custom Metrics

```typescript
import { metrics } from '@opentelemetry/api';

const meter = metrics.getMeter('order-service');

// Counter — tracks totals
const ordersProcessed = meter.createCounter('orders.processed', {
  description: 'Total orders processed',
  unit: 'orders',
});

// Histogram — tracks distributions
const orderDuration = meter.createHistogram('orders.duration', {
  description: 'Order processing duration',
  unit: 'ms',
});

// Up-down counter — tracks current values
const activeOrders = meter.createUpDownCounter('orders.active', {
  description: 'Currently processing orders',
});

// Usage
async function processOrder(order: Order) {
  activeOrders.add(1);
  const startTime = Date.now();

  try {
    const result = await doProcessing(order);
    ordersProcessed.add(1, {
      'order.status': 'success',
      'order.type': order.type,
    });
    return result;
  } catch (err) {
    ordersProcessed.add(1, { 'order.status': 'failure' });
    throw err;
  } finally {
    orderDuration.record(Date.now() - startTime);
    activeOrders.add(-1);
  }
}
```

## Step 4: The Collector

The OTel Collector is a proxy that receives telemetry, processes it, and exports to backends.

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    send_batch_size: 1024
    timeout: 5s

  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128

  attributes:
    actions:
      - key: environment
        value: production
        action: upsert

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  prometheus:
    endpoint: 0.0.0.0:8889

  loki:
    endpoint: http://loki:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, attributes]
      exporters: [otlp/jaeger]

    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [loki]
```

<div class="diagram-box">
COLLECTOR PIPELINE

Receivers ──► Processors ──► Exporters

OTLP/gRPC ─┐   ┌─ batch ─────┐   ┌─► Jaeger (traces)
            ├──►│  memory     ├──►├─► Prometheus (metrics)
OTLP/HTTP ─┘   │  attributes │   └─► Loki (logs)
                └─────────────┘
</div>

## Step 5: Deploy the Full Stack

```yaml
# docker-compose.yml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: --config=/etc/otel-collector-config.yaml
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686" # Jaeger UI

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
```

## Production Checklist

- [ ] **Sampling** — don't trace 100% of requests in production; use tail sampling or probability sampling
- [ ] **Resource attributes** — set service name, version, and environment on every signal
- [ ] **Collector as a sidecar or DaemonSet** — don't send directly to backends from your app
- [ ] **Memory limits** — configure `memory_limiter` processor to prevent OOM
- [ ] **Alerting rules** — create Prometheus alerts for error rate spikes and latency thresholds
- [ ] **Dashboard templates** — use Grafana's RED (Rate, Error, Duration) dashboard per service

## Debugging with Traces

When a request fails, the trace shows exactly what happened:

<div class="diagram-box">
TRACE: POST /api/orders (500 Internal Server Error)

order-api ────────────────────────────────────── 342ms (ERROR)
  │
  ├─ check-inventory ────────────────── 45ms ✅
  │    └─ pg.query SELECT ... ───── 12ms ✅
  │
  ├─ process-payment ────────────────── 287ms ❌
  │    └─ http POST stripe.com ──── 285ms ❌
  │         Status: 402 Payment Required
  │         Error: Card declined
  │
  └─ (create-shipment — never reached)

ROOT CAUSE: Payment failed due to declined card.
Time to diagnose: 15 seconds (not 15 minutes).
</div>

That's the power of distributed tracing. Every request tells a story. OpenTelemetry makes sure you can read it.

*Published by the TechAI Explained Team.*
