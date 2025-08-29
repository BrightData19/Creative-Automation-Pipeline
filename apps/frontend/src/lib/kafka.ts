import { Kafka, Producer, Partitioners } from "kafkajs";

let producer: Producer | null = null;
let connectionStatus: "disconnected" | "connecting" | "connected" | "error" =
  "disconnected";

export async function getKafkaProducer() {
  if (producer && connectionStatus === "connected") return producer;

  if (connectionStatus === "connecting") {
    // Wait for existing connection attempt
    while (connectionStatus === "connecting") {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    if (producer && connectionStatus === "connected") return producer;
  }

  connectionStatus = "connecting";

  try {
    const broker = process.env.KAFKA_BROKER || "localhost:9092";
    console.log(`Connecting to Kafka broker: ${broker}`);

    const kafka = new Kafka({
      clientId: "frontend-api",
      brokers: [broker],
      retry: {
        initialRetryTime: 100,
        retries: 8,
      },
      connectionTimeout: 3000,
      authenticationTimeout: 1000,
    });

    // Use legacy partitioner to retain pre-v2 behavior and silence warning
    producer = kafka.producer({
      createPartitioner: Partitioners.LegacyPartitioner,
      retry: {
        initialRetryTime: 100,
        retries: 8,
      },
    });

    await producer.connect();
    connectionStatus = "connected";
    console.log("Kafka producer connected successfully");
    return producer;
  } catch (error) {
    connectionStatus = "error";
    console.error("Failed to connect Kafka producer:", error);
    throw error;
  }
}

export async function publish(topic: string, message: Record<string, unknown>) {
  try {
    const p = await getKafkaProducer();
    const result = await p.send({
      topic,
      messages: [
        {
          value: JSON.stringify(message),
          timestamp: Date.now().toString(),
        },
      ],
    });

    console.log(`Message published to topic ${topic}:`, result);
    return result;
  } catch (error) {
    console.error(`Failed to publish message to topic ${topic}:`, error);
    // Reset producer on error to force reconnection
    producer = null;
    connectionStatus = "disconnected";
    throw error;
  }
}

export function getConnectionStatus() {
  return connectionStatus;
}

export async function disconnectProducer() {
  if (producer) {
    try {
      await producer.disconnect();
      console.log("Kafka producer disconnected");
    } catch (error) {
      console.error("Error disconnecting producer:", error);
    } finally {
      producer = null;
      connectionStatus = "disconnected";
    }
  }
}
