#!/usr/bin/env python3

"""
Event-Driven Microservices Demo - Order Client
This client demonstrates how to interact with the order service
and observe the event-driven workflow.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List
import requests
import grpc
import sys
import os

# Add the proto directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services/order-service'))

try:
    import order_pb2
    import order_pb2_grpc
except ImportError:
    print("Error: Could not import order protobuf files.")
    print("Please ensure the order service protobuf files are generated.")
    print("Run: cd services/order-service && python -m grpc_tools.protoc --proto_path=proto --python_out=. --grpc_python_out=. proto/order.proto")
    sys.exit(1)

class OrderClient:
    """Client for interacting with the Order Service"""
    
    def __init__(self, order_service_host='localhost', order_service_port=50051):
        self.order_service_host = order_service_host
        self.order_service_port = order_service_port
        self.channel = None
        self.stub = None
    
    def connect(self):
        """Connect to the order service"""
        try:
            self.channel = grpc.insecure_channel(f'{self.order_service_host}:{self.order_service_port}')
            self.stub = order_pb2_grpc.OrderServiceStub(self.channel)
            print(f"✅ Connected to Order Service at {self.order_service_host}:{self.order_service_port}")
        except Exception as e:
            print(f"❌ Failed to connect to Order Service: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from the order service"""
        if self.channel:
            self.channel.close()
            print("🔌 Disconnected from Order Service")
    
    def create_order(self, customer_id: str, customer_email: str, items: List[Dict], 
                    shipping_address: str, payment_method: str) -> Dict[str, Any]:
        """Create a new order"""
        try:
            # Convert items to protobuf format
            order_items = []
            for item in items:
                order_item = order_pb2.OrderItem(
                    product_id=item['product_id'],
                    product_name=item['product_name'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price']
                )
                order_items.append(order_item)
            
            # Create the request
            request = order_pb2.CreateOrderRequest(
                customer_id=customer_id,
                customer_email=customer_email,
                items=order_items,
                shipping_address=shipping_address,
                payment_method=payment_method
            )
            
            print(f"📦 Creating order for customer: {customer_id}")
            response = self.stub.CreateOrder(request)
            
            if response.success:
                print(f"✅ Order created successfully: {response.order.order_id}")
                return {
                    'success': True,
                    'order_id': response.order.order_id,
                    'total_amount': response.order.total_amount,
                    'status': response.order.status,
                    'message': response.message
                }
            else:
                print(f"❌ Failed to create order: {response.message}")
                return {
                    'success': False,
                    'message': response.message
                }
                
        except grpc.RpcError as e:
            print(f"❌ gRPC error creating order: {e.code()} - {e.details()}")
            return {
                'success': False,
                'message': f"gRPC error: {e.details()}"
            }
        except Exception as e:
            print(f"❌ Unexpected error creating order: {e}")
            return {
                'success': False,
                'message': f"Unexpected error: {str(e)}"
            }
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get an order by ID"""
        try:
            request = order_pb2.GetOrderRequest(order_id=order_id)
            response = self.stub.GetOrder(request)
            
            if response.success:
                order = response.order
                return {
                    'success': True,
                    'order': {
                        'order_id': order.order_id,
                        'customer_id': order.customer_id,
                        'customer_email': order.customer_email,
                        'total_amount': order.total_amount,
                        'status': order.status,
                        'created_at': order.created_at,
                        'updated_at': order.updated_at,
                        'items': [
                            {
                                'product_id': item.product_id,
                                'product_name': item.product_name,
                                'quantity': item.quantity,
                                'unit_price': item.unit_price,
                                'total_price': item.total_price
                            }
                            for item in order.items
                        ]
                    }
                }
            else:
                return {
                    'success': False,
                    'message': response.message
                }
                
        except grpc.RpcError as e:
            print(f"❌ gRPC error getting order: {e.code()} - {e.details()}")
            return {
                'success': False,
                'message': f"gRPC error: {e.details()}"
            }
    
    def update_order(self, order_id: str, status: str) -> Dict[str, Any]:
        """Update an order status"""
        try:
            # Convert string status to enum
            status_map = {
                'pending': order_pb2.OrderStatus.ORDER_STATUS_PENDING,
                'confirmed': order_pb2.OrderStatus.ORDER_STATUS_CONFIRMED,
                'processing': order_pb2.OrderStatus.ORDER_STATUS_PROCESSING,
                'shipped': order_pb2.OrderStatus.ORDER_STATUS_SHIPPED,
                'delivered': order_pb2.OrderStatus.ORDER_STATUS_DELIVERED,
                'cancelled': order_pb2.OrderStatus.ORDER_STATUS_CANCELLED,
                'failed': order_pb2.OrderStatus.ORDER_STATUS_FAILED
            }
            
            status_enum = status_map.get(status.lower(), order_pb2.OrderStatus.ORDER_STATUS_UNSPECIFIED)
            
            request = order_pb2.UpdateOrderRequest(
                order_id=order_id,
                status=status_enum
            )
            
            response = self.stub.UpdateOrder(request)
            
            if response.success:
                print(f"✅ Order {order_id} updated to status: {status}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': status,
                    'message': response.message
                }
            else:
                print(f"❌ Failed to update order: {response.message}")
                return {
                    'success': False,
                    'message': response.message
                }
                
        except grpc.RpcError as e:
            print(f"❌ gRPC error updating order: {e.code()} - {e.details()}")
            return {
                'success': False,
                'message': f"gRPC error: {e.details()}"
            }
    
    def cancel_order(self, order_id: str, reason: str = "Customer request") -> Dict[str, Any]:
        """Cancel an order"""
        try:
            request = order_pb2.CancelOrderRequest(
                order_id=order_id,
                reason=reason
            )
            
            response = self.stub.CancelOrder(request)
            
            if response.success:
                print(f"✅ Order {order_id} cancelled successfully")
                return {
                    'success': True,
                    'order_id': order_id,
                    'message': response.message
                }
            else:
                print(f"❌ Failed to cancel order: {response.message}")
                return {
                    'success': False,
                    'message': response.message
                }
                
        except grpc.RpcError as e:
            print(f"❌ gRPC error cancelling order: {e.code()} - {e.details()}")
            return {
                'success': False,
                'message': f"gRPC error: {e.details()}"
            }

def check_notification_service():
    """Check if notification service is responding"""
    try:
        response = requests.get('http://localhost:3000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Notification Service is healthy")
            return True
        else:
            print(f"⚠️ Notification Service returned status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"⚠️ Notification Service is not responding: {e}")
        return False

def demo_workflow():
    """Demonstrate the complete order workflow"""
    print("🚀 Starting Event-Driven Microservices Demo")
    print("=" * 50)
    
    # Check services
    print("\n🔍 Checking service health...")
    notification_healthy = check_notification_service()
    
    # Create client
    client = OrderClient()
    
    try:
        # Connect to order service
        client.connect()
        
        # Sample order data
        customer_id = f"customer-{uuid.uuid4().hex[:8]}"
        customer_email = "demo@example.com"
        
        sample_items = [
            {
                'product_id': 'prod-001',
                'product_name': 'Laptop Computer',
                'quantity': 1,
                'unit_price': 999.99
            },
            {
                'product_id': 'prod-002',
                'product_name': 'Wireless Mouse',
                'quantity': 2,
                'unit_price': 29.99
            }
        ]
        
        shipping_address = "123 Demo Street, Test City, TC 12345"
        payment_method = "credit_card"
        
        print(f"\n📋 Order Details:")
        print(f"  Customer ID: {customer_id}")
        print(f"  Customer Email: {customer_email}")
        print(f"  Items: {len(sample_items)} products")
        print(f"  Shipping: {shipping_address}")
        print(f"  Payment: {payment_method}")
        
        # Step 1: Create order
        print(f"\n🛒 Step 1: Creating order...")
        create_result = client.create_order(
            customer_id=customer_id,
            customer_email=customer_email,
            items=sample_items,
            shipping_address=shipping_address,
            payment_method=payment_method
        )
        
        if not create_result['success']:
            print(f"❌ Demo failed: {create_result['message']}")
            return
        
        order_id = create_result['order_id']
        print(f"✅ Order created: {order_id}")
        print(f"💰 Total amount: ${create_result['total_amount']:.2f}")
        
        # Wait for event processing
        print(f"\n⏳ Waiting for event processing...")
        time.sleep(3)
        
        # Step 2: Check order status
        print(f"\n📊 Step 2: Checking order status...")
        get_result = client.get_order(order_id)
        
        if get_result['success']:
            order = get_result['order']
            print(f"✅ Order retrieved successfully")
            print(f"  Status: {order['status']}")
            print(f"  Created: {order['created_at']}")
            print(f"  Updated: {order['updated_at']}")
        else:
            print(f"❌ Failed to retrieve order: {get_result['message']}")
        
        # Step 3: Update order status (simulate processing)
        print(f"\n🔄 Step 3: Updating order status to 'processing'...")
        update_result = client.update_order(order_id, 'processing')
        
        if update_result['success']:
            print(f"✅ Order status updated successfully")
        else:
            print(f"❌ Failed to update order: {update_result['message']}")
        
        # Wait for event processing
        print(f"\n⏳ Waiting for event processing...")
        time.sleep(2)
        
        # Step 4: Simulate order completion
        print(f"\n🚚 Step 4: Updating order status to 'shipped'...")
        ship_result = client.update_order(order_id, 'shipped')
        
        if ship_result['success']:
            print(f"✅ Order shipped successfully")
        else:
            print(f"❌ Failed to ship order: {ship_result['message']}")
        
        # Wait for event processing
        print(f"\n⏳ Waiting for final event processing...")
        time.sleep(2)
        
        # Step 5: Final order status check
        print(f"\n📋 Step 5: Final order status check...")
        final_result = client.get_order(order_id)
        
        if final_result['success']:
            final_order = final_result['order']
            print(f"✅ Final order status: {final_order['status']}")
            print(f"  Last updated: {final_order['updated_at']}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"📝 Order ID for reference: {order_id}")
        
        if notification_healthy:
            print(f"📧 Check the logs to see notification events being processed")
            print(f"   docker-compose logs notification-service")
        
        print(f"\n🔍 Observability:")
        print(f"  • View traces: http://localhost:16686")
        print(f"  • View metrics: http://localhost:9090")
        print(f"  • View dashboards: http://localhost:3001")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
    finally:
        client.disconnect()

def interactive_mode():
    """Interactive mode for testing individual operations"""
    print("🎮 Interactive Mode - Event-Driven Microservices Demo")
    print("=" * 55)
    
    client = OrderClient()
    
    try:
        client.connect()
        
        while True:
            print(f"\n📋 Available Commands:")
            print(f"  1. Create Order")
            print(f"  2. Get Order")
            print(f"  3. Update Order")
            print(f"  4. Cancel Order")
            print(f"  5. Run Demo Workflow")
            print(f"  6. Exit")
            
            choice = input(f"\n🔢 Enter your choice (1-6): ").strip()
            
            if choice == '1':
                # Create order
                customer_id = input("Customer ID (or press Enter for random): ").strip()
                if not customer_id:
                    customer_id = f"customer-{uuid.uuid4().hex[:8]}"
                
                customer_email = input("Customer Email (demo@example.com): ").strip()
                if not customer_email:
                    customer_email = "demo@example.com"
                
                # Use sample items for simplicity
                items = [
                    {
                        'product_id': 'prod-001',
                        'product_name': 'Laptop Computer',
                        'quantity': 1,
                        'unit_price': 999.99
                    }
                ]
                
                result = client.create_order(
                    customer_id=customer_id,
                    customer_email=customer_email,
                    items=items,
                    shipping_address="123 Demo Street, Test City, TC 12345",
                    payment_method="credit_card"
                )
                
                if result['success']:
                    print(f"✅ Order created: {result['order_id']}")
                else:
                    print(f"❌ Failed: {result['message']}")
            
            elif choice == '2':
                # Get order
                order_id = input("Enter Order ID: ").strip()
                if order_id:
                    result = client.get_order(order_id)
                    if result['success']:
                        order = result['order']
                        print(f"✅ Order found:")
                        print(f"  ID: {order['order_id']}")
                        print(f"  Customer: {order['customer_id']}")
                        print(f"  Status: {order['status']}")
                        print(f"  Total: ${order['total_amount']:.2f}")
                    else:
                        print(f"❌ Failed: {result['message']}")
            
            elif choice == '3':
                # Update order
                order_id = input("Enter Order ID: ").strip()
                status = input("Enter new status (pending/confirmed/processing/shipped/delivered/cancelled): ").strip()
                if order_id and status:
                    result = client.update_order(order_id, status)
                    if result['success']:
                        print(f"✅ Order updated successfully")
                    else:
                        print(f"❌ Failed: {result['message']}")
            
            elif choice == '4':
                # Cancel order
                order_id = input("Enter Order ID: ").strip()
                reason = input("Cancellation reason (optional): ").strip()
                if order_id:
                    result = client.cancel_order(order_id, reason or "User request")
                    if result['success']:
                        print(f"✅ Order cancelled successfully")
                    else:
                        print(f"❌ Failed: {result['message']}")
            
            elif choice == '5':
                # Run demo workflow
                demo_workflow()
                return
            
            elif choice == '6':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print(f"\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.disconnect()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Event-Driven Microservices Demo Client')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='Run in interactive mode')
    parser.add_argument('--host', default='localhost', 
                       help='Order service host (default: localhost)')
    parser.add_argument('--port', type=int, default=50051, 
                       help='Order service port (default: 50051)')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        demo_workflow()

if __name__ == '__main__':
    main()

