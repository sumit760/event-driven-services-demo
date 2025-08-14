# Event-Driven Microservices Demo

A comprehensive demonstration of event-driven microservices architecture using modern cloud-native technologies.

## 🏗️ Architecture Overview

This demo showcases a complete event-driven microservices system with the following components:

### 🔧 Technology Stack
- **Message Queue**: Apache Kafka for reliable event streaming
- **Communication Protocol**: gRPC for high-performance service-to-service communication
- **Application Runtime**: Dapr for simplified microservices development
- **Service Discovery**: Kubernetes-native service discovery
- **Deployment**: Kubernetes with Docker containers
- **Programming Language**: Go for all microservices

### 🏢 Services Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Order Service │    │Inventory Service│    │Notification Svc │
│     (gRPC)      │    │     (gRPC)      │    │     (HTTP)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────┬───────────┴──────────────────────┘
                     │
          ┌─────────────────┐
          │   Apache Kafka  │
          │  (Event Stream) │
          └─────────────────┘
                     │
          ┌─────────────────┐
          │      Dapr       │
          │ (App Runtime)   │
          └─────────────────┘
                     │
          ┌─────────────────┐
          │   Kubernetes    │
          │   (Orchestration)│
          └─────────────────┘
```

## 🚀 Services

### 1. Order Service (gRPC)
- **Port**: 50051
- **Protocol**: gRPC
- **Responsibilities**:
  - Create and manage customer orders
  - Validate order data and inventory availability
  - Publish order events to Kafka
  - Handle order lifecycle (create, update, cancel)

**Key Features**:
- Order creation with inventory validation
- Order status management
- Event-driven notifications
- Customer order history

### 2. Inventory Service (gRPC)
- **Port**: 50052
- **Protocol**: gRPC
- **Responsibilities**:
  - Manage product inventory levels
  - Handle inventory reservations
  - Process inventory updates
  - Validate product availability

**Key Features**:
- Real-time inventory tracking
- Automatic stock level updates
- Product availability checks
- Inventory reservation system

### 3. Notification Service (HTTP)
- **Port**: 8080
- **Protocol**: HTTP REST
- **Responsibilities**:
  - Process notification events from Kafka
  - Send notifications via multiple channels
  - Handle notification delivery status
  - Manage notification templates

**Key Features**:
- Multi-channel notifications (Email, SMS, Push, Webhook)
- Event-driven processing
- Delivery status tracking
- Template-based messaging

## 🛠️ Prerequisites

Before running this demo, ensure you have the following installed:

- **Docker**: For containerization
- **Kubernetes**: Local cluster (minikube, kind, or Docker Desktop)
- **kubectl**: Kubernetes command-line tool
- **Go**: Version 1.19 or later
- **Git**: For cloning the repository

### Optional Tools
- **Dapr CLI**: For Dapr management (will be installed automatically)
- **Helm**: For advanced Kubernetes deployments

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/sumit760/event-driven-services-demo.git
cd event-driven-services-demo
```

### 2. Deploy the Complete System
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Deploy everything with one command
./scripts/deploy-local.sh
```

This script will:
- ✅ Check prerequisites
- ✅ Install and configure Dapr
- ✅ Deploy Apache Kafka
- ✅ Deploy Dapr components
- ✅ Build and deploy all microservices
- ✅ Verify the deployment

### 3. Test the System

#### Test gRPC Services (Order & Inventory)
```bash
cd examples/grpc-client
go mod tidy
go run main.go
```

#### Test HTTP Service (Notifications)
```bash
cd examples/http-client
go mod tidy
go run main.go
```

## 📋 Manual Deployment (Step by Step)

If you prefer to deploy components individually:

### 1. Install Dapr
```bash
# Install Dapr CLI
curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | /bin/bash

# Initialize Dapr in Kubernetes
dapr init -k --wait
```

### 2. Deploy Kafka
```bash
kubectl create namespace kafka
kubectl apply -f k8s/infrastructure/kafka.yaml
```

### 3. Deploy Dapr Components
```bash
kubectl apply -f k8s/dapr/
```

### 4. Build and Deploy Services
```bash
# Build Docker images
docker build -t order-service:latest services/order-service/
docker build -t inventory-service:latest services/inventory-service/
docker build -t notification-service:latest services/notification-service/

# Deploy to Kubernetes
kubectl apply -f k8s/services/
```

## 🔍 Monitoring and Debugging

### View Service Status
```bash
# Check pod status
kubectl get pods

# Check service endpoints
kubectl get services

# View Dapr sidecars
dapr list -k
```

### Access Logs
```bash
# Order service logs
kubectl logs -l app=order-service -c order-service

# Inventory service logs
kubectl logs -l app=inventory-service -c inventory-service

# Notification service logs
kubectl logs -l app=notification-service -c notification-service

# Dapr sidecar logs
kubectl logs -l app=order-service -c daprd
```

### Dapr Dashboard
```bash
# Launch Dapr dashboard
dapr dashboard -k
```

### Kafka Monitoring
```bash
# Check Kafka topics
kubectl exec -it kafka-0 -n kafka -- kafka-topics.sh --bootstrap-server localhost:9092 --list

# View topic messages
kubectl exec -it kafka-0 -n kafka -- kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic order-events --from-beginning
```

## 🧪 Testing Scenarios

### Scenario 1: Complete Order Flow
1. Create an order via gRPC client
2. Verify inventory check
3. Confirm order creation event in Kafka
4. Check notification delivery

### Scenario 2: Inventory Management
1. Check product availability
2. Reserve inventory for order
3. Update stock levels
4. Handle out-of-stock scenarios

### Scenario 3: Event Processing
1. Monitor Kafka topics for events
2. Verify event consumption by notification service
3. Check notification delivery across channels
4. Validate event ordering and reliability

## 🔧 Configuration

### Environment Variables
Each service supports configuration via environment variables:

#### Order Service
- `DAPR_HTTP_PORT`: Dapr HTTP port (default: 3500)
- `DAPR_GRPC_PORT`: Dapr gRPC port (default: 50001)
- `SERVICE_PORT`: Service port (default: 50051)

#### Inventory Service
- `DAPR_HTTP_PORT`: Dapr HTTP port (default: 3501)
- `DAPR_GRPC_PORT`: Dapr gRPC port (default: 50002)
- `SERVICE_PORT`: Service port (default: 50052)

#### Notification Service
- `DAPR_HTTP_PORT`: Dapr HTTP port (default: 3502)
- `SERVICE_PORT`: Service port (default: 8080)

### Dapr Components
- **State Store**: Redis for persistent state
- **Pub/Sub**: Kafka for event streaming
- **Service Invocation**: mTLS enabled

## 🧹 Cleanup

To remove all deployed resources:

```bash
./scripts/cleanup.sh
```

This will:
- Remove all services and deployments
- Clean up Dapr components
- Remove Kafka installation
- Optionally remove Dapr and Docker images

## 📚 Learning Resources

### Key Concepts Demonstrated
- **Event-Driven Architecture**: Loose coupling via events
- **Microservices Patterns**: Service decomposition and communication
- **Cloud-Native Development**: Kubernetes, containers, and service mesh
- **Observability**: Logging, monitoring, and tracing
- **Resilience**: Circuit breakers, retries, and timeouts

### Further Reading
- [Dapr Documentation](https://docs.dapr.io/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [gRPC Documentation](https://grpc.io/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Event-Driven Architecture Patterns](https://microservices.io/patterns/data/event-driven-architecture.html)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

#### Services Not Starting
- Check if Dapr is properly initialized: `dapr list -k`
- Verify Kubernetes cluster is running: `kubectl cluster-info`
- Check resource availability: `kubectl describe nodes`

#### gRPC Connection Issues
- Verify service endpoints: `kubectl get services`
- Check if ports are correctly exposed
- Ensure firewall rules allow traffic

#### Kafka Connection Issues
- Check Kafka pod status: `kubectl get pods -n kafka`
- Verify Kafka service is accessible
- Check Dapr pub/sub component configuration

#### Build Issues
- Ensure Go version 1.19 or later
- Run `go mod tidy` in service directories
- Check Docker daemon is running

### Getting Help
- Check the [Issues](https://github.com/sumit760/event-driven-services-demo/issues) page
- Review service logs for error messages
- Consult Dapr and Kubernetes documentation

---

****Happy coding! 🚀****

