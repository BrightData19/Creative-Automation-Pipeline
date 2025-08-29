// /apps/realtime-gateway/index.js

const express = require("express");
const cors = require("cors");
const { Kafka } = require("kafkajs");

const app = express();
const port = process.env.REALTIME_GATEWAY_PORT || 3001;

// --- Middleware ---
app.use(cors());
app.use(express.json());

// --- SSE Setup ---
let clients = [];

app.get("/events", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const clientId = Date.now();
  const newClient = { id: clientId, res };
  clients.push(newClient);
  console.log(`Client ${clientId} connected`);

  req.on("close", () => {
    clients = clients.filter((c) => c.id !== clientId);
    console.log(`Client ${clientId} disconnected`);
  });
});

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    kafka: kafkaStatus,
    clients: clients.length,
    timestamp: new Date().toISOString(),
  });
});

function broadcastEvent(event) {
  const data = `data: ${JSON.stringify(event)}\n\n`;
  clients.forEach((client) => {
    try {
      client.res.write(data);
    } catch (error) {
      console.error(`Error broadcasting to client ${client.id}:`, error);
    }
  });
}

// --- Kafka Configuration ---
const kafkaConfig = {
  clientId: "realtime-gateway",
  brokers: [process.env.KAFKA_BROKER || "localhost:9092"],
  retry: {
    initialRetryTime: 100,
    retries: 8,
  },
  connectionTimeout: 3000,
  authenticationTimeout: 1000,
};

const kafka = new Kafka(kafkaConfig);
const consumer = kafka.consumer({
  groupId: "realtime-gateway-group",
  retry: {
    initialRetryTime: 100,
    retries: 8,
  },
});

let kafkaStatus = "disconnected";
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

// --- Kafka Health Check ---
async function checkKafkaHealth() {
  try {
    const admin = kafka.admin();
    await admin.connect();
    const metadata = await admin.fetchTopicMetadata();
    await admin.disconnect();
    kafkaStatus = "connected";
    reconnectAttempts = 0;
    return true;
  } catch (error) {
    console.error("Kafka health check failed:", error.message);
    kafkaStatus = "disconnected";
    return false;
  }
}

// --- Kafka Consumer Setup ---
const runConsumer = async () => {
  try {
    // Check health before connecting
    if (!(await checkKafkaHealth())) {
      throw new Error("Kafka broker not healthy");
    }

    await consumer.connect();
    console.log("Kafka consumer connected successfully.");

    // Subscribe to specific topics instead of regex for better reliability
    const topics = [
      "briefs.ingest.v1",
      "pipeline.status.v1",
      "assets.created.v1",
      "alerts.v1",
      "compliance.v1",
      "approvals.request.v1",
      "approvals.decision.v1",
      "performance.metrics.v1",
      "ready_for_publish.v1",
    ];

    for (const topic of topics) {
      await consumer.subscribe({ topic, fromBeginning: false });
      console.log(`Subscribed to topic: ${topic}`);
    }

    await consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        try {
          console.log(
            `Received message from ${topic}:`,
            message.value.toString()
          );
          const event = {
            topic,
            timestamp: new Date().toISOString(),
            ...JSON.parse(message.value.toString()),
          };
          broadcastEvent(event);
        } catch (error) {
          console.error("Error processing message:", error);
        }
      },
    });

    kafkaStatus = "connected";
    reconnectAttempts = 0;
  } catch (error) {
    console.error("Kafka consumer error:", error);
    kafkaStatus = "error";

    // Implement exponential backoff for reconnection
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      const delay = Math.min(5000 * Math.pow(2, reconnectAttempts), 30000);
      console.log(
        `Retrying Kafka connection in ${delay}ms (attempt ${
          reconnectAttempts + 1
        }/${MAX_RECONNECT_ATTEMPTS})...`
      );
      reconnectAttempts++;
      setTimeout(() => runConsumer(), delay);
    } else {
      console.error(
        "Max reconnection attempts reached. Please check Kafka broker status."
      );
      kafkaStatus = "failed";
    }
  }
};

// --- Server Start ---
app.listen(port, () => {
  console.log(`Realtime gateway listening at http://localhost:${port}`);
  console.log(`Health check available at http://localhost:${port}/health`);

  // Start Kafka consumer after a short delay to ensure broker is ready
  setTimeout(() => {
    runConsumer().catch((e) => console.error("Kafka consumer error:", e));
  }, 2000);
});

// Graceful shutdown
process.on("SIGINT", async () => {
  console.log("Shutting down gracefully...");
  try {
    await consumer.disconnect();
    console.log("Kafka consumer disconnected successfully");
    process.exit(0);
  } catch (error) {
    console.error("Error during shutdown:", error);
    process.exit(1);
  }
});

// Periodic health check
setInterval(checkKafkaHealth, 30000); // Check every 30 seconds
