---
title: "Event-Driven Architecture with Azure Service Bus and .NET"
description: "A hands-on guide to building event-driven systems with Azure Service Bus — covering queues, topics, dead-letter handling, and the patterns that keep production systems reliable."
date: 2026-03-11
tags: ["Azure"]
readTime: "13 min read"
---

Event-driven architecture decouples services so they communicate through events instead of direct calls. When a user places an order, the order service publishes an `OrderPlaced` event — and every service that cares (inventory, notifications, analytics) reacts independently. No one waits. No one blocks.

Azure Service Bus is the backbone for these systems in the Microsoft ecosystem. This guide shows you how to build one properly — with dead-letter handling, retry policies, and the patterns that survive production.

## Why Events Instead of API Calls?

<div class="diagram-box">
SYNCHRONOUS (API Calls)          ASYNCHRONOUS (Events)
───────────────────────          ─────────────────────

Order Service                    Order Service
    │                                │
    ├── POST /inventory/reserve      ├── Publish: OrderPlaced
    │   (waits 200ms)                │   (fire and forget)
    │                                │
    ├── POST /email/send             │
    │   (waits 150ms)                │
    │                                │
    └── POST /analytics/track   ┌────┴────┐────────┐
        (waits 100ms)           ▼         ▼        ▼
                             Inventory  Email   Analytics
Total: 450ms + coupling      (subscribe) (sub)   (sub)
If email is down → order     
fails!                       Total: ~5ms (publish only)
                             If email is down → order
                             still succeeds!
</div>

## Azure Service Bus Concepts

Before writing code, understand the two messaging patterns:

### Queues: Point-to-Point

One sender, one receiver. Each message is processed by exactly one consumer.

```
Producer ──► [  Queue  ] ──► Consumer
              msg msg msg
              (FIFO order)
```

Use for: background job processing, command execution, work distribution.

### Topics & Subscriptions: Publish-Subscribe

One publisher, many subscribers. Each subscriber gets its own copy of every message.

```
Publisher ──► [ Topic ]
                 │
         ┌───────┼───────┐
         ▼       ▼       ▼
      [Sub A] [Sub B] [Sub C]
      Email   Inventory Analytics
      Service Service  Service
```

Use for: event broadcasting, fan-out patterns, decoupling services.

## Setting Up Azure Service Bus

### Create the Infrastructure

```bash
# Create resource group and namespace
az group create --name rg-events --location eastus

az servicebus namespace create \
  --name sb-myapp \
  --resource-group rg-events \
  --sku Standard

# Create a topic with subscriptions
az servicebus topic create \
  --namespace-name sb-myapp \
  --resource-group rg-events \
  --name order-events

az servicebus topic subscription create \
  --namespace-name sb-myapp \
  --resource-group rg-events \
  --topic-name order-events \
  --name inventory-sub

az servicebus topic subscription create \
  --namespace-name sb-myapp \
  --resource-group rg-events \
  --topic-name order-events \
  --name notification-sub
```

### .NET Project Setup

```bash
dotnet new worker -n OrderProcessor
cd OrderProcessor
dotnet add package Azure.Messaging.ServiceBus
dotnet add package Microsoft.Extensions.Azure
```

## Publishing Events

### Define Your Events

```csharp
// Events/OrderPlaced.cs
public record OrderPlaced
{
    public required Guid OrderId { get; init; }
    public required Guid CustomerId { get; init; }
    public required List<OrderItem> Items { get; init; }
    public required decimal TotalAmount { get; init; }
    public required DateTimeOffset OccurredAt { get; init; }
}

public record OrderItem
{
    public required string ProductId { get; init; }
    public required int Quantity { get; init; }
    public required decimal UnitPrice { get; init; }
}
```

### Publish with Retry and Correlation

```csharp
// Services/EventPublisher.cs
public class EventPublisher : IAsyncDisposable
{
    private readonly ServiceBusSender _sender;

    public EventPublisher(ServiceBusClient client, string topicName)
    {
        _sender = client.CreateSender(topicName);
    }

    public async Task PublishAsync<T>(
        T @event,
        string correlationId,
        CancellationToken ct = default) where T : class
    {
        var message = new ServiceBusMessage(
            BinaryData.FromObjectAsJson(@event))
        {
            ContentType = "application/json",
            Subject = typeof(T).Name,
            CorrelationId = correlationId,
            MessageId = Guid.NewGuid().ToString(),
            ApplicationProperties =
            {
                ["EventType"] = typeof(T).Name,
                ["Timestamp"] = DateTimeOffset.UtcNow.ToString("O"),
            }
        };

        await _sender.SendMessageAsync(message, ct);
    }

    public async ValueTask DisposeAsync()
    {
        await _sender.DisposeAsync();
    }
}
```

### Usage in Your API

```csharp
app.MapPost("/api/orders", async (
    CreateOrderRequest request,
    OrderService orderService,
    EventPublisher events) =>
{
    var order = await orderService.CreateAsync(request);

    await events.PublishAsync(new OrderPlaced
    {
        OrderId = order.Id,
        CustomerId = request.CustomerId,
        Items = order.Items,
        TotalAmount = order.Total,
        OccurredAt = DateTimeOffset.UtcNow,
    }, correlationId: order.Id.ToString());

    return Results.Created($"/api/orders/{order.Id}", order);
});
```

## Consuming Events

### The Processor Pattern

```csharp
// Workers/InventoryWorker.cs
public class InventoryWorker : BackgroundService
{
    private readonly ServiceBusProcessor _processor;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<InventoryWorker> _logger;

    public InventoryWorker(
        ServiceBusClient client,
        IServiceScopeFactory scopeFactory,
        ILogger<InventoryWorker> logger)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
        _processor = client.CreateProcessor(
            "order-events",
            "inventory-sub",
            new ServiceBusProcessorOptions
            {
                MaxConcurrentCalls = 10,
                AutoCompleteMessages = false,
                PrefetchCount = 20,
            });
    }

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        _processor.ProcessMessageAsync += HandleMessageAsync;
        _processor.ProcessErrorAsync += HandleErrorAsync;

        await _processor.StartProcessingAsync(ct);

        // Keep running until cancellation
        await Task.Delay(Timeout.Infinite, ct);
    }

    private async Task HandleMessageAsync(
        ProcessMessageEventArgs args)
    {
        var eventType = args.Message.Subject;

        using var scope = _scopeFactory.CreateScope();
        var handler = scope.ServiceProvider
            .GetRequiredService<IEventHandler>();

        try
        {
            switch (eventType)
            {
                case nameof(OrderPlaced):
                    var order = args.Message.Body
                        .ToObjectFromJson<OrderPlaced>();
                    await handler.HandleAsync(order);
                    break;

                default:
                    _logger.LogWarning(
                        "Unknown event type: {EventType}", eventType);
                    break;
            }

            await args.CompleteMessageAsync(args.Message);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Failed to process {EventType}, attempt {Count}",
                eventType, args.Message.DeliveryCount);

            if (args.Message.DeliveryCount >= 3)
            {
                await args.DeadLetterMessageAsync(
                    args.Message,
                    "MaxRetriesExceeded",
                    ex.Message);
            }
            else
            {
                await args.AbandonMessageAsync(args.Message);
            }
        }
    }

    private Task HandleErrorAsync(ProcessErrorEventArgs args)
    {
        _logger.LogError(args.Exception,
            "Service Bus error: {Source}", args.ErrorSource);
        return Task.CompletedTask;
    }
}
```

## Dead-Letter Queue: Your Safety Net

Messages that can't be processed go to the dead-letter queue (DLQ). This prevents poison messages from blocking your entire pipeline.

<div class="diagram-box">
Normal Flow:
Publisher ──► Topic ──► Subscription ──► Consumer ──► ✓ Complete

Failure Flow (after max retries):
Publisher ──► Topic ──► Subscription ──► Consumer ──► ✗ Fail
                                            │
                                            ▼ (after 3 retries)
                                     ┌──────────────┐
                                     │ Dead-Letter   │
                                     │ Queue (DLQ)   │
                                     │               │
                                     │ Inspect, fix, │
                                     │ and replay    │
                                     └──────────────┘
</div>

### Monitoring the Dead-Letter Queue

```csharp
// Services/DeadLetterMonitor.cs
public class DeadLetterMonitor : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        var dlqReceiver = _client.CreateReceiver(
            "order-events",
            "inventory-sub",
            new ServiceBusReceiverOptions
            {
                SubQueue = SubQueue.DeadLetter,
            });

        while (!ct.IsCancellationRequested)
        {
            var messages = await dlqReceiver
                .ReceiveMessagesAsync(10, TimeSpan.FromSeconds(5), ct);

            foreach (var msg in messages)
            {
                _logger.LogWarning(
                    "DLQ message: {Subject}, Reason: {Reason}, Error: {Error}",
                    msg.Subject,
                    msg.DeadLetterReason,
                    msg.DeadLetterErrorDescription);

                // Option 1: Fix and re-publish to the main topic
                // Option 2: Store for manual inspection
                // Option 3: Alert the ops team

                await dlqReceiver.CompleteMessageAsync(msg, ct);
            }

            await Task.Delay(TimeSpan.FromMinutes(1), ct);
        }
    }
}
```

## Idempotency: Process Once, Even If Delivered Twice

Service Bus guarantees **at-least-once** delivery. Your handlers must be idempotent — processing the same message twice should produce the same result.

```csharp
public class IdempotentOrderHandler : IEventHandler
{
    private readonly IDistributedCache _cache;

    public async Task HandleAsync(OrderPlaced @event)
    {
        var messageKey = $"processed:{@event.OrderId}";

        // Check if already processed
        var existing = await _cache.GetStringAsync(messageKey);
        if (existing != null)
        {
            _logger.LogInformation(
                "Order {OrderId} already processed, skipping",
                @event.OrderId);
            return;
        }

        // Process the event
        await _inventoryService.ReserveItemsAsync(@event.Items);

        // Mark as processed (with TTL)
        await _cache.SetStringAsync(
            messageKey,
            "true",
            new DistributedCacheEntryOptions
            {
                AbsoluteExpirationRelativeToNow = TimeSpan.FromHours(24),
            });
    }
}
```

## Subscription Filters

Not every subscriber needs every message. Use SQL filters to route specific events:

```csharp
// Only receive high-value orders
await adminClient.CreateRuleAsync(
    "order-events",
    "high-value-sub",
    new CreateRuleOptions
    {
        Name = "HighValueFilter",
        Filter = new SqlRuleFilter("TotalAmount > 1000"),
    });

// Only receive specific event types
await adminClient.CreateRuleAsync(
    "order-events",
    "notification-sub",
    new CreateRuleOptions
    {
        Name = "OrderEventsOnly",
        Filter = new SqlRuleFilter(
            "Subject IN ('OrderPlaced', 'OrderCancelled')"),
    });
```

## Production Checklist

### Message Design
- [ ] Events are immutable facts (past tense: `OrderPlaced`, not `PlaceOrder`)
- [ ] Each event includes a correlation ID for tracing
- [ ] Schema versioning strategy defined (add fields, never remove)
- [ ] Message size under 256 KB (use claim-check pattern for large payloads)

### Reliability
- [ ] Dead-letter queue monitoring and alerting configured
- [ ] All handlers are idempotent
- [ ] Retry policy configured (exponential backoff)
- [ ] Circuit breaker on downstream dependencies
- [ ] Max delivery count set appropriately (default is 10)

### Observability
- [ ] Structured logging with correlation IDs
- [ ] Metrics: queue depth, processing rate, DLQ depth, latency
- [ ] Alerts on DLQ growth and processing failures
- [ ] Distributed tracing across publisher → Service Bus → consumer

### Performance
- [ ] `MaxConcurrentCalls` tuned for your workload
- [ ] `PrefetchCount` set to batch-optimize network calls
- [ ] Sessions enabled if message ordering is required
- [ ] Partitioning enabled for high-throughput scenarios

## When NOT to Use Service Bus

- **Simple fire-and-forget notifications** → use Azure Event Grid (cheaper, simpler)
- **High-throughput event streaming** → use Azure Event Hubs or Kafka (millions/sec)
- **Request-response patterns** → use HTTP/gRPC (events are one-way by design)
- **Local development only** → use an in-memory queue or RabbitMQ in Docker

Choose Service Bus when you need **reliable, transactional messaging** with dead-letter support, sessions, and enterprise-grade SLAs.

*Published by the TechAI Explained Team.*
