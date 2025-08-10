#!/bin/bash

# Event-Driven Microservices Demo - Cleanup Script
# This script removes all deployed resources from the Kubernetes cluster

set -e

echo "🧹 Starting cleanup of Event-Driven Microservices Demo..."

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

# Remove services
cleanup_services() {
    print_status "Removing services..."
    
    if kubectl get deployment order-service &> /dev/null; then
        kubectl delete -f k8s/services/ --ignore-not-found=true
        print_success "Services removed successfully!"
    else
        print_warning "No services found to remove."
    fi
}

# Remove Dapr components
cleanup_dapr_components() {
    print_status "Removing Dapr components..."
    
    kubectl delete -f k8s/dapr/ --ignore-not-found=true
    print_success "Dapr components removed successfully!"
}

# Remove Kafka
cleanup_kafka() {
    print_status "Removing Kafka..."
    
    if kubectl get namespace kafka &> /dev/null; then
        kubectl delete -f k8s/infrastructure/kafka.yaml --ignore-not-found=true
        kubectl delete namespace kafka --ignore-not-found=true
        print_success "Kafka removed successfully!"
    else
        print_warning "Kafka namespace not found."
    fi
}

# Remove Dapr (optional)
cleanup_dapr() {
    read -p "Do you want to remove Dapr completely? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing Dapr..."
        if command -v dapr &> /dev/null; then
            dapr uninstall -k
            print_success "Dapr removed successfully!"
        else
            print_warning "Dapr CLI not found. Manually remove Dapr resources if needed."
        fi
    else
        print_status "Keeping Dapr installed."
    fi
}

# Remove Docker images (optional)
cleanup_docker_images() {
    read -p "Do you want to remove Docker images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing Docker images..."
        
        # Remove service images
        docker rmi order-service:latest --force 2>/dev/null || true
        docker rmi inventory-service:latest --force 2>/dev/null || true
        docker rmi notification-service:latest --force 2>/dev/null || true
        
        print_success "Docker images removed successfully!"
    else
        print_status "Keeping Docker images."
    fi
}

# Verify cleanup
verify_cleanup() {
    print_status "Verifying cleanup..."
    
    echo ""
    echo "=== Remaining Resources ==="
    kubectl get pods --all-namespaces | grep -E "(order-service|inventory-service|notification-service|kafka)" || echo "No demo resources found."
    echo ""
    
    print_success "Cleanup verification completed!"
}

# Main execution
main() {
    cleanup_services
    cleanup_dapr_components
    cleanup_kafka
    cleanup_dapr
    cleanup_docker_images
    verify_cleanup
    
    echo ""
    echo "🎉 Cleanup completed successfully!"
    echo "Your Kubernetes cluster is now clean of demo resources."
}

# Run main function
main "$@"

