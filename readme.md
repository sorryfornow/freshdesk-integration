# WordPress + Freshdesk + Xero Integration System

A complete integration solution that connects WordPress forms, Freshdesk customer service system, and Xero accounting software to enable automated processing of customer requests and billing.

## 🚀 Features

- **WordPress Form Integration**: Supports multiple form plugins and custom forms
- **Freshdesk Automation**: Automatic ticket creation and customer management
- **Xero Invoice Generation**: Automatic invoice creation based on resolved tickets
- **Webhook Support**: Real-time data synchronization
- **Security Authentication**: API key and signature verification
- **Comprehensive Logging**: Complete operation logs with detailed debugging
- **Robust Error Handling**: Advanced error handling and recovery mechanisms
- **Field Mapping**: Intelligent field mapping between different systems

## 📋 System Requirements

- **Python**: 3.7+ (3.9+ recommended)
- **Anaconda**: Recommended for environment management
- **WordPress**: 5.0+
- **Freshdesk**: Garden plan or higher (for webhook functionality)
- **Xero**: Standard plan or higher

## 🛠️ Installation Guide

### 1. Create Anaconda Environment

```bash
# Create new environment
conda create -n freshdesk-integration python=3.9

# Activate environment
conda activate freshdesk-integration

# Verify Python version
python --version
```

### 2. Clone or Create Project

```bash
# Create project directory
mkdir freshdesk-integration-project
cd freshdesk-integration-project

# Create necessary directories
mkdir static templates logs
```

### 3. Install Dependencies

Create a `requirements.txt` file:

```txt
Flask==2.3.3
python-dotenv==1.0.0
requests==2.31.0
flask-cors==4.0.0
```

Install dependencies:

```bash
# Install all dependencies
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in your project root:

```env
# Freshdesk Configuration
FRESHDESK_DOMAIN=your-domain.freshdesk.com
FRESHDESK_API_KEY=your_freshdesk_api_key

# Webhook Security Configuration
WEBHOOK_SECRET=your_random_webhook_secret_at_least_32_chars

# Xero API Configuration
XERO_CLIENT_ID=your_xero_client_id
XERO_CLIENT_SECRET=your_xero_client_secret
XERO_REDIRECT_URI=http://localhost:5001/xero/callback
XERO_SCOPE=accounting.transactions

# Flask Application Configuration
SECRET_KEY=your_flask_secret_key_at_least_32_chars
FLASK_ENV=development
FLASK_DEBUG=True
PORT=5001
HOST=0.0.0.0

# WordPress Configuration
WP_FORM_ID=107
WP_SITE_URL=https://your-wordpress-site.com

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Security Configuration
ALLOWED_ORIGINS=https://your-wordpress-site.com,http://localhost:3000

# Email Notifications (Optional)
NOTIFICATION_EMAIL=admin@yourcompany.com
```

### 5. Obtain API Keys

#### Freshdesk API Key
1. Login to your Freshdesk admin panel
2. Go to **Admin → Profile Settings**
3. Find **Your API Key** on the right side
4. Copy the API key to your `.env` file

#### Xero API Configuration
1. Visit [Xero Developer Portal](https://developer.xero.com/)
2. Create a new app
3. Get Client ID and Client Secret
4. Set redirect URI: `http://localhost:5001/xero/callback`
5. Add the credentials to your `.env` file

### 6. Start the Application

```bash
# Check configuration
python app.py

# Or run with specific environment
export FLASK_ENV=development
python app.py
```

### 7. WordPress Integration

#### Method 1: Custom Form Integration

Create a WordPress form that sends data to your Flask endpoint:

```html
<form id="equipment-repair-form" method="post">
    <input type="text" name="contact_name" placeholder="Your Name" required>
    <input type="email" name="contact_email" placeholder="Email" required>
    <input type="tel" name="contact_phone" placeholder="Phone">
    <input type="text" name="business_name" placeholder="Business Name">
    <select name="equipment_type">
        <option value="Desktop">Desktop</option>
        <option value="Laptop">Laptop</option>
        <option value="Printer">Printer</option>
    </select>
    <input type="text" name="equipment_brand" placeholder="Brand">
    <input type="text" name="equipment_model" placeholder="Model">
    <textarea name="fault_description" placeholder="Describe the issue" required></textarea>
    <button type="submit">Submit Request</button>
</form>

<script>
document.getElementById('equipment-repair-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const data = Object.fromEntries(formData);
    
    // Add additional fields
    data.tags = [data.equipment_type];
    data.custom_fields = {
        equipment_brand: data.equipment_brand,
        equipment_model: data.equipment_model,
        internal_ticket_id: 'WP' + Date.now()
    };
    
    fetch('http://your-flask-app.com:5001/webhook/wordpress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Request submitted successfully!');
        } else {
            alert('Error: ' + data.error);
        }
    });
});
</script>
```

#### Method 2: Plugin Integration

Create a WordPress plugin file:

```php
<?php
/**
 * Plugin Name: Freshdesk Integration
 * Description: Integrates WordPress forms with Freshdesk
 * Version: 1.0.0
 */

add_action('wp_ajax_submit_repair_request', 'handle_repair_request');
add_action('wp_ajax_nopriv_submit_repair_request', 'handle_repair_request');

function handle_repair_request() {
    $data = array(
        'name' => sanitize_text_field($_POST['contact_name']),
        'email' => sanitize_email($_POST['contact_email']),
        'phone' => sanitize_text_field($_POST['contact_phone']),
        'company' => sanitize_text_field($_POST['business_name']),
        'subject' => 'Equipment Repair Request - ' . sanitize_text_field($_POST['equipment_type']),
        'message' => sanitize_textarea_field($_POST['fault_description']),
        'custom_fields' => array(
            'equipment_brand' => sanitize_text_field($_POST['equipment_brand']),
            'equipment_model' => sanitize_text_field($_POST['equipment_model']),
            'internal_ticket_id' => 'WP' . time()
        ),
        'tags' => array(sanitize_text_field($_POST['equipment_type']))
    );
    
    $response = wp_remote_post('http://your-flask-app.com:5001/webhook/wordpress', array(
        'headers' => array('Content-Type' => 'application/json'),
        'body' => json_encode($data),
        'timeout' => 30
    ));
    
    if (is_wp_error($response)) {
        wp_send_json_error('Failed to submit request');
    } else {
        wp_send_json_success('Request submitted successfully');
    }
}
?>
```

## 🔧 Configuration Details

### Freshdesk Webhook Setup

1. In Freshdesk, create a new automation rule:
   - **Admin → Automations → New rule**
   - Set trigger conditions (e.g., ticket created, updated, resolved)
   - In Actions, select **Trigger webhook**
   - Set webhook URL: `http://your-domain:5001/webhook/freshdesk`
   - Add webhook secret if configured

### Field Mapping System

The system automatically maps WordPress form fields to Freshdesk requirements:

```
WordPress Field → Internal Field → Freshdesk Field
email          → contact_email  → email
name           → contact_name   → name
phone          → contact_phone  → phone
company        → business_name  → company
```

### Xero Authorization Setup

1. Visit `http://localhost:5001/xero/auth`
2. Complete OAuth authorization flow
3. Access token will be stored for invoice creation

## 📊 Usage Guide

### Basic Workflow

1. **User submits form** (WordPress)
   ↓
2. **Create Freshdesk ticket** (Automatic)
   ↓  
3. **Ticket processing** (Manual)
   ↓
4. **Ticket resolution** (Triggers webhook)
   ↓
5. **Auto-create Xero invoice** (Optional, based on tags)

### API Endpoints

```
GET  /                     # Application information
GET  /health              # Health check
GET  /test/connection     # Connection test

POST /webhook/wordpress   # WordPress form webhook
POST /webhook/freshdesk   # Freshdesk system webhook

GET  /xero/auth          # Xero authorization
GET  /xero/callback      # Xero callback

POST /api/tickets        # Create ticket
GET  /api/tickets/:id    # Get ticket details
POST /api/xero/invoice   # Create invoice
```

## 🔍 Testing Guide

### 1. Connection Testing
```bash
# Test all connections
curl http://localhost:5001/test/connection

# Health check
curl http://localhost:5001/health
```

### 2. Form Submission Testing

#### Basic Test
```bash
curl -X POST http://localhost:5001/webhook/wordpress \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "1234567890",
    "company": "Test Company",
    "subject": "Equipment Repair Request - Desktop",
    "message": "Computer not starting",
    "tags": ["Desktop"],
    "custom_fields": {
      "equipment_brand": "Dell",
      "equipment_model": "OptiPlex 5060",
      "internal_ticket_id": "TEST123"
    }
  }'
```

#### Complete Equipment Repair Test
```bash
curl -X POST http://localhost:5001/webhook/wordpress \
  -H "Content-Type: application/json" \
  -d '{
    "name": "JOHN SMITH",
    "email": "john.smith@company.com",
    "phone": "0412345678",
    "company": "Tech Solutions Ltd",
    "subject": "Equipment Repair Request - Laptop",
    "message": "=== EQUIPMENT REPAIR REQUEST ===\n\nCUSTOMER DETAILS:\nContact Name: JOHN SMITH\nBusiness Name: Tech Solutions Ltd\nPhone: 0412345678\nEmail: john.smith@company.com\n\nEQUIPMENT INFORMATION:\nEquipment Type: Laptop\nBrand: HP\nModel: ProBook 450\nSerial Number: ABC123XYZ\n\nSERVICE DETAILS:\nStore Location: Mail In Delivery\nPreferred Date: 25/6/2025\nPreferred Time: 14:00\n\nFAULT DESCRIPTION:\nLaptop screen flickering and random shutdowns\n\nACCESSORIES INCLUDED:\nCharger, Mouse\n\nADDITIONAL COMMENTS:\nUrgent repair needed for business presentation\n\n=== END OF REPAIR REQUEST ===",
    "priority": "high",
    "ticket_type": "Problem",
    "tags": ["repair", "equipment", "Laptop"],
    "custom_fields": {
      "equipment_brand": "HP",
      "equipment_model": "ProBook 450",
      "serial_number": "ABC123XYZ",
      "store_location": "Mail In Delivery",
      "repair_date": "25/6/2025",
      "repair_time": "14:00",
      "internal_ticket_id": "TECH789456123"
    }
  }'
```

### 3. WordPress Integration Testing

Add this shortcode to a WordPress page: `[freshdesk_form]` and test form submission.

## 🛡️ Security Configuration

### 1. Webhook Signature Verification
```env
WEBHOOK_SECRET=your_very_secure_random_string_at_least_32_characters
```

### 2. Allowed Origins
```env
ALLOWED_ORIGINS=https://your-wordpress-site.com,https://your-domain.com
```

### 3. API Key Protection
- Regularly rotate API keys
- Use HTTPS in production
- Never hardcode keys in source code
- Use environment variables for all secrets

### 4. Production Security Checklist
- [ ] HTTPS enabled
- [ ] Webhook secrets configured
- [ ] API keys rotated
- [ ] Allowed origins restricted
- [ ] Firewall rules configured
- [ ] Logs monitored

## 📝 Logging and Monitoring

### Log Levels
```env
LOG_LEVEL=DEBUG    # Development
LOG_LEVEL=INFO     # Production
LOG_LEVEL=WARNING  # Critical only
LOG_LEVEL=ERROR    # Errors only
```

### View Logs
```bash
# Real-time log monitoring
tail -f logs/app.log

# Filter error logs
grep ERROR logs/app.log

# Filter specific operations
grep "wordpress_webhook" logs/app.log
```

### Monitoring Endpoints
- `GET /health` - Application health status
- `GET /test/connection` - External service connection status

### Log Format
```
2025-06-24 10:03:17,405 - app - INFO - Received WordPress webhook - Origin: None
2025-06-24 10:03:17,411 - app - INFO - Raw form data: {...}
2025-06-24 10:03:17,415 - app - INFO - 📝 Using WordPress field names directly
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Field Mapping Errors
```
Error: contact_email is required
Cause: WordPress sends 'email' but system expects 'contact_email'
Solution: The new field mapping system handles this automatically
```

#### 2. Freshdesk API Authentication Failed
```
Error: 401 Unauthorized
Cause: Invalid API key or insufficient permissions
Solution: 
- Verify API key in Freshdesk Profile Settings
- Ensure API key has correct permissions
- Check domain name format (domain.freshdesk.com)
```

#### 3. WordPress Form Submission Failed
```
Error: Connection refused
Cause: Flask app not running or incorrect URL
Solution:
- Ensure Flask application is running
- Check URL configuration in WordPress
- Verify port and host settings
```

#### 4. Xero Authorization Failed
```
Error: Invalid client
Cause: Incorrect Client ID/Secret or redirect URI
Solution:
- Verify credentials in Xero Developer Portal
- Ensure redirect URI matches exactly
- Check OAuth scope configuration
```

#### 5. Webhook Not Triggered
```
Problem: Freshdesk webhook not working
Cause: Plan limitations or configuration issues
Solution:
- Ensure Garden plan or higher
- Verify webhook URL accessibility
- Check automation rule configuration
- Test webhook endpoint manually
```

#### 6. Email Validation Errors
```
Error: Invalid email format
Cause: Malformed email addresses
Solution:
- Check email regex pattern
- Validate form input on frontend
- Add additional email sanitization
```

### Debug Mode

```bash
# Enable debug mode
export FLASK_DEBUG=True
export LOG_LEVEL=DEBUG
python app.py

# View detailed request/response logs
grep -A 5 -B 5 "Freshdesk API" logs/app.log
```

### Performance Issues

```bash
# Monitor response times
grep "response status" logs/app.log | tail -20

# Check memory usage
ps aux | grep python

# Monitor disk space
df -h logs/
```

## 📚 Advanced Features

### Custom Field Mapping

Modify field mapping in `app.py`:

```python
def map_wordpress_fields(form_data):
    """Custom field mapping for specific requirements"""
    field_mapping = {
        'email': 'contact_email',
        'name': 'contact_name',
        'phone': 'contact_phone',
        'company': 'business_name',
        # Add custom mappings
        'customer_ref': 'internal_reference',
        'urgency': 'priority_level'
    }
    # Implementation continues...
```

### Custom Ticket Templates

```python
def format_ticket_description_clean(form_data):
    """Create custom ticket description templates"""
    template = """
=== CUSTOM SERVICE REQUEST ===

CLIENT INFORMATION:
Name: {name}
Company: {company}
Contact: {email} | {phone}

SERVICE DETAILS:
Type: {service_type}
Priority: {priority}
Description: {description}

INTERNAL NOTES:
Reference: {internal_ref}
Assigned: {assigned_agent}
    """
    # Format with form data
    return template.format(**form_data)
```

### Invoice Auto-Creation Rules

```python
def should_create_invoice(ticket_data):
    """Determine when to auto-create invoices"""
    # Custom logic for invoice creation
    tags = ticket_data.get('tags', [])
    priority = ticket_data.get('priority', 1)
    
    return (
        'billing' in tags or
        'consultation' in tags or
        priority >= 3  # High priority tickets
    )
```

### WordPress Plugin Enhancement

```php
// Add custom form fields
function add_custom_repair_fields() {
    ?>
    <div class="repair-form-section">
        <h3>Equipment Details</h3>
        <select name="equipment_type" required>
            <option value="">Select Equipment Type</option>
            <option value="Desktop">Desktop Computer</option>
            <option value="Laptop">Laptop</option>
            <option value="Printer">Printer</option>
            <option value="Server">Server</option>
        </select>
        
        <input type="text" name="serial_number" placeholder="Serial Number">
        <input type="date" name="purchase_date" placeholder="Purchase Date">
        <textarea name="warranty_info" placeholder="Warranty Information"></textarea>
    </div>
    <?php
}
```

## 🚀 Deployment

### Production Deployment

#### 1. Environment Setup
```bash
# Set production environment
export FLASK_ENV=production
export FLASK_DEBUG=False
export LOG_LEVEL=INFO
```

#### 2. Process Management (using systemd)

Create `/etc/systemd/system/freshdesk-integration.service`:

```ini
[Unit]
Description=Freshdesk Integration Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/freshdesk-integration-project
Environment=PATH=/path/to/conda/envs/freshdesk-integration/bin
ExecStart=/path/to/conda/envs/freshdesk-integration/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 3. Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 4. SSL Certificate (Let's Encrypt)
```bash
sudo certbot --nginx -d your-domain.com
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["python", "app.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  freshdesk-integration:
    build: .
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

Run with Docker:
```bash
docker-compose up -d
```

## 🤝 Contributing

1. Fork the project
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Create Pull Request

### Development Guidelines

- Follow PEP 8 Python style guide
- Add comprehensive logging for new features
- Include unit tests for critical functions
- Update documentation for API changes
- Test all integrations before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check project README and code comments
- **Issues**: Report bugs in GitHub Issues
- **Community**: Join relevant technical communities for discussion

## 📋 Changelog

### v1.2.0 (2025-06-24)
- ✅ Fixed field mapping issues between WordPress and Freshdesk
- ✅ Added intelligent field extraction from structured messages
- ✅ Improved error handling and logging
- ✅ Enhanced debugging capabilities
- ✅ Added comprehensive field validation

### v1.1.0 (2025-01-15)
- Added Xero invoice auto-creation
- Improved webhook security
- Enhanced logging system
- Added health check endpoints

### v1.0.0 (2024-12-01)
- Initial release
- WordPress form integration
- Freshdesk API integration
- Xero OAuth authentication
- Basic webhook functionality

---

## 📞 Contact Information

- **Developer**: 1Cyber Computer Services
- **Website**: https://1cyber.com.au
- **Support**: support@1cyber.com.au
- **Project Repository**: https://github.com/1cyber/freshdesk-integration

---

**Note**: This is a production-ready system. Please thoroughly test in a development environment before deploying to production.