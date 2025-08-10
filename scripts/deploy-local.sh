#!/bin/bash

# Event-Driven Microservices Demo - Local Deployment Script
# This script sets up the entire demo environment locally using Docker Compose

set -e

echo "🚀 Starting Event-Driven Microservices Demo - Local Deployment"
echo "================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Create monitoring configuration
create_monitoring_config() {
    print_status "Creating monitoring configuration..."
    
    mkdir -p monitoring
    
    cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'order-service'
    static_configs:
      - targets: ['order-service:9090']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'inventory-service'
    static_configs:
      - targets: ['inventory-service:9090']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'notification-service'
    static_configs:
      - targets: ['notification-service:9090']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka:9101']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    metrics_path: '/metrics'
    scrape_interval: 10s
EOF
    
    print_success "Monitoring configuration created"
}

# Build services
build_services() {
    print_status "Building application services..."
    
    # Build Order Service
    print_status "Building Order Service..."
    docker-compose build order-service
    
    # Build Inventory Service
    print_status "Building Inventory Service..."
    docker-compose build inventory-service
    
    # Build Notification Service
    print_status "Building Notification Service..."
    docker-compose build notification-service
    
    print_success "All services built successfully"
}

# Start infrastructure
start_infrastructure() {
    print_status "Starting infrastructure services..."
    
    # Start infrastructure services first
    docker-compose up -d zookeeper kafka redis jaeger prometheus grafana dapr-placement
    
    print_status "Waiting for infrastructure services to be ready..."
    sleep 30
    
    # Check if Kafka is ready
    print_status "Checking Kafka readiness..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list &> /dev/null; then
            print_success "Kafka is ready"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "Kafka failed to start within timeout"
        exit 1
    fi
    
    # Check if Redis is ready
    print_status "Checking Redis readiness..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
            print_success "Redis is ready"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done
    
    if [ $timeout -le 0 ]; then
        print_error "Redis failed to start within timeout"
        exit 1
    fi
    
    print_success "Infrastructure services started successfully"
}

# Start application services
start_applications() {
    print_status "Starting application services..."
    
    # Start application services with their Dapr sidecars
    docker-compose up -d order-service order-service-dapr
    docker-compose up -d inventory-service inventory-service-dapr
    docker-compose up -d notification-service notification-service-dapr
    
    print_status "Waiting for application services to be ready..."
    sleep 20
    
    print_success "Application services started successfully"
}

# Create Kafka topics
create_kafka_topics() {
    print_status "Creating Kafka topics..."
    
    topics=(
        "order.created"
        "order.updated"
        "order.cancelled"
        "inventory.reserved"
        "inventory.released"
        "inventory.updated"
        "payment.processed"
        "payment.failed"
    )
    
    for topic in "${topics[@]}"; do
        print_status "Creating topic: $topic"
        docker-compose exec -T kafka kafka-topics \
            --create \
            --bootstrap-server localhost:9092 \
            --replication-factor 1 \
            --partitions 3 \
            --topic "$topic" \
            --if-not-exists
    done
    
    print_success "Kafka topics created successfully"
}

# Health check
health_check() {
    print_status "Performing health checks..."
    
    # Check Order Service
    if curl -f http://localhost:50051 &> /dev/null; then
        print_success "Order Service is healthy"
    else
        print_warning "Order Service health check failed (gRPC service may not respond to HTTP)"
    fi
    
    # Check Inventory Service
    if curl -f http://localhost:50052 &> /dev/null; then
        print_success "Inventory Service is healthy"
    else
        print_warning "Inventory Service health check failed (gRPC service may not respond to HTTP)"
    fi
    
    # Check Notification Service
    if curl -f http://localhost:3000/health &> /dev/null; then
        print_success "Notification Service is healthy"
    else
        print_warning "Notification Service health check failed"
    fi
    
    # Check Kafka
    if docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 &> /dev/null; then
        print_success "Kafka is healthy"
    else
        print_warning "Kafka health check failed"
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
        print_success "Redis is healthy"
    else
        print_warning "Redis health check failed"
    fi
}

# Display service URLs
display_urls() {
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo "===================================="
    echo ""
    echo "📊 Service URLs:"
    echo "  • Grafana Dashboard:    http://localhost:3001 (admin/admin)"
    echo "  • Prometheus:           http://localhost:9090"
    echo "  • Jaeger Tracing:       http://localhost:16686"
    echo "  • Notification Service: http://localhost:3000/health"
    echo ""
    echo "🔧 Service Ports:"
    echo "  • Order Service (gRPC):      localhost:50051"
    echo "  • Inventory Service (gRPC):  localhost:50052"
    echo "  • Notification Service:      localhost:3000"
    echo "  • Kafka:                     localhost:9092"
    echo "  • Redis:                     localhost:6379"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Test the system: python examples/client/order-client.py"
    echo "  2. View logs: docker-compose logs -f [service-name]"
    echo "  3. Stop services: docker-compose down"
    echo ""
    echo "🐛 Troubleshooting:"
    echo "  • Check service status: docker-compose ps"
    echo "  • View service logs: docker-compose logs [service-name]"
    echo "  • Restart a service: docker-compose restart [service-name]"
    echo ""
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    docker-compose down -v
    print_success "Cleanup completed"
}

# Main execution
main() {
    # Handle script interruption
    trap cleanup EXIT
    
    check_prerequisites
    create_monitoring_config
    build_services
    start_infrastructure
    create_kafka_topics
    start_applications
    health_check
    display_urls
    
    # Remove cleanup trap since we completed successfully
    trap - EXIT
}

# Handle command line arguments
case "${1:-}" in
    "clean")
        print_status "Cleaning up existing deployment..."
        docker-compose down -v
        docker system prune -f
        print_success "Cleanup completed"
        ;;
    "logs")
        docker-compose logs -f "${2:-}"
        ;;
    "status")
        docker-compose ps
        ;;
    "stop")
        print_status "Stopping services..."
        docker-compose down
        print_success "Services stopped"
        ;;
    "restart")
        print_status "Restarting services..."
        docker-compose restart "${2:-}"
        print_success "Services restarted"
        ;;
    *)
        main
        ;;
esac

