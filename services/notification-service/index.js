const express = require('express');
const { DaprClient, DaprServer, CommunicationProtocolEnum } = require('@dapr/dapr');
const winston = require('winston');
const nodemailer = require('nodemailer');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

// Configuration
const DAPR_HTTP_PORT = process.env.DAPR_HTTP_PORT || '3500';
const APP_PORT = process.env.APP_PORT || '3000';
const PUBSUB_NAME = 'kafka-pubsub';
const STATE_STORE_NAME = 'redis-statestore';

// Configure logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});

// Notification channels
class NotificationChannels {
  constructor() {
    this.emailTransporter = this.createEmailTransporter();
  }

  createEmailTransporter() {
    // For demo purposes, use a test email service
    // In production, configure with real SMTP settings
    return nodemailer.createTransporter({
      host: 'smtp.ethereal.email',
      port: 587,
      auth: {
        user: process.env.EMAIL_USER || 'demo@example.com',
        pass: process.env.EMAIL_PASS || 'demo123'
      }
    });
  }

  async sendEmail(to, subject, text, html) {
    try {
      logger.info(`Sending email to: ${to}, subject: ${subject}`);
      
      // For demo purposes, just log the email content
      logger.info('Email content:', { to, subject, text });
      
      // Uncomment below for real email sending
      /*
      const info = await this.emailTransporter.sendMail({
        from: process.env.EMAIL_FROM || 'noreply@demo.com',
        to,
        subject,
        text,
        html
      });
      
      logger.info('Email sent:', info.messageId);
      return info;
      */
      
      return { messageId: `demo-${uuidv4()}`, status: 'sent' };
    } catch (error) {
      logger.error('Failed to send email:', error);
      throw error;
    }
  }

  async sendSMS(to, message) {
    try {
      logger.info(`Sending SMS to: ${to}, message: ${message}`);
      
      // For demo purposes, just log the SMS content
      logger.info('SMS content:', { to, message });
      
      // Uncomment below for real SMS sending with Twilio
      /*
      const client = require('twilio')(
        process.env.TWILIO_ACCOUNT_SID,
        process.env.TWILIO_AUTH_TOKEN
      );
      
      const result = await client.messages.create({
        body: message,
        from: process.env.TWILIO_PHONE_NUMBER,
        to: to
      });
      
      logger.info('SMS sent:', result.sid);
      return result;
      */
      
      return { sid: `demo-${uuidv4()}`, status: 'sent' };
    } catch (error) {
      logger.error('Failed to send SMS:', error);
      throw error;
    }
  }

  async sendPushNotification(userId, title, body, data = {}) {
    try {
      logger.info(`Sending push notification to user: ${userId}, title: ${title}`);
      
      // For demo purposes, just log the push notification
      logger.info('Push notification content:', { userId, title, body, data });
      
      // In production, integrate with Firebase Cloud Messaging, Apple Push Notification Service, etc.
      
      return { notificationId: `demo-${uuidv4()}`, status: 'sent' };
    } catch (error) {
      logger.error('Failed to send push notification:', error);
      throw error;
    }
  }
}

// Notification templates
class NotificationTemplates {
  static getOrderCreatedTemplate(orderData) {
    return {
      email: {
        subject: `Order Confirmation - ${orderData.order_id}`,
        text: `Dear Customer,\n\nYour order ${orderData.order_id} has been created successfully.\nTotal Amount: $${orderData.total_amount}\n\nThank you for your business!`,
        html: `
          <h2>Order Confirmation</h2>
          <p>Dear Customer,</p>
          <p>Your order <strong>${orderData.order_id}</strong> has been created successfully.</p>
          <p>Total Amount: <strong>$${orderData.total_amount}</strong></p>
          <p>Thank you for your business!</p>
        `
      },
      sms: `Order ${orderData.order_id} confirmed! Total: $${orderData.total_amount}. Thank you!`,
      push: {
        title: 'Order Confirmed',
        body: `Your order ${orderData.order_id} has been confirmed.`
      }
    };
  }

  static getOrderUpdatedTemplate(orderData) {
    return {
      email: {
        subject: `Order Update - ${orderData.order_id}`,
        text: `Dear Customer,\n\nYour order ${orderData.order_id} status has been updated to: ${orderData.status}\n\nThank you for your patience!`,
        html: `
          <h2>Order Update</h2>
          <p>Dear Customer,</p>
          <p>Your order <strong>${orderData.order_id}</strong> status has been updated to: <strong>${orderData.status}</strong></p>
          <p>Thank you for your patience!</p>
        `
      },
      sms: `Order ${orderData.order_id} updated: ${orderData.status}`,
      push: {
        title: 'Order Updated',
        body: `Order ${orderData.order_id} is now ${orderData.status}`
      }
    };
  }

  static getPaymentProcessedTemplate(paymentData) {
    return {
      email: {
        subject: `Payment Confirmation - ${paymentData.order_id}`,
        text: `Dear Customer,\n\nYour payment for order ${paymentData.order_id} has been processed successfully.\nAmount: $${paymentData.amount}\n\nThank you!`,
        html: `
          <h2>Payment Confirmation</h2>
          <p>Dear Customer,</p>
          <p>Your payment for order <strong>${paymentData.order_id}</strong> has been processed successfully.</p>
          <p>Amount: <strong>$${paymentData.amount}</strong></p>
          <p>Thank you!</p>
        `
      },
      sms: `Payment of $${paymentData.amount} processed for order ${paymentData.order_id}`,
      push: {
        title: 'Payment Processed',
        body: `Payment confirmed for order ${paymentData.order_id}`
      }
    };
  }

  static getInventoryLowTemplate(inventoryData) {
    return {
      email: {
        subject: `Low Inventory Alert - ${inventoryData.product_name}`,
        text: `Alert: Product ${inventoryData.product_name} (${inventoryData.product_id}) is running low.\nCurrent quantity: ${inventoryData.available_quantity}`,
        html: `
          <h2>Low Inventory Alert</h2>
          <p>Alert: Product <strong>${inventoryData.product_name}</strong> (${inventoryData.product_id}) is running low.</p>
          <p>Current quantity: <strong>${inventoryData.available_quantity}</strong></p>
        `
      },
      sms: `Low inventory: ${inventoryData.product_name} - ${inventoryData.available_quantity} left`,
      push: {
        title: 'Low Inventory Alert',
        body: `${inventoryData.product_name} is running low`
      }
    };
  }
}

// Notification service
class NotificationService {
  constructor() {
    this.daprClient = new DaprClient({ daprHost: 'localhost', daprPort: DAPR_HTTP_PORT });
    this.channels = new NotificationChannels();
    this.notificationHistory = new Map();
  }

  async processOrderCreated(eventData) {
    logger.info('Processing order.created event:', eventData.order_id);
    
    try {
      const orderData = eventData.data;
      const templates = NotificationTemplates.getOrderCreatedTemplate(orderData);
      
      // Send email notification
      if (orderData.customer_email) {
        await this.channels.sendEmail(
          orderData.customer_email,
          templates.email.subject,
          templates.email.text,
          templates.email.html
        );
      }
      
      // Send SMS notification (if phone number available)
      if (orderData.customer_phone) {
        await this.channels.sendSMS(orderData.customer_phone, templates.sms);
      }
      
      // Send push notification
      if (orderData.customer_id) {
        await this.channels.sendPushNotification(
          orderData.customer_id,
          templates.push.title,
          templates.push.body,
          { orderId: orderData.order_id }
        );
      }
      
      // Store notification history
      await this.storeNotificationHistory('order.created', orderData.order_id, {
        email: !!orderData.customer_email,
        sms: !!orderData.customer_phone,
        push: !!orderData.customer_id
      });
      
      logger.info(`Notifications sent for order: ${orderData.order_id}`);
      
    } catch (error) {
      logger.error('Error processing order.created event:', error);
      throw error;
    }
  }

  async processOrderUpdated(eventData) {
    logger.info('Processing order.updated event:', eventData.order_id);
    
    try {
      const orderData = eventData.data;
      const templates = NotificationTemplates.getOrderUpdatedTemplate(orderData);
      
      // Send notifications based on status
      if (orderData.customer_email) {
        await this.channels.sendEmail(
          orderData.customer_email,
          templates.email.subject,
          templates.email.text,
          templates.email.html
        );
      }
      
      if (orderData.customer_phone) {
        await this.channels.sendSMS(orderData.customer_phone, templates.sms);
      }
      
      if (orderData.customer_id) {
        await this.channels.sendPushNotification(
          orderData.customer_id,
          templates.push.title,
          templates.push.body,
          { orderId: orderData.order_id, status: orderData.status }
        );
      }
      
      await this.storeNotificationHistory('order.updated', orderData.order_id, {
        status: orderData.status,
        email: !!orderData.customer_email,
        sms: !!orderData.customer_phone,
        push: !!orderData.customer_id
      });
      
      logger.info(`Order update notifications sent for: ${orderData.order_id}`);
      
    } catch (error) {
      logger.error('Error processing order.updated event:', error);
      throw error;
    }
  }

  async processPaymentProcessed(eventData) {
    logger.info('Processing payment.processed event:', eventData.order_id);
    
    try {
      const paymentData = eventData.data;
      const templates = NotificationTemplates.getPaymentProcessedTemplate(paymentData);
      
      // Send payment confirmation
      if (paymentData.customer_email) {
        await this.channels.sendEmail(
          paymentData.customer_email,
          templates.email.subject,
          templates.email.text,
          templates.email.html
        );
      }
      
      if (paymentData.customer_phone) {
        await this.channels.sendSMS(paymentData.customer_phone, templates.sms);
      }
      
      if (paymentData.customer_id) {
        await this.channels.sendPushNotification(
          paymentData.customer_id,
          templates.push.title,
          templates.push.body,
          { orderId: paymentData.order_id, amount: paymentData.amount }
        );
      }
      
      await this.storeNotificationHistory('payment.processed', paymentData.order_id, {
        amount: paymentData.amount,
        email: !!paymentData.customer_email,
        sms: !!paymentData.customer_phone,
        push: !!paymentData.customer_id
      });
      
      logger.info(`Payment notifications sent for order: ${paymentData.order_id}`);
      
    } catch (error) {
      logger.error('Error processing payment.processed event:', error);
      throw error;
    }
  }

  async processInventoryUpdated(eventData) {
    logger.info('Processing inventory.updated event:', eventData.product_id);
    
    try {
      const inventoryData = eventData.data;
      
      // Send low inventory alerts to admin
      if (inventoryData.available_quantity < 10) {
        const templates = NotificationTemplates.getInventoryLowTemplate(inventoryData);
        
        // Send to admin email
        const adminEmail = process.env.ADMIN_EMAIL || 'admin@demo.com';
        await this.channels.sendEmail(
          adminEmail,
          templates.email.subject,
          templates.email.text,
          templates.email.html
        );
        
        // Send admin push notification
        await this.channels.sendPushNotification(
          'admin',
          templates.push.title,
          templates.push.body,
          { productId: inventoryData.product_id, quantity: inventoryData.available_quantity }
        );
        
        logger.info(`Low inventory alert sent for product: ${inventoryData.product_id}`);
      }
      
    } catch (error) {
      logger.error('Error processing inventory.updated event:', error);
      throw error;
    }
  }

  async storeNotificationHistory(eventType, entityId, metadata) {
    try {
      const historyEntry = {
        id: uuidv4(),
        eventType,
        entityId,
        metadata,
        timestamp: new Date().toISOString()
      };
      
      await this.daprClient.state.save(STATE_STORE_NAME, [
        {
          key: `notification_history:${historyEntry.id}`,
          value: historyEntry
        }
      ]);
      
      logger.info(`Stored notification history: ${historyEntry.id}`);
      
    } catch (error) {
      logger.error('Error storing notification history:', error);
    }
  }

  async getNotificationHistory(entityId) {
    try {
      // This is a simplified implementation
      // In production, you'd implement proper querying
      return [];
    } catch (error) {
      logger.error('Error retrieving notification history:', error);
      return [];
    }
  }
}

// Initialize services
const notificationService = new NotificationService();
const app = express();
const server = new DaprServer({
  serverHost: 'localhost',
  serverPort: APP_PORT,
  communicationProtocol: CommunicationProtocolEnum.HTTP
});

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Notification history endpoint
app.get('/notifications/history/:entityId', async (req, res) => {
  try {
    const history = await notificationService.getNotificationHistory(req.params.entityId);
    res.json({ history });
  } catch (error) {
    logger.error('Error retrieving notification history:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Event handlers
server.pubsub.subscribe(PUBSUB_NAME, 'order.created', async (data) => {
  try {
    await notificationService.processOrderCreated(data);
    return { success: true };
  } catch (error) {
    logger.error('Error handling order.created:', error);
    return { success: false, error: error.message };
  }
});

server.pubsub.subscribe(PUBSUB_NAME, 'order.updated', async (data) => {
  try {
    await notificationService.processOrderUpdated(data);
    return { success: true };
  } catch (error) {
    logger.error('Error handling order.updated:', error);
    return { success: false, error: error.message };
  }
});

server.pubsub.subscribe(PUBSUB_NAME, 'order.cancelled', async (data) => {
  try {
    await notificationService.processOrderUpdated(data);
    return { success: true };
  } catch (error) {
    logger.error('Error handling order.cancelled:', error);
    return { success: false, error: error.message };
  }
});

server.pubsub.subscribe(PUBSUB_NAME, 'payment.processed', async (data) => {
  try {
    await notificationService.processPaymentProcessed(data);
    return { success: true };
  } catch (error) {
    logger.error('Error handling payment.processed:', error);
    return { success: false, error: error.message };
  }
});

server.pubsub.subscribe(PUBSUB_NAME, 'inventory.updated', async (data) => {
  try {
    await notificationService.processInventoryUpdated(data);
    return { success: true };
  } catch (error) {
    logger.error('Error handling inventory.updated:', error);
    return { success: false, error: error.message };
  }
});

// Start servers
async function start() {
  try {
    // Start Express server
    app.listen(APP_PORT, () => {
      logger.info(`Notification Service HTTP server listening on port ${APP_PORT}`);
    });
    
    // Start Dapr server
    await server.start();
    logger.info('Notification Service Dapr server started');
    
  } catch (error) {
    logger.error('Failed to start Notification Service:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  logger.info('Shutting down Notification Service...');
  await server.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  logger.info('Shutting down Notification Service...');
  await server.stop();
  process.exit(0);
});

// Start the service
start().catch((error) => {
  logger.error('Failed to start service:', error);
  process.exit(1);
});

