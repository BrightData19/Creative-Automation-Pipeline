# Kafka Setup Guide for Creative Automation Pipeline

This guide covers the setup, configuration, and troubleshooting of Kafka (Redpanda) for the Creative Automation Pipeline project.

## 🚀 Quick Start

1. **Setup dependencies:**

   ```bash
   make setup
   ```

2. **Configure environment:**

   ```bash
   make check-env
   # Review and update .env file if needed
   ```

3. **Start Kafka services:**

   ```bash
   make run-services
   ```

4. **Wait for Kafka to be ready:**

   ```bash
   make wait-kafka
   ```

5. **Setup Kafka topics:**

   ```bash
   make setup-topics
   ```

6. **Start all application services:**
   ```bash
   make run-dev
   ```

## 📋 What Was Fixed

### 1. **Docker Compose Configuration**

- ✅ Fixed port mapping for external access
- ✅ Added health checks for Kafka and Redpanda Console
- ✅ Proper service dependency management

### 2. **Environment Configuration**

- ✅ Created `env.example` template
- ✅ Centralized Kafka broker configuration
- ✅ Environment-specific settings

### 3. **Kafka Client Improvements**

- ✅ Better retry logic with exponential backoff
- ✅ Connection health checks
- ✅ Proper error handling and logging
- ✅ Client ID configuration for monitoring

### 4. **Topic Management**

- ✅ Automatic topic creation with proper configuration
- ✅ Topic setup script with retention policies
- ✅ Partition and replication factor configuration

### 5. **Service Resilience**

- ✅ Health check endpoints
- ✅ Graceful shutdown handling
- ✅ Connection status monitoring

## 🔧 Configuration Details

### Kafka Broker URLs

- **External (Host)**: `localhost:9092` - Used by applications running on host
- **Internal (Docker)**: `kafka:29092` - Used by services within Docker network

### Topics Created

| Topic                | Partitions | Retention | Purpose                         |
| -------------------- | ---------- | --------- | ------------------------------- |
| `briefs.ingest.v1`   | 3          | 7 days    | Incoming creative briefs        |
| `pipeline.status.v1` | 3          | 30 days   | Pipeline status updates         |
| `assets.created.v1`  | 3          | 30 days   | Generated creative assets       |
| `alerts.v1`          | 2          | 14 days   | System alerts and notifications |

### Environment Variables

```bash
# Kafka Configuration
KAFKA_BROKER=localhost:9092
KAFKA_INTERNAL_BROKER=kafka:29092

# Application Ports
FRONTEND_PORT=3000
REALTIME_GATEWAY_PORT=3001

# Dropbox Configuration
DROPBOX_ROOT=/Apps/CreativeAutomation
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **Kafka Connection Failed**

```bash
# Check if services are running
make status

# Check Docker logs
make logs

# Restart services
make stop-services
make run-services
```

#### 2. **Topics Not Created**

```bash
# Manually create topics
make setup-topics

# Check topic status in Redpanda Console
# http://localhost:8080
```

#### 3. **Port Already in Use**

```bash
# Check what's using the port
lsof -i :9092

# Stop conflicting services
docker compose down
```

#### 4. **Python Dependencies Missing**

```bash
# Reinstall Python dependencies
cd apps/pipeline-worker && uv sync
cd apps/agent-worker && uv sync
```

### Health Checks

#### Kafka Broker Health

```bash
# Check via Redpanda Console
curl http://localhost:8080/api/cluster-config

# Check via realtime gateway
curl http://localhost:3001/health
```

#### Application Health

```bash
# Frontend
curl http://localhost:3000

# Realtime Gateway
curl http://localhost:3001/health

# Check service status
make status
```

## 📊 Monitoring

### Redpanda Console

- **URL**: http://localhost:8080
- **Features**: Topic management, message inspection, consumer groups

### Application Endpoints

- **Frontend**: http://localhost:3000
- **Dashboard**: http://localhost:3000/dashboard
- **Realtime Events**: http://localhost:3001/events
- **Health Check**: http://localhost:3001/health

### Logs

```bash
# All services
make logs

# Specific service
docker compose logs -f kafka
docker compose logs -f redpanda-console
```

## 🔄 Development Workflow

### 1. **Start Development Environment**

```bash
make run-dev
```

This command:

- Starts Kafka services
- Waits for Kafka to be ready
- Sets up required topics
- Starts all application services

### 2. **Submit Test Data**

```bash
make demo
```

This submits a sample brief to test the pipeline.

### 3. **Monitor Progress**

- Check dashboard: http://localhost:3000/dashboard
- Monitor realtime events: http://localhost:3001/events
- View Kafka topics: http://localhost:8080

### 4. **Stop Services**

```bash
make stop-services
```

## 🚨 Production Considerations

### Security

- Enable SSL/TLS encryption
- Configure authentication (SASL)
- Use proper network isolation

### Performance

- Adjust partition counts based on throughput
- Configure retention policies
- Monitor broker metrics

### Monitoring

- Set up alerting for broker health
- Monitor consumer lag
- Track message throughput

## 📚 Additional Resources

- [Redpanda Documentation](https://docs.redpanda.com/)
- [Kafka Python Client](https://kafka-python.readthedocs.io/)
- [Kafkajs Documentation](https://kafka.js.org/)

## 🤝 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review application logs
3. Verify Kafka broker status
4. Check environment configuration

For persistent issues, check the Docker Compose logs and ensure all services are running properly.
