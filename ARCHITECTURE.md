# System Architecture

## Overview

The Aircraft Landing Tracker is a serverless system built on AWS that monitors aircraft movements around Kisumu International Airport and detects landing events in real-time.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Aircraft Landing Tracker                              │
│                         Kisumu International Airport                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────────────┐
│   EventBridge   │    │   AWS Lambda     │    │        OpenSky Network         │
│   Scheduler     │───▶│  Landing Tracker │───▶│         REST API               │
│  (2 minutes)    │    │   (Python 3.11) │    │    (Aircraft Position Data)    │
└─────────────────┘    └──────────────────┘    └─────────────────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │   Landing Detection  │
                    │      Algorithm       │
                    │                      │
                    │ • Altitude < 1000ft  │
                    │ • Vertical Rate < -1 │
                    │ • Distance < 2km     │
                    │ • State Comparison   │
                    └──────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   DynamoDB      │ │   DynamoDB      │ │   Amazon SNS    │
    │ Aircraft State  │ │    Landings     │ │  Notifications  │
    │                 │ │                 │ │                 │
    │ • Current State │ │ • Landing Events│ │ • Email Alerts  │
    │ • TTL: 1 hour   │ │ • Historical    │ │ • JSON Payload  │
    │ • Encrypted     │ │ • GSI Index     │ │ • Topic ARN     │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │  Email Endpoint │
                                            │   Subscriber    │
                                            └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Monitoring & Logging                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│  CloudWatch Logs          │  CloudWatch Metrics      │  AWS X-Ray Tracing      │
│  • Lambda Execution       │  • Function Duration     │  • Request Tracing      │
│  • Error Tracking         │  • Memory Usage          │  • Performance Analysis │
│  • 14-day Retention       │  • Invocation Count      │  • Dependency Mapping   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Data Flow

1. Trigger: EventBridge rule triggers Lambda function every 2 minutes
2. Data Retrieval: Lambda queries OpenSky API for aircraft within 5km of Kisumu airport
3. State Management: Current aircraft positions stored in DynamoDB with TTL
4. Landing Detection: Algorithm compares current vs previous state to identify landings
5. Notification: SNS publishes landing events to email subscribers
6. Logging: All activities logged to CloudWatch for monitoring

### Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Security Layers                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   IAM Roles     │    │   Encryption    │    │ Network Security│            │
│  │                 │    │                 │    │                 │            │
│  │ • Lambda Role   │    │ • DynamoDB SSE  │    │ • HTTPS Only    │            │
│  │ • Least Privilege│   │ • SNS Encryption│    │ • VPC Endpoints │            │
│  │ • Resource ARNs │    │ • TLS in Transit│    │ • No Public IPs │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Geographic Coverage

```
                    Kisumu International Airport
                           (-0.0861, 34.7289)
                                  ●
                              ┌───┼───┐
                              │   │   │
                          ┌───┼───●───┼───┐
                          │   │       │   │  Detection Radius
                          │   │  5km   │   │     (5km)
                          └───┼───────┼───┘
                              │       │
                              └───────┘
                                  │
                            Landing Zone
                             (2km radius)
```

## Technology Stack

### AWS Services
- AWS Lambda: Serverless compute for processing logic
- Amazon DynamoDB: NoSQL database for state and landing storage
- Amazon EventBridge: Event-driven scheduling service
- Amazon SNS: Notification service for alerts
- Amazon CloudWatch: Monitoring and logging service

### External Services
- OpenSky Network API: Real-time aircraft position data
- HTTPS/TLS: Secure communication protocols

### Development Tools
- Terraform: Infrastructure as Code
- Python 3.11: Lambda runtime environment
- Git: Version control system

## Scalability Considerations

### Horizontal Scaling
- Lambda automatically scales with concurrent executions
- DynamoDB auto-scaling for increased throughput
- SNS handles high message volumes natively

### Performance Optimization
- Efficient API queries using geographic bounding boxes
- DynamoDB TTL for automatic data cleanup
- Lambda memory optimization (256MB)
- Connection pooling for external API calls

### Cost Management
- Pay-per-request DynamoDB billing
- Lambda execution-based pricing
- CloudWatch log retention policies
- SNS pay-per-message model

## Disaster Recovery

### Data Backup
- DynamoDB point-in-time recovery enabled
- Infrastructure as Code for rapid rebuilding
- Cross-region replication capabilities

### Monitoring and Alerting
- CloudWatch alarms for function failures
- SNS delivery status tracking
- Lambda error rate monitoring
- API availability checks

## Compliance and Governance

### Data Privacy
- No personally identifiable information stored
- Aircraft registration data is publicly available
- GDPR compliance through data minimization

### Audit Trail
- CloudTrail logs all API calls
- DynamoDB item-level logging available
- SNS message delivery confirmation
- Lambda execution history tracking