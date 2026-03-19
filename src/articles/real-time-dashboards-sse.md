---
title: "Building Real-Time Dashboards with Server-Sent Events"
description: "A hands-on tutorial for building live-updating dashboards using Server-Sent Events — with a Node.js backend, vanilla JavaScript frontend, and production patterns for reconnection and scaling."
date: 2026-03-04
tags: ["Architecture"]
readTime: "10 min read"
---

Real-time dashboards show data the instant it changes — no refresh button, no polling intervals. Server-Sent Events (SSE) is the simplest way to build them. It's native to every browser, works through every proxy, and requires zero client-side libraries.

This tutorial builds a live metrics dashboard from scratch.

## What We're Building

<div class="diagram-box">
┌──────────────────────────────────────────────────┐
│              LIVE METRICS DASHBOARD              │
│                                                  │
│  Active Users: 1,247 ▲         Requests/sec: 842│
│  Error Rate:   0.3%  ▼         P95 Latency: 45ms│
│                                                  │
│  ┌──────────────────────────────────────┐        │
│  │ Live Request Log                     │        │
│  │ 10:42:01 GET  /api/orders    12ms ✅ │        │
│  │ 10:42:01 POST /api/users     45ms ✅ │        │
│  │ 10:42:02 GET  /api/search   203ms ⚠️ │        │
│  │ 10:42:02 GET  /api/orders    8ms  ✅ │        │
│  └──────────────────────────────────────┘        │
│                                                  │
│  All data updates in real-time via SSE           │
│  No WebSocket. No polling. No libraries.         │
└──────────────────────────────────────────────────┘
</div>

## The Server: Node.js + Express

### Basic SSE Endpoint

```typescript
import express from 'express';

const app = express();
app.use(express.static('public'));

// Track connected clients
const clients: Set<express.Response> = new Set();

app.get('/events', (req, res) => {
  // SSE headers
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',  // Disable NGINX buffering
  });

  // Send initial connection event
  res.write(`event: connected\ndata: ${JSON.stringify({
    time: new Date().toISOString()
  })}\n\n`);

  // Register this client
  clients.add(res);
  console.log(`Client connected. Total: ${clients.size}`);

  // Remove on disconnect
  req.on('close', () => {
    clients.delete(res);
    console.log(`Client disconnected. Total: ${clients.size}`);
  });
});

// Broadcast to all connected clients
function broadcast(event: string, data: object) {
  const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  clients.forEach(client => client.write(message));
}

app.listen(3000, () => console.log('Dashboard server on :3000'));
```

### Generating Metrics

```typescript
// Simulate real-time metrics (replace with actual data sources)
setInterval(() => {
  broadcast('metrics', {
    activeUsers: Math.floor(1200 + Math.random() * 100),
    requestsPerSec: Math.floor(800 + Math.random() * 100),
    errorRate: (Math.random() * 0.8).toFixed(2),
    p95Latency: Math.floor(30 + Math.random() * 40),
    timestamp: Date.now(),
  });
}, 1000);

// Simulate request log entries
setInterval(() => {
  const methods = ['GET', 'POST', 'PUT', 'DELETE'];
  const paths = ['/api/orders', '/api/users', '/api/search', '/api/products'];
  const statusCodes = [200, 200, 200, 200, 200, 201, 400, 500];

  broadcast('request', {
    method: methods[Math.floor(Math.random() * methods.length)],
    path: paths[Math.floor(Math.random() * paths.length)],
    status: statusCodes[Math.floor(Math.random() * statusCodes.length)],
    duration: Math.floor(Math.random() * 200),
    timestamp: Date.now(),
  });
}, 200);
```

## The Client: Vanilla JavaScript

### Connecting to SSE

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Live Dashboard</title>
  <style>
    body { font-family: monospace; background: #0d1117; color: #e6edf3; padding: 2rem; }
    .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
    .metric { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.5rem; }
    .metric .value { font-size: 2rem; font-weight: bold; color: #58a6ff; }
    .metric .label { color: #8b949e; font-size: 0.9rem; }
    .log { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; max-height: 400px; overflow-y: auto; }
    .log-entry { padding: 0.3rem 0; border-bottom: 1px solid #21262d; font-size: 0.85rem; }
    .status-ok { color: #3fb950; }
    .status-err { color: #f85149; }
    .status-warn { color: #d29922; }
    #connection-status { margin-bottom: 1rem; }
    .connected { color: #3fb950; }
    .disconnected { color: #f85149; }
  </style>
</head>
<body>
  <h1>⚡ Live Dashboard</h1>
  <div id="connection-status" class="connected">● Connected</div>

  <div class="metrics">
    <div class="metric"><div class="value" id="active-users">—</div><div class="label">Active Users</div></div>
    <div class="metric"><div class="value" id="rps">—</div><div class="label">Requests/sec</div></div>
    <div class="metric"><div class="value" id="error-rate">—</div><div class="label">Error Rate</div></div>
    <div class="metric"><div class="value" id="p95">—</div><div class="label">P95 Latency</div></div>
  </div>

  <h2>Live Request Log</h2>
  <div class="log" id="request-log"></div>

  <script>
    const statusEl = document.getElementById('connection-status');
    const logEl = document.getElementById('request-log');

    function connect() {
      const source = new EventSource('/events');

      source.addEventListener('connected', (e) => {
        statusEl.textContent = '● Connected';
        statusEl.className = 'connected';
      });

      source.addEventListener('metrics', (e) => {
        const data = JSON.parse(e.data);
        document.getElementById('active-users').textContent = data.activeUsers.toLocaleString();
        document.getElementById('rps').textContent = data.requestsPerSec;
        document.getElementById('error-rate').textContent = data.errorRate + '%';
        document.getElementById('p95').textContent = data.p95Latency + 'ms';
      });

      source.addEventListener('request', (e) => {
        const data = JSON.parse(e.data);
        const time = new Date(data.timestamp).toLocaleTimeString();
        const statusClass = data.status < 300 ? 'status-ok' :
                           data.status < 500 ? 'status-warn' : 'status-err';
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = `<span>${time}</span> `
          + `<span>${data.method.padEnd(6)}</span> `
          + `<span>${data.path.padEnd(20)}</span> `
          + `<span>${String(data.duration).padStart(4)}ms</span> `
          + `<span class="${statusClass}">${data.status}</span>`;
        logEl.prepend(entry);

        // Keep only last 100 entries
        while (logEl.children.length > 100) logEl.removeChild(logEl.lastChild);
      });

      source.onerror = () => {
        statusEl.textContent = '● Reconnecting...';
        statusEl.className = 'disconnected';
        // EventSource auto-reconnects — no manual code needed!
      };
    }

    connect();
  </script>
</body>
</html>
```

**Key point:** `EventSource` auto-reconnects when the connection drops. No retry logic, no exponential backoff — the browser handles it natively.

## Production Patterns

### Pattern 1: Event ID for Resume

If the connection drops, the client can resume from where it left off using `Last-Event-ID`:

```typescript
// Server: include event IDs
let eventCounter = 0;

function broadcast(event: string, data: object) {
  eventCounter++;
  const message = `id: ${eventCounter}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  clients.forEach(client => client.write(message));
}

// On reconnect, the browser sends Last-Event-ID header
app.get('/events', (req, res) => {
  const lastId = parseInt(req.headers['last-event-id'] || '0');

  // Send any missed events since lastId
  missedEvents
    .filter(e => e.id > lastId)
    .forEach(e => res.write(`id: ${e.id}\nevent: ${e.event}\ndata: ${e.data}\n\n`));
  // Then continue with live events...
});
```

### Pattern 2: Heartbeat Keep-Alive

Proxies and load balancers may close idle connections. Send a heartbeat:

```typescript
// Server: send a comment (ignored by EventSource) every 15s
setInterval(() => {
  clients.forEach(client => client.write(': heartbeat\n\n'));
}, 15000);
```

### Pattern 3: Channel-Based Subscriptions

Let clients subscribe to specific event types:

```typescript
app.get('/events', (req, res) => {
  const channels = (req.query.channels as string || 'metrics,requests').split(',');

  // Store client with their subscriptions
  const client = { res, channels: new Set(channels) };
  clients.add(client);

  req.on('close', () => clients.delete(client));
});

function broadcast(event: string, data: object) {
  clients.forEach(client => {
    if (client.channels.has(event)) {
      client.res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    }
  });
}
```

Client subscribes to specific channels:

```javascript
const source = new EventSource('/events?channels=metrics,alerts');
```

### Pattern 4: Scaling with Redis Pub/Sub

For multiple server instances behind a load balancer, use Redis to broadcast events across all instances:

```typescript
import Redis from 'ioredis';

const redisSub = new Redis();
const redisPub = new Redis();

// Publish events to Redis (from any server instance)
function publishEvent(event: string, data: object) {
  redisPub.publish('dashboard-events', JSON.stringify({ event, data }));
}

// Each server instance subscribes and forwards to its SSE clients
redisSub.subscribe('dashboard-events');
redisSub.on('message', (channel, message) => {
  const { event, data } = JSON.parse(message);
  clients.forEach(client => {
    client.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  });
});
```

<div class="diagram-box">
SCALING SSE WITH REDIS

Client A ──► Server 1 ◄──┐
Client B ──► Server 1     │
                          ├── Redis Pub/Sub
Client C ──► Server 2 ◄──┘
Client D ──► Server 2

Any server publishes to Redis.
All servers receive and forward to their connected clients.
Every client sees every event.
</div>

## SSE vs Polling vs WebSocket for Dashboards

| Approach | Latency | Complexity | Server Load |
|----------|---------|------------|-------------|
| Polling (1s) | Up to 1s delay | Lowest | Highest (constant requests) |
| Long Polling | Near-instant | Medium | Medium |
| SSE | Instant | Low | Low (one connection) |
| WebSocket | Instant | Highest | Low |

For dashboards that only need server-to-client data flow, SSE is the optimal choice. It's simpler than WebSocket, more efficient than polling, and works natively in every browser.

## When to Choose Something Else

- **Bidirectional communication** (chat, collaboration) → WebSocket
- **Binary data streaming** (video, audio) → WebSocket
- **Millions of concurrent connections** → WebSocket with custom protocol
- **Server-to-server streaming** → gRPC

For everything else — dashboards, notifications, live feeds, LLM streaming — SSE is the right default.

*Published by the TechAI Explained Team.*
