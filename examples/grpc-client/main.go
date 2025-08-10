package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "github.com/sumit760/event-driven-services-demo/services/order-service/proto"
)

const (
	orderServiceAddress = "localhost:30051" // NodePort service
)

func main() {
	fmt.Println("🚀 Event-Driven Microservices Demo - gRPC Client")
	fmt.Println("================================================")

	// Connect to Order Service
	conn, err := grpc.Dial(orderServiceAddress, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("Failed to connect to order service: %v", err)
	}
	defer conn.Close()

	client := pb.NewOrderServiceClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Test 1: Create Order
	fmt.Println("\n📦 Test 1: Creating a new order...")
	createReq := &pb.CreateOrderRequest{
		CustomerId: "customer-123",
		Items: []*pb.OrderItem{
			{
				ProductId: "product-456",
				Quantity:  2,
				Price:     29.99,
			},
			{
				ProductId: "product-789",
				Quantity:  1,
				Price:     15.50,
			},
		},
	}

	createResp, err := client.CreateOrder(ctx, createReq)
	if err != nil {
		log.Printf("❌ Failed to create order: %v", err)
		return
	}

	fmt.Printf("✅ Order created successfully!\n")
	fmt.Printf("   Order ID: %s\n", createResp.Order.Id)
	fmt.Printf("   Status: %s\n", createResp.Order.Status)
	fmt.Printf("   Total: $%.2f\n", createResp.Order.TotalAmount)
	fmt.Printf("   Items: %d\n", len(createResp.Order.Items))

	orderId := createResp.Order.Id

	// Test 2: Get Order
	fmt.Println("\n📋 Test 2: Retrieving the order...")
	getReq := &pb.GetOrderRequest{
		OrderId: orderId,
	}

	getResp, err := client.GetOrder(ctx, getReq)
	if err != nil {
		log.Printf("❌ Failed to get order: %v", err)
		return
	}

	fmt.Printf("✅ Order retrieved successfully!\n")
	fmt.Printf("   Order ID: %s\n", getResp.Order.Id)
	fmt.Printf("   Customer ID: %s\n", getResp.Order.CustomerId)
	fmt.Printf("   Status: %s\n", getResp.Order.Status)
	fmt.Printf("   Created: %s\n", getResp.Order.CreatedAt.AsTime().Format(time.RFC3339))

	// Test 3: Update Order Status
	fmt.Println("\n🔄 Test 3: Updating order status...")
	updateReq := &pb.UpdateOrderStatusRequest{
		OrderId: orderId,
		Status:  "PROCESSING",
	}

	updateResp, err := client.UpdateOrderStatus(ctx, updateReq)
	if err != nil {
		log.Printf("❌ Failed to update order status: %v", err)
		return
	}

	fmt.Printf("✅ Order status updated successfully!\n")
	fmt.Printf("   Order ID: %s\n", updateResp.Order.Id)
	fmt.Printf("   New Status: %s\n", updateResp.Order.Status)
	fmt.Printf("   Updated: %s\n", updateResp.Order.UpdatedAt.AsTime().Format(time.RFC3339))

	// Test 4: List Orders
	fmt.Println("\n📜 Test 4: Listing orders for customer...")
	listReq := &pb.ListOrdersRequest{
		CustomerId: "customer-123",
		PageSize:   10,
		PageToken:  "",
	}

	listResp, err := client.ListOrders(ctx, listReq)
	if err != nil {
		log.Printf("❌ Failed to list orders: %v", err)
		return
	}

	fmt.Printf("✅ Orders listed successfully!\n")
	fmt.Printf("   Total orders: %d\n", len(listResp.Orders))
	for i, order := range listResp.Orders {
		fmt.Printf("   Order %d: %s (Status: %s, Total: $%.2f)\n", 
			i+1, order.Id, order.Status, order.TotalAmount)
	}

	// Test 5: Cancel Order
	fmt.Println("\n❌ Test 5: Cancelling the order...")
	cancelReq := &pb.CancelOrderRequest{
		OrderId: orderId,
		Reason:  "Customer requested cancellation",
	}

	cancelResp, err := client.CancelOrder(ctx, cancelReq)
	if err != nil {
		log.Printf("❌ Failed to cancel order: %v", err)
		return
	}

	fmt.Printf("✅ Order cancelled successfully!\n")
	fmt.Printf("   Order ID: %s\n", cancelResp.Order.Id)
	fmt.Printf("   Status: %s\n", cancelResp.Order.Status)
	fmt.Printf("   Reason: %s\n", cancelResp.Message)

	fmt.Println("\n🎉 All tests completed successfully!")
	fmt.Println("\n💡 Tips:")
	fmt.Println("   - Check the notification service logs for event processing")
	fmt.Println("   - Monitor Dapr dashboard for service communication")
	fmt.Println("   - Use 'kubectl logs' to view service logs")
}

