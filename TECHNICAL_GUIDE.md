# Technical Guide: Real-Time Aircraft Landing Tracker for Kisumu International Airport

## System Architecture

### Overview
This system implements a serverless aircraft landing detection solution using AWS services and the OpenSky Network API. The architecture follows cloud engineering best practices for scalability, security, and cost optimization.

### Core Components

Data Ingestion Layer
- OpenSky Network API provides real-time aircraft position data
- AWS Lambda function processes API responses every 2 minutes
- EventBridge scheduler ensures reliable execution

Processing Layer
- Python-based landing detection algorithm
- Geospatial calculations for airport proximity
- State comparison logic for landing identification

Storage Layer
- DynamoDB tables for aircraft state and landing records
- TTL-enabled records for automatic cleanup
- Global Secondary Index for efficient queries

Notification Layer
- SNS topic for real-time landing alerts
- Email notifications for detected landings

## Landing Detection Algorithm

### Detection Criteria
The system identifies aircraft landings using multiple parameters:

```python
def detect_landing(current_aircraft, previous_state):
    current_altitude_ft = current_aircraft['baro_altitude'] * 3.28084
    previous_altitude_ft = previous_state['baro_altitude'] * 3.28084
    
    conditions = [
        current_altitude_ft < LANDING_ALTITUDE_THRESHOLD,  # Below 1000ft
        current_aircraft['vertical_rate'] < -1,            # Descending > 1 m/s
        previous_altitude_ft > LANDING_ALTITUDE_THRESHOLD, # Was higher
        not current_aircraft['on_ground'],                 # Not on ground
        current_aircraft['distance_to_airport'] <= 2.0    # Within 2km
    ]
    
    return all(conditions)
```

### Geospatial Calculations
Airport proximity uses the Haversine formula for accurate distance calculation:

```python
def calculate_distance(lat1, lon1, lat2, lon2):
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return c * 6371  # Earth radius in km
```

### State Management
Aircraft state tracking prevents duplicate landing detections:

- Current state stored in DynamoDB with 1-hour TTL
- Previous state comparison for landing validation
- Unique landing IDs prevent duplicate records

## Data Flow

### 1. Scheduled Execution
EventBridge triggers Lambda function every 2 minutes using cron expression:
```
rate(2 minutes)
```

### 2. Data Retrieval
Lambda function queries OpenSky API with bounding box parameters:
```python
params = {
    'lamin': lat - offset,
    'lomin': lon - offset, 
    'lamax': lat + offset,
    'lomax': lon + offset
}
```

### 3. Processing Pipeline
For each aircraft in the response:
1. Calculate distance to Kisumu airport
2. Filter aircraft within detection radius (5km)
3. Retrieve previous state from DynamoDB
4. Apply landing detection algorithm
5. Update current state in DynamoDB
6. Record landing if detected

### 4. Notification
When landing detected:
1. Store landing record in DynamoDB
2. Publish structured message to SNS topic
3. Email notification sent to subscribers

## Security Implementation

### IAM Least Privilege
Lambda execution role includes minimal required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem", 
        "dynamodb:UpdateItem"
      ],
      "Resource": ["arn:aws:dynamodb:*:*:table/aircraft-*"]
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:*:*:landing-notifications"
    }
  ]
}
```

### Data Encryption
- DynamoDB tables use server-side encryption
- SNS messages encrypted in transit
- Lambda environment variables for sensitive data

### Network Security
- Lambda function operates in AWS managed VPC
- HTTPS-only communication with OpenSky API
- No inbound network access required

## Performance Optimization

### Lambda Configuration
- Runtime: Python 3.11 for optimal performance
- Memory: 256MB sufficient for processing workload
- Timeout: 60 seconds accommodates API latency
- Concurrent executions: Limited to prevent API rate limiting

### DynamoDB Optimization
- Pay-per-request billing for variable workload
- TTL automatic cleanup reduces storage costs
- GSI enables efficient aircraft history queries
- Partition key design prevents hot partitions

### API Rate Management
- Optional OpenSky authentication for higher limits
- Bounding box queries reduce response size
- Error handling with exponential backoff
- Request timeout prevents Lambda timeouts

## Monitoring and Observability

### CloudWatch Integration
- Lambda function logs for debugging
- Custom metrics for landing detection rate
- Alarms for function failures or API errors
- Log retention set to 14 days for cost control

### Operational Metrics
Track key performance indicators:
- Aircraft detection count per execution
- Landing detection accuracy
- API response times
- DynamoDB read/write capacity utilization

## Deployment Process

### Prerequisites
```bash
# Install required tools
aws configure  # Configure AWS credentials
terraform --version  # Verify Terraform installation
```

### Infrastructure Deployment
```bash
# Clone repository
git clone https://github.com/Copubah/kisumu-aircraft-tracker.git
cd kisumu-aircraft-tracker

# Configure variables
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy infrastructure
./scripts/deploy.sh
```

### Post-Deployment Configuration
1. Confirm SNS email subscription
2. Verify Lambda function execution in CloudWatch
3. Test landing detection with sample data
4. Configure CloudWatch alarms for monitoring

## Cost Optimization

### Resource Sizing
- Lambda: 256MB memory, 60-second timeout
- DynamoDB: Pay-per-request billing
- SNS: Pay-per-message pricing
- CloudWatch: 14-day log retention

### Estimated Monthly Costs (US East 1)
- Lambda: approximately $2.50 (21,600 invocations/month)
- DynamoDB: approximately $1.25 (read/write operations)
- SNS: approximately $0.50 (email notifications)
- CloudWatch: approximately $0.75 (logs and metrics)
- Total: approximately $5.00/month

## Troubleshooting

### Common Issues

Lambda Timeout Errors
- Check OpenSky API response times
- Verify network connectivity
- Review CloudWatch logs for bottlenecks

Missing Landing Detections
- Validate detection algorithm parameters
- Check aircraft state data quality
- Verify DynamoDB write operations

High False Positive Rate
- Adjust altitude threshold parameters
- Refine vertical rate sensitivity
- Review airport proximity calculations

### Debug Commands
```bash
# View Lambda logs
aws logs tail /aws/lambda/kisumu-aircraft-tracker-landing-tracker --follow

# Check DynamoDB items
aws dynamodb scan --table-name kisumu-aircraft-tracker-aircraft-state

# Test SNS notifications
aws sns publish --topic-arn <topic-arn> --message "Test notification"
```

## Scaling Considerations

### Horizontal Scaling
- Lambda automatically scales with concurrent executions
- DynamoDB auto-scaling for increased throughput
- SNS handles high message volumes natively

### Multi-Airport Extension
- Parameterize airport coordinates
- Deploy separate stacks per airport
- Centralized monitoring dashboard

### Enhanced Features
- Real-time WebSocket notifications
- Historical landing analytics
- Machine learning-based prediction
- Integration with air traffic control systems

## Compliance and Governance

### Data Privacy
- No personally identifiable information stored
- Aircraft registration data publicly available
- GDPR compliance through data minimization

### Audit Trail
- CloudTrail logs all API calls
- DynamoDB item-level logging available
- SNS message delivery status tracking

### Backup and Recovery
- DynamoDB point-in-time recovery enabled
- Infrastructure as Code for disaster recovery
- Cross-region replication for high availability