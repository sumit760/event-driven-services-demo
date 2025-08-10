package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"time"

	"github.com/dapr/go-sdk/client"
	"github.com/google/uuid"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/timestamppb"

	pb "github.com/sumit760/event-driven-services-demo/services/order-service/proto"
)

const (
	port           = ":50051"
	daprHTTPPort   = "3500"
	pubsubName     = "kafka-pubsub"
	stateStoreName = "redis-statestore"
)

// OrderService implements the gRPC OrderService
type OrderService struct {
	pb.UnimplementedOrderServiceServer
	daprClient client.Client
}

// OrderEvent represents an order event for Kafka
type OrderEvent struct {
	EventID     string    `json:"event_id"`
	EventType   string    `json:"event_type"`
	OrderID     string    `json:"order_id"`
	CustomerID  string    `json:"customer_id"`
	TotalAmount float64   `json:"total_amount"`
	Status      string    `json:"status"`
	Timestamp   time.Time `json:"timestamp"`
	Data        *pb.Order `json:"data"`
}

// NewOrderService creates a new OrderService instance
func NewOrderService() *OrderService {
	daprClient, err := client.NewClient()
	if err != nil {
		log.Fatalf("Failed to create Dapr client: %v", err)
	}

	return &OrderService{
		daprClient: daprClient,
	}
}

// CreateOrder handles order creation
func (s *OrderService) CreateOrder(ctx context.Context, req *pb.CreateOrderRequest) (*pb.CreateOrderResponse, error) {
	log.Printf("Creating order for customer: %s", req.CustomerId)

	// Generate order ID
	orderID := uuid.New().String()
	now := time.Now()

	// Calculate total amount
	var totalAmount float64
	for _, item := range req.Items {
		item.TotalPrice = float64(item.Quantity) * item.UnitPrice
		totalAmount += item.TotalPrice
	}

	// Create order
	order := &pb.Order{
		OrderId:         orderID,
		CustomerId:      req.CustomerId,
		CustomerEmail:   req.CustomerEmail,
		Items:           req.Items,
		TotalAmount:     totalAmount,
		Status:          pb.OrderStatus_ORDER_STATUS_PENDING,
		CreatedAt:       timestamppb.New(now).String(),
		UpdatedAt:       timestamppb.New(now).String(),
		ShippingAddress: req.ShippingAddress,
		PaymentMethod:   req.PaymentMethod,
	}

	// Save order to state store
	orderData, err := json.Marshal(order)
	if err != nil {
		log.Printf("Failed to marshal order: %v", err)
		return &pb.CreateOrderResponse{
			Success: false,
			Message: "Failed to create order",
		}, err
	}

	err = s.daprClient.SaveState(ctx, stateStoreName, orderID, orderData, nil)
	if err != nil {
		log.Printf("Failed to save order to state store: %v", err)
		return &pb.CreateOrderResponse{
			Success: false,
			Message: "Failed to save order",
		}, err
	}

	// Check inventory availability via Dapr service invocation
	inventoryAvailable, err := s.checkInventoryAvailability(ctx, req.Items)
	if err != nil {
		log.Printf("Failed to check inventory: %v", err)
		return &pb.CreateOrderResponse{
			Success: false,
			Message: "Failed to check inventory availability",
		}, err
	}

	if !inventoryAvailable {
		order.Status = pb.OrderStatus_ORDER_STATUS_FAILED
		return &pb.CreateOrderResponse{
			Order:   order,
			Success: false,
			Message: "Insufficient inventory",
		}, nil
	}

	// Publish order created event
	event := OrderEvent{
		EventID:     uuid.New().String(),
		EventType:   "order.created",
		OrderID:     orderID,
		CustomerID:  req.CustomerId,
		TotalAmount: totalAmount,
		Status:      "pending",
		Timestamp:   now,
		Data:        order,
	}

	err = s.publishEvent(ctx, "order.created", event)
	if err != nil {
		log.Printf("Failed to publish order created event: %v", err)
		// Don't fail the order creation if event publishing fails
	}

	log.Printf("Order created successfully: %s", orderID)
	return &pb.CreateOrderResponse{
		Order:   order,
		Success: true,
		Message: "Order created successfully",
	}, nil
}

// GetOrder retrieves an order by ID
func (s *OrderService) GetOrder(ctx context.Context, req *pb.GetOrderRequest) (*pb.GetOrderResponse, error) {
	log.Printf("Getting order: %s", req.OrderId)

	// Get order from state store
	result, err := s.daprClient.GetState(ctx, stateStoreName, req.OrderId, nil)
	if err != nil {
		log.Printf("Failed to get order from state store: %v", err)
		return &pb.GetOrderResponse{
			Success: false,
			Message: "Failed to retrieve order",
		}, err
	}

	if len(result.Value) == 0 {
		return &pb.GetOrderResponse{
			Success: false,
			Message: "Order not found",
		}, nil
	}

	var order pb.Order
	err = json.Unmarshal(result.Value, &order)
	if err != nil {
		log.Printf("Failed to unmarshal order: %v", err)
		return &pb.GetOrderResponse{
			Success: false,
			Message: "Failed to parse order data",
		}, err
	}

	return &pb.GetOrderResponse{
		Order:   &order,
		Success: true,
		Message: "Order retrieved successfully",
	}, nil
}

// UpdateOrder updates an existing order
func (s *OrderService) UpdateOrder(ctx context.Context, req *pb.UpdateOrderRequest) (*pb.UpdateOrderResponse, error) {
	log.Printf("Updating order: %s", req.OrderId)

	// Get existing order
	getResp, err := s.GetOrder(ctx, &pb.GetOrderRequest{OrderId: req.OrderId})
	if err != nil || !getResp.Success {
		return &pb.UpdateOrderResponse{
			Success: false,
			Message: "Order not found",
		}, err
	}

	order := getResp.Order
	oldStatus := order.Status
	order.Status = req.Status
	order.UpdatedAt = timestamppb.New(time.Now()).String()

	// Save updated order
	orderData, err := json.Marshal(order)
	if err != nil {
		return &pb.UpdateOrderResponse{
			Success: false,
			Message: "Failed to update order",
		}, err
	}

	err = s.daprClient.SaveState(ctx, stateStoreName, req.OrderId, orderData, nil)
	if err != nil {
		return &pb.UpdateOrderResponse{
			Success: false,
			Message: "Failed to save updated order",
		}, err
	}

	// Publish order updated event if status changed
	if oldStatus != req.Status {
		event := OrderEvent{
			EventID:     uuid.New().String(),
			EventType:   "order.updated",
			OrderID:     req.OrderId,
			CustomerID:  order.CustomerId,
			TotalAmount: order.TotalAmount,
			Status:      req.Status.String(),
			Timestamp:   time.Now(),
			Data:        order,
		}

		err = s.publishEvent(ctx, "order.updated", event)
		if err != nil {
			log.Printf("Failed to publish order updated event: %v", err)
		}
	}

	return &pb.UpdateOrderResponse{
		Order:   order,
		Success: true,
		Message: "Order updated successfully",
	}, nil
}

// CancelOrder cancels an existing order
func (s *OrderService) CancelOrder(ctx context.Context, req *pb.CancelOrderRequest) (*pb.CancelOrderResponse, error) {
	log.Printf("Cancelling order: %s", req.OrderId)

	// Update order status to cancelled
	updateResp, err := s.UpdateOrder(ctx, &pb.UpdateOrderRequest{
		OrderId: req.OrderId,
		Status:  pb.OrderStatus_ORDER_STATUS_CANCELLED,
		Notes:   req.Reason,
	})

	if err != nil || !updateResp.Success {
		return &pb.CancelOrderResponse{
			Success: false,
			Message: "Failed to cancel order",
		}, err
	}

	// Publish order cancelled event
	event := OrderEvent{
		EventID:    uuid.New().String(),
		EventType:  "order.cancelled",
		OrderID:    req.OrderId,
		Status:     "cancelled",
		Timestamp:  time.Now(),
		Data:       updateResp.Order,
	}

	err = s.publishEvent(ctx, "order.cancelled", event)
	if err != nil {
		log.Printf("Failed to publish order cancelled event: %v", err)
	}

	return &pb.CancelOrderResponse{
		Success: true,
		Message: "Order cancelled successfully",
	}, nil
}

// ListOrders lists orders for a customer
func (s *OrderService) ListOrders(ctx context.Context, req *pb.ListOrdersRequest) (*pb.ListOrdersResponse, error) {
	log.Printf("Listing orders for customer: %s", req.CustomerId)

	// This is a simplified implementation
	// In a real system, you'd implement proper pagination and filtering
	return &pb.ListOrdersResponse{
		Orders:        []*pb.Order{},
		NextPageToken: "",
		TotalCount:    0,
	}, nil
}

// checkInventoryAvailability checks if inventory is available for order items
func (s *OrderService) checkInventoryAvailability(ctx context.Context, items []*pb.OrderItem) (bool, error) {
	// Call inventory service via Dapr service invocation
	for _, item := range items {
		req := map[string]interface{}{
			"product_id": item.ProductId,
			"quantity":   item.Quantity,
		}

		reqData, err := json.Marshal(req)
		if err != nil {
			return false, err
		}

		resp, err := s.daprClient.InvokeMethod(ctx, "inventory-service", "check-availability", "POST", reqData)
		if err != nil {
			log.Printf("Failed to call inventory service: %v", err)
			// For demo purposes, assume inventory is available if service is not reachable
			return true, nil
		}

		var result map[string]interface{}
		err = json.Unmarshal(resp, &result)
		if err != nil {
			return false, err
		}

		if available, ok := result["available"].(bool); !ok || !available {
			return false, nil
		}
	}

	return true, nil
}

// publishEvent publishes an event to Kafka via Dapr
func (s *OrderService) publishEvent(ctx context.Context, topic string, event OrderEvent) error {
	eventData, err := json.Marshal(event)
	if err != nil {
		return err
	}

	err = s.daprClient.PublishEvent(ctx, pubsubName, topic, eventData)
	if err != nil {
		return fmt.Errorf("failed to publish event to topic %s: %w", topic, err)
	}

	log.Printf("Published event %s to topic %s", event.EventID, topic)
	return nil
}

func main() {
	log.Println("Starting Order Service...")

	// Create gRPC server
	lis, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	s := grpc.NewServer()
	orderService := NewOrderService()
	pb.RegisterOrderServiceServer(s, orderService)

	log.Printf("Order Service listening on port %s", port)
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}

