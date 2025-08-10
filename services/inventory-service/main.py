#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import uuid
from concurrent import futures
from datetime import datetime
from typing import Dict, Any

import grpc
from dapr.clients import DaprClient
from dapr.ext.grpc import App
import redis

# Import generated protobuf classes
import inventory_pb2
import inventory_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GRPC_PORT = 50052
DAPR_HTTP_PORT = 3500
PUBSUB_NAME = "kafka-pubsub"
STATE_STORE_NAME = "redis-statestore"

class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    """Inventory service implementation"""
    
    def __init__(self):
        self.dapr_client = DaprClient()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize sample inventory data"""
        sample_products = [
            {
                "product_id": "prod-001",
                "product_name": "Laptop Computer",
                "available_quantity": 50,
                "reserved_quantity": 0,
                "total_quantity": 50,
                "unit_price": 999.99
            },
            {
                "product_id": "prod-002", 
                "product_name": "Wireless Mouse",
                "available_quantity": 200,
                "reserved_quantity": 0,
                "total_quantity": 200,
                "unit_price": 29.99
            },
            {
                "product_id": "prod-003",
                "product_name": "Mechanical Keyboard",
                "available_quantity": 75,
                "reserved_quantity": 0,
                "total_quantity": 75,
                "unit_price": 149.99
            }
        ]
        
        for product in sample_products:
            try:
                self.dapr_client.save_state(
                    store_name=STATE_STORE_NAME,
                    key=f"inventory:{product['product_id']}",
                    value=json.dumps(product)
                )
                logger.info(f"Initialized inventory for product: {product['product_id']}")
            except Exception as e:
                logger.error(f"Failed to initialize product {product['product_id']}: {e}")

    def CheckAvailability(self, request, context):
        """Check if product is available in requested quantity"""
        logger.info(f"Checking availability for product: {request.product_id}, quantity: {request.quantity}")
        
        try:
            # Get inventory from state store
            result = self.dapr_client.get_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}"
            )
            
            if not result.data:
                return inventory_pb2.CheckAvailabilityResponse(
                    available=False,
                    available_quantity=0,
                    message="Product not found"
                )
            
            inventory_data = json.loads(result.data)
            available_qty = inventory_data.get("available_quantity", 0)
            
            is_available = available_qty >= request.quantity
            
            return inventory_pb2.CheckAvailabilityResponse(
                available=is_available,
                available_quantity=available_qty,
                message="Available" if is_available else "Insufficient inventory"
            )
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return inventory_pb2.CheckAvailabilityResponse(
                available=False,
                available_quantity=0,
                message="Internal error"
            )

    def ReserveInventory(self, request, context):
        """Reserve inventory for an order"""
        logger.info(f"Reserving inventory for product: {request.product_id}, quantity: {request.quantity}")
        
        try:
            # Get current inventory
            result = self.dapr_client.get_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}"
            )
            
            if not result.data:
                return inventory_pb2.ReserveInventoryResponse(
                    success=False,
                    message="Product not found"
                )
            
            inventory_data = json.loads(result.data)
            available_qty = inventory_data.get("available_quantity", 0)
            
            if available_qty < request.quantity:
                return inventory_pb2.ReserveInventoryResponse(
                    success=False,
                    message="Insufficient inventory"
                )
            
            # Update inventory
            inventory_data["available_quantity"] -= request.quantity
            inventory_data["reserved_quantity"] += request.quantity
            inventory_data["last_updated"] = datetime.now().isoformat()
            
            # Save updated inventory
            self.dapr_client.save_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}",
                value=json.dumps(inventory_data)
            )
            
            # Generate reservation ID
            reservation_id = str(uuid.uuid4())
            
            # Save reservation details
            reservation_data = {
                "reservation_id": reservation_id,
                "product_id": request.product_id,
                "quantity": request.quantity,
                "order_id": request.order_id,
                "customer_id": request.customer_id,
                "created_at": datetime.now().isoformat()
            }
            
            self.dapr_client.save_state(
                store_name=STATE_STORE_NAME,
                key=f"reservation:{reservation_id}",
                value=json.dumps(reservation_data)
            )
            
            # Publish inventory reserved event
            self._publish_inventory_event("inventory.reserved", {
                "product_id": request.product_id,
                "quantity": request.quantity,
                "order_id": request.order_id,
                "reservation_id": reservation_id,
                "available_quantity": inventory_data["available_quantity"]
            })
            
            return inventory_pb2.ReserveInventoryResponse(
                success=True,
                reservation_id=reservation_id,
                message="Inventory reserved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error reserving inventory: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return inventory_pb2.ReserveInventoryResponse(
                success=False,
                message="Internal error"
            )

    def ReleaseInventory(self, request, context):
        """Release reserved inventory"""
        logger.info(f"Releasing inventory for product: {request.product_id}, quantity: {request.quantity}")
        
        try:
            # Get current inventory
            result = self.dapr_client.get_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}"
            )
            
            if not result.data:
                return inventory_pb2.ReleaseInventoryResponse(
                    success=False,
                    message="Product not found"
                )
            
            inventory_data = json.loads(result.data)
            
            # Update inventory
            inventory_data["available_quantity"] += request.quantity
            inventory_data["reserved_quantity"] -= request.quantity
            inventory_data["last_updated"] = datetime.now().isoformat()
            
            # Save updated inventory
            self.dapr_client.save_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}",
                value=json.dumps(inventory_data)
            )
            
            # Remove reservation if provided
            if request.reservation_id:
                self.dapr_client.delete_state(
                    store_name=STATE_STORE_NAME,
                    key=f"reservation:{request.reservation_id}"
                )
            
            # Publish inventory released event
            self._publish_inventory_event("inventory.released", {
                "product_id": request.product_id,
                "quantity": request.quantity,
                "order_id": request.order_id,
                "available_quantity": inventory_data["available_quantity"]
            })
            
            return inventory_pb2.ReleaseInventoryResponse(
                success=True,
                message="Inventory released successfully"
            )
            
        except Exception as e:
            logger.error(f"Error releasing inventory: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return inventory_pb2.ReleaseInventoryResponse(
                success=False,
                message="Internal error"
            )

    def UpdateInventory(self, request, context):
        """Update inventory quantity"""
        logger.info(f"Updating inventory for product: {request.product_id}, change: {request.quantity_change}")
        
        try:
            # Get current inventory
            result = self.dapr_client.get_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}"
            )
            
            if not result.data:
                return inventory_pb2.UpdateInventoryResponse(
                    success=False,
                    message="Product not found"
                )
            
            inventory_data = json.loads(result.data)
            
            # Update quantities
            inventory_data["total_quantity"] += request.quantity_change
            inventory_data["available_quantity"] += request.quantity_change
            inventory_data["last_updated"] = datetime.now().isoformat()
            
            # Ensure quantities don't go negative
            if inventory_data["total_quantity"] < 0:
                inventory_data["total_quantity"] = 0
            if inventory_data["available_quantity"] < 0:
                inventory_data["available_quantity"] = 0
            
            # Save updated inventory
            self.dapr_client.save_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}",
                value=json.dumps(inventory_data)
            )
            
            # Create response inventory object
            inventory_pb = inventory_pb2.ProductInventory(
                product_id=inventory_data["product_id"],
                product_name=inventory_data["product_name"],
                available_quantity=inventory_data["available_quantity"],
                reserved_quantity=inventory_data["reserved_quantity"],
                total_quantity=inventory_data["total_quantity"],
                unit_price=inventory_data["unit_price"],
                last_updated=inventory_data["last_updated"]
            )
            
            # Publish inventory updated event
            self._publish_inventory_event("inventory.updated", {
                "product_id": request.product_id,
                "quantity_change": request.quantity_change,
                "reason": request.reason,
                "new_quantity": inventory_data["available_quantity"]
            })
            
            return inventory_pb2.UpdateInventoryResponse(
                success=True,
                inventory=inventory_pb,
                message="Inventory updated successfully"
            )
            
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return inventory_pb2.UpdateInventoryResponse(
                success=False,
                message="Internal error"
            )

    def GetInventory(self, request, context):
        """Get inventory information for a product"""
        logger.info(f"Getting inventory for product: {request.product_id}")
        
        try:
            # Get inventory from state store
            result = self.dapr_client.get_state(
                store_name=STATE_STORE_NAME,
                key=f"inventory:{request.product_id}"
            )
            
            if not result.data:
                return inventory_pb2.GetInventoryResponse(
                    success=False,
                    message="Product not found"
                )
            
            inventory_data = json.loads(result.data)
            
            # Create response inventory object
            inventory_pb = inventory_pb2.ProductInventory(
                product_id=inventory_data["product_id"],
                product_name=inventory_data["product_name"],
                available_quantity=inventory_data["available_quantity"],
                reserved_quantity=inventory_data["reserved_quantity"],
                total_quantity=inventory_data["total_quantity"],
                unit_price=inventory_data["unit_price"],
                last_updated=inventory_data.get("last_updated", "")
            )
            
            return inventory_pb2.GetInventoryResponse(
                inventory=inventory_pb,
                success=True,
                message="Inventory retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return inventory_pb2.GetInventoryResponse(
                success=False,
                message="Internal error"
            )

    def _publish_inventory_event(self, event_type: str, data: Dict[str, Any]):
        """Publish inventory event to Kafka"""
        try:
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            self.dapr_client.publish_event(
                pubsub_name=PUBSUB_NAME,
                topic_name=event_type,
                data=json.dumps(event)
            )
            
            logger.info(f"Published event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

# Dapr event handlers
app = App()

@app.subscribe(pubsub_name=PUBSUB_NAME, topic='order.created')
def order_created_handler(event):
    """Handle order created events"""
    logger.info("Received order.created event")
    try:
        order_data = json.loads(event.data)
        logger.info(f"Processing order: {order_data.get('order_id')}")
        
        # In a real implementation, you might want to:
        # 1. Validate the order
        # 2. Reserve inventory automatically
        # 3. Send confirmation events
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error processing order.created event: {e}")
        return {"success": False}

@app.subscribe(pubsub_name=PUBSUB_NAME, topic='order.cancelled')
def order_cancelled_handler(event):
    """Handle order cancelled events"""
    logger.info("Received order.cancelled event")
    try:
        order_data = json.loads(event.data)
        logger.info(f"Processing cancelled order: {order_data.get('order_id')}")
        
        # Release any reserved inventory for this order
        # This is a simplified implementation
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error processing order.cancelled event: {e}")
        return {"success": False}

def serve():
    """Start the gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        InventoryService(), server
    )
    
    listen_addr = f'[::]:{GRPC_PORT}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting Inventory Service on {listen_addr}")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down Inventory Service")
        server.stop(0)

if __name__ == '__main__':
    # Generate protobuf files if they don't exist
    import subprocess
    import sys
    
    try:
        subprocess.run([
            sys.executable, '-m', 'grpc_tools.protoc',
            '--proto_path=proto',
            '--python_out=.',
            '--grpc_python_out=.',
            'proto/inventory.proto'
        ], check=True)
        logger.info("Generated protobuf files")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate protobuf files: {e}")
    
    # Start both gRPC server and Dapr app
    import threading
    
    # Start gRPC server in a separate thread
    grpc_thread = threading.Thread(target=serve)
    grpc_thread.daemon = True
    grpc_thread.start()
    
    # Start Dapr app (this will block)
    logger.info("Starting Dapr event handlers")
    app.run(DAPR_HTTP_PORT)

