package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

const (
	notificationServiceURL = "http://localhost:30053" // NodePort service
)

// NotificationRequest represents a notification request
type NotificationRequest struct {
	Type      string                 `json:"type"`
	Recipient string                 `json:"recipient"`
	Subject   string                 `json:"subject"`
	Message   string                 `json:"message"`
	Data      map[string]interface{} `json:"data,omitempty"`
}

// NotificationResponse represents a notification response
type NotificationResponse struct {
	ID        string    `json:"id"`
	Status    string    `json:"status"`
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
}

// HealthResponse represents a health check response
type HealthResponse struct {
	Status    string    `json:"status"`
	Timestamp time.Time `json:"timestamp"`
	Version   string    `json:"version"`
}

func main() {
	fmt.Println("🚀 Event-Driven Microservices Demo - HTTP Client")
	fmt.Println("=================================================")

	// Test 1: Health Check
	fmt.Println("\n🏥 Test 1: Health check...")
	if err := testHealthCheck(); err != nil {
		log.Printf("❌ Health check failed: %v", err)
		return
	}
	fmt.Println("✅ Health check passed!")

	// Test 2: Send Email Notification
	fmt.Println("\n📧 Test 2: Sending email notification...")
	emailReq := NotificationRequest{
		Type:      "email",
		Recipient: "customer@example.com",
		Subject:   "Order Confirmation",
		Message:   "Your order has been confirmed and is being processed.",
		Data: map[string]interface{}{
			"orderId":     "order-123",
			"customerName": "John Doe",
			"totalAmount": 45.49,
		},
	}

	if err := testSendNotification(emailReq); err != nil {
		log.Printf("❌ Email notification failed: %v", err)
		return
	}
	fmt.Println("✅ Email notification sent successfully!")

	// Test 3: Send SMS Notification
	fmt.Println("\n📱 Test 3: Sending SMS notification...")
	smsReq := NotificationRequest{
		Type:      "sms",
		Recipient: "+1234567890",
		Subject:   "Order Update",
		Message:   "Your order #order-123 has been shipped!",
		Data: map[string]interface{}{
			"orderId":      "order-123",
			"trackingCode": "TRK123456789",
		},
	}

	if err := testSendNotification(smsReq); err != nil {
		log.Printf("❌ SMS notification failed: %v", err)
		return
	}
	fmt.Println("✅ SMS notification sent successfully!")

	// Test 4: Send Push Notification
	fmt.Println("\n🔔 Test 4: Sending push notification...")
	pushReq := NotificationRequest{
		Type:      "push",
		Recipient: "user-device-token-123",
		Subject:   "Order Delivered",
		Message:   "Your order has been delivered successfully!",
		Data: map[string]interface{}{
			"orderId":     "order-123",
			"deliveryTime": time.Now().Format(time.RFC3339),
		},
	}

	if err := testSendNotification(pushReq); err != nil {
		log.Printf("❌ Push notification failed: %v", err)
		return
	}
	fmt.Println("✅ Push notification sent successfully!")

	// Test 5: Send Webhook Notification
	fmt.Println("\n🔗 Test 5: Sending webhook notification...")
	webhookReq := NotificationRequest{
		Type:      "webhook",
		Recipient: "https://api.partner.com/webhook",
		Subject:   "Order Status Update",
		Message:   "Order status has been updated",
		Data: map[string]interface{}{
			"orderId":    "order-123",
			"status":     "DELIVERED",
			"customerId": "customer-123",
			"timestamp":  time.Now().Unix(),
		},
	}

	if err := testSendNotification(webhookReq); err != nil {
		log.Printf("❌ Webhook notification failed: %v", err)
		return
	}
	fmt.Println("✅ Webhook notification sent successfully!")

	fmt.Println("\n🎉 All tests completed successfully!")
	fmt.Println("\n💡 Tips:")
	fmt.Println("   - Check the notification service logs for processing details")
	fmt.Println("   - Monitor Kafka topics for event messages")
	fmt.Println("   - Use Dapr dashboard to view service metrics")
}

func testHealthCheck() error {
	resp, err := http.Get(notificationServiceURL + "/health")
	if err != nil {
		return fmt.Errorf("failed to make health check request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check returned status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read health check response: %w", err)
	}

	var healthResp HealthResponse
	if err := json.Unmarshal(body, &healthResp); err != nil {
		return fmt.Errorf("failed to parse health check response: %w", err)
	}

	fmt.Printf("   Status: %s\n", healthResp.Status)
	fmt.Printf("   Version: %s\n", healthResp.Version)
	fmt.Printf("   Timestamp: %s\n", healthResp.Timestamp.Format(time.RFC3339))

	return nil
}

func testSendNotification(req NotificationRequest) error {
	jsonData, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := http.Post(
		notificationServiceURL+"/notify",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return fmt.Errorf("failed to make notification request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("notification request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var notifResp NotificationResponse
	if err := json.Unmarshal(body, &notifResp); err != nil {
		return fmt.Errorf("failed to parse notification response: %w", err)
	}

	fmt.Printf("   Notification ID: %s\n", notifResp.ID)
	fmt.Printf("   Status: %s\n", notifResp.Status)
	fmt.Printf("   Message: %s\n", notifResp.Message)
	fmt.Printf("   Timestamp: %s\n", notifResp.Timestamp.Format(time.RFC3339))

	return nil
}

