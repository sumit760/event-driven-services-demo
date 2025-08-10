#!/bin/bash

# Event-Driven Microservices Demo - Local Deployment Script
# This script deploys the complete demo application to a local Kubernetes cluster

set -e

echo "🚀 Starting Event-Driven Microservices Demo Deployment..."

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
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if Kubernetes cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Kubernetes cluster is not accessible. Please ensure your cluster is running."
        exit 1
    fi
    
    print_success "Prerequisites check passed!"
}

# Install Dapr
install_dapr() {
    print_status "Installing Dapr..."
    
    # Check if Dapr is already installed
    if kubectl get namespace dapr-system &> /dev/null; then
        print_warning "Dapr is already installed. Skipping installation."
        return
    fi
    
    # Install Dapr CLI if not present
    if ! command -v dapr &> /dev/null; then
        print_status "Installing Dapr CLI..."
        curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | /bin/bash
    fi
    
    # Initialize Dapr in Kubernetes
    dapr init -k --wait
    
    print_success "Dapr installed successfully!"
}

# Install Kafka
install_kafka() {
    print_status "Installing Kafka..."
    
    # Check if Kafka is already installed
    if kubectl get namespace kafka &> /dev/null; then
        print_warning "Kafka namespace already exists. Skipping installation."
        return
    fi
    
    # Create Kafka namespace
    kubectl create namespace kafka
    
    # Apply Kafka manifests
    kubectl apply -f k8s/infrastructure/kafka.yaml
    
    # Wait for Kafka to be ready
    print_status "Waiting for Kafka to be ready..."
    kubectl wait --for=condition=ready pod -l app=kafka -n kafka --timeout=300s
    
    print_success "Kafka installed successfully!"
}

# Deploy Dapr components
deploy_dapr_components() {
    print_status "Deploying Dapr components..."
    
    kubectl apply -f k8s/dapr/
    
    print_success "Dapr components deployed successfully!"
}

# Build and deploy services
build_and_deploy_services() {
    print_status "Building and deploying services..."
    
    # Build Docker images
    print_status "Building Docker images..."
    
    # Build Order Service
    print_status "Building Order Service..."
    docker build -t order-service:latest services/order-service/
    
    # Build Inventory Service
    print_status "Building Inventory Service..."
    docker build -t inventory-service:latest services/inventory-service/
    
    # Build Notification Service
    print_status "Building Notification Service..."
    docker build -t notification-service:latest services/notification-service/
    
    print_success "Docker images built successfully!"
    
    # Deploy services
    print_status "Deploying services to Kubernetes..."
    
    kubectl apply -f k8s/services/
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    kubectl wait --for=condition=available deployment/order-service --timeout=300s
    kubectl wait --for=condition=available deployment/inventory-service --timeout=300s
    kubectl wait --for=condition=available deployment/notification-service --timeout=300s
    
    print_success "Services deployed successfully!"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    echo ""
    echo "=== Deployment Status ==="
    kubectl get pods -o wide
    echo ""
    kubectl get services
    echo ""
    
    # Check Dapr sidecars
    print_status "Checking Dapr sidecars..."
    dapr list -k
    
    print_success "Deployment verification completed!"
}

# Display access information
display_access_info() {
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "=== Service Access Information ==="
    
    # Get service endpoints
    ORDER_SERVICE_PORT=$(kubectl get service order-service -o jsonpath='{.spec.ports[0].nodePort}')
    INVENTORY_SERVICE_PORT=$(kubectl get service inventory-service -o jsonpath='{.spec.ports[0].nodePort}')
    NOTIFICATION_SERVICE_PORT=$(kubectl get service notification-service -o jsonpath='{.spec.ports[0].nodePort}')
    
    echo "📦 Order Service (gRPC): localhost:${ORDER_SERVICE_PORT}"
    echo "📋 Inventory Service (gRPC): localhost:${INVENTORY_SERVICE_PORT}"
    echo "📧 Notification Service (HTTP): localhost:${NOTIFICATION_SERVICE_PORT}"
    echo ""
    echo "=== Testing the Application ==="
    echo "You can test the application using the client examples:"
    echo "  go run examples/grpc-client/main.go"
    echo "  go run examples/http-client/main.go"
    echo ""
    echo "=== Monitoring ==="
    echo "Dapr Dashboard: dapr dashboard -k"
    echo "Kubernetes Dashboard: kubectl proxy"
    echo ""
    echo "=== Cleanup ==="
    echo "To remove the deployment: ./scripts/cleanup.sh"
}

# Main execution
main() {
    check_prerequisites
    install_dapr
    install_kafka
    deploy_dapr_components
    build_and_deploy_services
    verify_deployment
    display_access_info
}

# Run main function
main "$@"

