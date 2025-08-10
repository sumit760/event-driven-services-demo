# Setup & Installation Guide

This guide will help you set up and run the Event-Driven Microservices Demo in different environments.

## Prerequisites

### Required Software

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Git** for cloning the repository
- **Python 3.8+** for running client examples
- **kubectl** (for Kubernetes deployment)
- **Dapr CLI** (for local Dapr development)

### System Requirements

- **Memory**: 8GB RAM minimum (16GB recommended)
- **CPU**: 4 cores minimum
- **Disk**: 10GB free space
- **Network**: Internet connection for downloading images

## Quick Start (Local Development)

### 1. Clone the Repository

```bash
git clone https://github.com/sumit760/event-driven-services-demo.git
cd event-driven-services-demo
```

### 2. Run the Demo

```bash
# Make the script executable (if not already)
chmod +x scripts/deploy-local.sh

# Deploy the entire stack
./scripts/deploy-local.sh
```

This script will:
- ✅ Check prerequisites
- 🏗️ Build all services
- 🚀 Start infrastructure (Kafka, Redis, monitoring)
- 📦 Deploy application services with Dapr sidecars
- 🔍 Perform health checks
- 📊 Display service URLs

### 3. Test the System

```bash
# Install client dependencies
cd examples/client
pip install -r requirements.txt

# Run the demo workflow
python order-client.py

# Or run in interactive mode
python order-client.py --interactive
```

### 4. Access Dashboards

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686

## Manual Setup (Step by Step)

If you prefer to set up components manually or need to troubleshoot:

### 1. Infrastructure Services

```bash
# Start infrastructure
docker-compose up -d zookeeper kafka redis jaeger prometheus grafana dapr-placement

# Wait for services to be ready
sleep 30

# Create Kafka topics
docker-compose exec kafka kafka-topics --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 3 --topic order.created --if-not-exists
docker-compose exec kafka kafka-topics --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 3 --topic order.updated --if-not-exists
docker-compose exec kafka kafka-topics --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 3 --topic inventory.reserved --if-not-exists
docker-compose exec kafka kafka-topics --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 3 --topic payment.processed --if-not-exists
```

### 2. Application Services

```bash
# Build services
docker-compose build order-service inventory-service notification-service

# Start services with Dapr sidecars
docker-compose up -d order-service order-service-dapr
docker-compose up -d inventory-service inventory-service-dapr
docker-compose up -d notification-service notification-service-dapr
```

### 3. Verify Deployment

```bash
# Check service status
docker-compose ps

# Check service logs
docker-compose logs order-service
docker-compose logs inventory-service
docker-compose logs notification-service

# Test connectivity
curl http://localhost:3000/health  # Notification service
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (local or cloud)
- kubectl configured
- Dapr installed on the cluster

### 1. Install Dapr on Kubernetes

```bash
# Install Dapr CLI
wget -q https://raw.githubusercontent.com/dapr/cli/master/install/install.sh -O - | /bin/bash

# Initialize Dapr on Kubernetes
dapr init -k

# Verify Dapr installation
dapr status -k
```

### 2. Deploy Infrastructure

```bash
# Create namespace and deploy infrastructure
kubectl apply -f k8s/infrastructure/

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=kafka -n demo --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n demo --timeout=300s
```

### 3. Deploy Dapr Components

```bash
# Deploy Dapr components
kubectl apply -f dapr/components/ -n demo
kubectl apply -f dapr/configuration/ -n demo

# Verify components
dapr components -k -n demo
```

### 4. Build and Push Images

```bash
# Build images (replace with your registry)
docker build -t your-registry/order-service:latest services/order-service/
docker build -t your-registry/inventory-service:latest services/inventory-service/
docker build -t your-registry/notification-service:latest services/notification-service/

# Push images
docker push your-registry/order-service:latest
docker push your-registry/inventory-service:latest
docker push your-registry/notification-service:latest
```

### 5. Deploy Services

```bash
# Update image references in k8s manifests
sed -i 's|order-service:latest|your-registry/order-service:latest|g' k8s/services/order-service.yaml
sed -i 's|inventory-service:latest|your-registry/inventory-service:latest|g' k8s/services/inventory-service.yaml
sed -i 's|notification-service:latest|your-registry/notification-service:latest|g' k8s/services/notification-service.yaml

# Deploy services
kubectl apply -f k8s/services/

# Check deployment status
kubectl get pods -n demo
kubectl get services -n demo
```

### 6. Access Services

```bash
# Port forward to access services locally
kubectl port-forward svc/order-service 50051:50051 -n demo &
kubectl port-forward svc/inventory-service 50052:50052 -n demo &
kubectl port-forward svc/notification-service 3000:3000 -n demo &

# Test the services
python examples/client/order-client.py
```

## Development Setup

### Local Development with Dapr CLI

For development, you can run services locally with Dapr CLI:

```bash
# Terminal 1: Start infrastructure
docker-compose up -d kafka redis

# Terminal 2: Run Order Service
cd services/order-service
dapr run --app-id order-service --app-port 50051 --dapr-http-port 3500 --components-path ../../dapr/components go run main.go

# Terminal 3: Run Inventory Service
cd services/inventory-service
dapr run --app-id inventory-service --app-port 50052 --dapr-http-port 3501 --components-path ../../dapr/components python main.py

# Terminal 4: Run Notification Service
cd services/notification-service
dapr run --app-id notification-service --app-port 3000 --dapr-http-port 3502 --components-path ../../dapr/components npm start
```

### IDE Setup

#### VS Code

Recommended extensions:
- Go extension
- Python extension
- Docker extension
- Kubernetes extension
- Dapr extension

#### IntelliJ IDEA

Recommended plugins:
- Go plugin
- Python plugin
- Docker plugin
- Kubernetes plugin

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DAPR_HTTP_PORT` | Dapr HTTP port | 3500 |
| `DAPR_GRPC_PORT` | Dapr gRPC port | 50001 |
| `KAFKA_BROKERS` | Kafka broker addresses | kafka:9092 |
| `REDIS_HOST` | Redis host | redis:6379 |
| `LOG_LEVEL` | Logging level | info |

### Dapr Components

The demo uses the following Dapr components:

- **Pub/Sub**: Kafka for event streaming
- **State Store**: Redis for state management
- **Service Invocation**: For inter-service communication

### Monitoring Configuration

- **Prometheus**: Scrapes metrics from services and infrastructure
- **Grafana**: Visualizes metrics with pre-built dashboards
- **Jaeger**: Collects distributed traces

## Troubleshooting

### Common Issues

#### Services Not Starting

```bash
# Check Docker daemon
docker info

# Check available resources
docker system df
docker system prune -f  # Clean up if needed

# Check service logs
docker-compose logs [service-name]
```

#### Kafka Connection Issues

```bash
# Check Kafka status
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# List topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check consumer groups
docker-compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list
```

#### Dapr Issues

```bash
# Check Dapr status
dapr status

# Check Dapr logs
docker-compose logs order-service-dapr
docker-compose logs inventory-service-dapr
docker-compose logs notification-service-dapr
```

#### gRPC Connection Issues

```bash
# Test gRPC connectivity
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50052 list

# Check if ports are open
netstat -tulpn | grep :50051
netstat -tulpn | grep :50052
```

### Performance Tuning

#### Docker Resources

```bash
# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Advanced > Memory: 8GB+

# For Linux, check available resources
free -h
df -h
```

#### Kafka Configuration

```yaml
# In docker-compose.yml, adjust Kafka settings:
environment:
  KAFKA_HEAP_OPTS: "-Xmx1G -Xms1G"
  KAFKA_NUM_NETWORK_THREADS: "8"
  KAFKA_NUM_IO_THREADS: "8"
```

#### Service Resources

```yaml
# In docker-compose.yml, add resource limits:
services:
  order-service:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### Debugging

#### Enable Debug Logging

```bash
# Set environment variables for debug logging
export LOG_LEVEL=debug
export DAPR_LOG_LEVEL=debug

# Restart services
docker-compose restart
```

#### Access Service Logs

```bash
# Follow logs for all services
docker-compose logs -f

# Follow logs for specific service
docker-compose logs -f order-service

# View Dapr sidecar logs
docker-compose logs -f order-service-dapr
```

#### Network Debugging

```bash
# Check network connectivity
docker-compose exec order-service ping kafka
docker-compose exec order-service ping redis

# Check DNS resolution
docker-compose exec order-service nslookup kafka
```

## Cleanup

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Clean Docker System

```bash
# Remove unused containers, networks, images
docker system prune -f

# Remove all unused volumes
docker volume prune -f

# Remove all unused images
docker image prune -a -f
```

## Next Steps

After successful setup:

1. **Explore the APIs**: Use the client examples to interact with services
2. **Monitor the System**: Check Grafana dashboards and Jaeger traces
3. **Modify the Code**: Make changes and see them in action
4. **Scale Services**: Try scaling individual services
5. **Add Features**: Extend the demo with new services or functionality

For more detailed information, see:
- [Architecture Documentation](architecture.md)
- [API Documentation](api.md)
- [Event Schemas](events.md)

