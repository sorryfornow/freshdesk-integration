import os
import logging
from flask import Flask, request, jsonify
import requests
import json
import base64
from datetime import datetime, timedelta
import hashlib
import hmac
from urllib.parse import urlencode
import re

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-default-secret-key')
FRESHDESK_DOMAIN = os.getenv('FRESHDESK_DOMAIN')
FRESHDESK_API_KEY = os.getenv('FRESHDESK_API_KEY')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

# Xero configuration
XERO_CLIENT_ID = os.getenv('XERO_CLIENT_ID')
XERO_CLIENT_SECRET = os.getenv('XERO_CLIENT_SECRET')
XERO_REDIRECT_URI = os.getenv('XERO_REDIRECT_URI')
XERO_SCOPE = os.getenv('XERO_SCOPE')
XERO_ACCESS_TOKEN = os.getenv('XERO_ACCESS_TOKEN')

# Other configuration
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []
NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5001')

# WordPress Form Configuration
WP_FORM_ID = os.getenv('WP_FORM_ID', '107')
WP_SITE_URL = os.getenv('WP_SITE_URL', 'https://ordering.1cyber.com.au')

# Validate required environment variables
required_vars = ['FRESHDESK_DOMAIN', 'FRESHDESK_API_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"⚠️  Warning: Missing required environment variables: {', '.join(missing_vars)}")
    print("Application may not work properly, please check .env file")

# Setup logging
log_dir = os.path.dirname(os.getenv('LOG_FILE', 'logs/app.log'))
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Base64 encode API key for Freshdesk authentication
freshdesk_auth = base64.b64encode(f"{FRESHDESK_API_KEY}:X".encode()).decode() if FRESHDESK_API_KEY else ""


def verify_webhook_signature(payload, signature):
    """Verify webhook signature"""
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET not set, skipping signature verification")
        return True

    try:
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Remove possible prefix
        if signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification error: {str(e)}")
        return False


def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        "message": "1Cyber Equipment Repair - Freshdesk Integration System",
        "status": "running",
        "version": "1.3.0",
        "environment": os.getenv('FLASK_ENV', 'production'),
        "company": "1Cyber Computer Services",
        "endpoints": {
            "wordpress_webhook": "/webhook/wordpress",
            "freshdesk_webhook": "/webhook/freshdesk",
            "xero_auth": "/xero/auth",
            "create_ticket": "/api/tickets",
            "create_invoice": "/api/xero/invoice",
            "health_check": "/health",
            "test_connection": "/test/connection"
        },
        "wordpress_form": {
            "form_id": WP_FORM_ID,
            "site_url": WP_SITE_URL
        },
        "features": [
            "WordPress Form Integration",
            "Freshdesk Ticket Creation",
            "Simplified Password Field Mapping",
            "Direct Password Display",
            "Xero Invoice Generation",
            "Comprehensive Logging"
        ],
        "timestamp": datetime.now().isoformat()
    })


@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check Freshdesk connection
        freshdesk_status = test_freshdesk_connection()

        return jsonify({
            "status": "healthy",
            "services": {
                "freshdesk": freshdesk_status,
                "xero": "configured" if XERO_CLIENT_ID else "not_configured"
            },
            "environment": os.getenv('FLASK_ENV', 'production'),
            "configuration": {
                "freshdesk_domain": FRESHDESK_DOMAIN,
                "freshdesk_api_configured": bool(FRESHDESK_API_KEY),
                "webhook_secret_configured": bool(WEBHOOK_SECRET),
                "allowed_origins": len(ALLOWED_ORIGINS) if ALLOWED_ORIGINS else 0,
                "wordpress_form_id": WP_FORM_ID
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


def test_freshdesk_connection():
    """Test Freshdesk connection"""
    try:
        if not FRESHDESK_DOMAIN or not FRESHDESK_API_KEY:
            return "not_configured"

        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets?per_page=1"
        headers = {
            "Authorization": f"Basic {freshdesk_auth}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"Freshdesk connection test: {response.status_code}")
        return "connected" if response.status_code == 200 else f"error_{response.status_code}"
    except Exception as e:
        logger.error(f"Freshdesk connection test failed: {str(e)}")
        return "error"


# ===================
# WordPress Integration
# ===================

@app.route('/webhook/wordpress', methods=['POST'])
def wordpress_webhook():
    """Handle webhook from WordPress equipment repair form - SIMPLIFIED PASSWORD HANDLING"""
    try:
        # Basic CORS and origin checking
        origin = request.headers.get('Origin')
        user_agent = request.headers.get('User-Agent', '')
        is_development = os.getenv('FLASK_ENV') == 'development'
        is_test_request = 'curl' in user_agent.lower() or 'postman' in user_agent.lower()

        if (not is_development and not is_test_request and
                ALLOWED_ORIGINS and origin and origin not in ALLOWED_ORIGINS):
            logger.warning(f"Unauthorized origin: {origin}")
            return jsonify({"error": "Unauthorized origin"}), 403

        logger.info(f"Received WordPress webhook - Origin: {origin}")

        # Get form data
        form_data = request.get_json()
        if not form_data:
            logger.error("No form data received")
            return jsonify({"error": "No form data received"}), 400

        # Log what we received
        logger.info(f"Raw form data: {json.dumps(form_data, indent=2)}")

        # Map WordPress field names to expected field names
        mapped_data = map_wordpress_fields(form_data)

        logger.info(f"Mapped form data: {json.dumps(mapped_data, indent=2)}")

        # Validate required fields using mapped data
        required_fields = ['contact_email', 'contact_name', 'fault_description']
        for field in required_fields:
            value = str(mapped_data.get(field, '')).strip()
            logger.info(f"Checking field '{field}': '{value}'")
            if not value:
                logger.error(f"Missing or empty required field: {field}")
                return jsonify({"error": f"{field} is required"}), 400

        # Email validation
        email = str(mapped_data.get('contact_email', '')).strip()
        if not validate_email(email):
            logger.error(f"Invalid email format: '{email}'")
            return jsonify({"error": "Invalid email format"}), 400

        # Log customer info
        logger.info(
            f"Customer: {mapped_data.get('contact_name')} - Equipment: {mapped_data.get('equipment_type')} {mapped_data.get('equipment_brand')}")

        # Create ticket using mapped data
        logger.info("Creating Freshdesk ticket...")
        ticket_result = create_repair_ticket_direct(mapped_data)

        if ticket_result and ticket_result.get('success'):
            ticket_data = ticket_result.get('ticket_data', {})
            logger.info(f"✅ Successfully created ticket: {ticket_data.get('id')}")

            return jsonify({
                "status": "success",
                "message": "Equipment repair ticket created successfully",
                "ticket_created": {
                    "id": ticket_data.get('id'),
                    "subject": ticket_data.get('subject'),
                    "status": "created",
                    "type": "equipment_repair"
                },
                "customer": {
                    "name": mapped_data.get('contact_name'),
                    "email": mapped_data.get('contact_email'),
                    "business": mapped_data.get('business_name')
                },
                "timestamp": datetime.now().isoformat()
            })
        else:
            error_msg = ticket_result.get('error', 'Unknown error') if ticket_result else 'Ticket creation failed'
            logger.error(f"❌ Ticket creation failed: {error_msg}")
            return jsonify({
                "error": "Failed to create repair ticket",
                "details": error_msg,
                "timestamp": datetime.now().isoformat()
            }), 500

    except json.JSONDecodeError:
        logger.error("JSON parsing error")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"WordPress webhook error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e) if os.getenv('FLASK_DEBUG') == 'True' else "Please contact administrator",
            "timestamp": datetime.now().isoformat()
        }), 500


def map_wordpress_fields(form_data):
    """Map WordPress field names to expected internal field names - FIXED PASSWORD PRIORITY"""
    try:
        # Extract fields from the structured message if available
        message = form_data.get('message', '')
        mapped_data = {}

        # First, try to extract from the structured message
        if '=== EQUIPMENT REPAIR REQUEST ===' in message:
            mapped_data = extract_from_structured_message(message)
            logger.info("📝 Extracted data from structured message")

        # Then map the direct WordPress fields, giving priority to top-level fields
        field_mapping = {
            # WordPress field -> Internal field
            'email': 'contact_email',
            'name': 'contact_name',
            'phone': 'contact_phone',
            'company': 'business_name',
            'subject': 'subject',
            'message': 'full_message',
            'priority': 'priority',
            'ticket_type': 'ticket_type',
            'tags': 'tags',
            # Direct password field mappings
            'user_profile_password': 'user_profile_password',
            'password': 'user_profile_password'
        }

        # Map direct fields
        for wp_field, internal_field in field_mapping.items():
            if wp_field in form_data and form_data[wp_field]:
                mapped_data[internal_field] = form_data[wp_field]

        # Map custom fields if they exist
        custom_fields = form_data.get('custom_fields', {})
        if custom_fields:
            custom_field_mapping = {
                'equipment_brand': 'equipment_brand',
                'equipment_model': 'equipment_model',
                'serial_number': 'serial_number',
                'store_location': 'store_location',
                'repair_date': 'repair_date',
                'repair_time': 'repair_time',
                'internal_ticket_id': 'internal_ticket_id',
                'user_profile_password': 'user_profile_password'
            }

            for cf_field, internal_field in custom_field_mapping.items():
                if cf_field in custom_fields and custom_fields[cf_field]:
                    mapped_data[internal_field] = custom_fields[cf_field]

        # Enhanced password detection with priority order
        password_sources = [
            # 1. Direct WordPress form fields (highest priority)
            ('user_profile_password', form_data),
            ('password', form_data),
            ('user_password', form_data),
            ('profile_password', form_data),
            # 2. Custom fields
            ('user_profile_password', custom_fields),
            ('password', custom_fields),
        ]

        password_found = False
        for field_name, source_data in password_sources:
            if field_name in source_data and source_data[field_name]:
                password_value = str(source_data[field_name]).strip()
                if password_value and password_value.lower() not in ['yes', 'no', 'provided', 'not provided']:
                    mapped_data['user_profile_password'] = password_value
                    logger.info(f"🔑 Found password in {field_name}: {password_value}")
                    password_found = True
                    break

        # Only as a last resort, try to find password in message
        if not password_found and 'full_message' in mapped_data:
            password_value = find_password_in_message(mapped_data['full_message'])
            if password_value:
                mapped_data['user_profile_password'] = password_value
                logger.info("🔑 Extracted password from message as fallback")
            else:
                # Check if message indicates password was provided but we can't find it
                if 'Password Provided: Yes' in mapped_data.get('full_message', ''):
                    logger.warning("🔑 Password was provided but not found in accessible fields")
                    # Don't set any password field - let it be empty rather than confusing

        # Set default values for missing required fields
        if 'equipment_type' not in mapped_data:
            # Try to extract from tags
            tags = form_data.get('tags', [])
            for tag in tags:
                if tag.lower() in ['desktop', 'laptop', 'printer', 'server']:
                    mapped_data['equipment_type'] = tag.title()
                    break
            else:
                mapped_data['equipment_type'] = 'Equipment'

        # Extract fault description from full message if not already set
        if 'fault_description' not in mapped_data and 'full_message' in mapped_data:
            fault_desc = extract_fault_description_from_message(mapped_data['full_message'])
            if fault_desc:
                mapped_data['fault_description'] = fault_desc

        logger.info(f"🔄 Field mapping completed. Mapped {len(mapped_data)} fields")
        password_status = "provided" if mapped_data.get('user_profile_password') else "not provided"
        logger.info(f"🔑 Password: {password_status}")

        return mapped_data

    except Exception as e:
        logger.error(f"Field mapping error: {str(e)}")
        return form_data  # Return original data if mapping fails


def extract_from_structured_message(message):
    """Extract structured data from the formatted message - FIXED PASSWORD EXTRACTION"""
    extracted_data = {}

    try:
        lines = message.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            if line.endswith(':') and line.isupper():
                current_section = line[:-1].lower().replace(' ', '_')
                continue

            # Extract key-value pairs
            if ':' in line and current_section:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                # Map common fields
                field_mappings = {
                    'contact_name': 'contact_name',
                    'business_name': 'business_name',
                    'phone': 'contact_phone',
                    'email': 'contact_email',
                    'equipment_type': 'equipment_type',
                    'brand': 'equipment_brand',
                    'model': 'equipment_model',
                    'serial_number': 'serial_number',
                    'store_location': 'store_location',
                    'preferred_date': 'repair_date',
                    'preferred_time': 'repair_time',
                    'ticket_id': 'internal_ticket_id',
                    'internal_ticket_id': 'internal_ticket_id',
                    'profile_name': 'user_profile_name',
                    # Direct password mapping
                    'password': 'user_profile_password',
                    'user_profile_password': 'user_profile_password'
                }

                if key in field_mappings and value and value != 'Not provided':
                    extracted_data[field_mappings[key]] = value

                # Skip the problematic password_provided logic - we'll handle passwords differently
                # The actual password should come from direct WordPress fields, not from status

            # Extract fault description (special handling)
            elif current_section == 'fault_description' and line and not line.endswith(':'):
                if 'fault_description' not in extracted_data:
                    extracted_data['fault_description'] = line
                else:
                    extracted_data['fault_description'] += ' ' + line

            # Extract additional comments (special handling)
            elif current_section == 'additional_comments' and line and not line.endswith(':'):
                if 'additional_comments' not in extracted_data:
                    extracted_data['additional_comments'] = line
                else:
                    extracted_data['additional_comments'] += ' ' + line

            # Extract accessories (special handling)
            elif current_section == 'accessories_included' and line and not line.endswith(':'):
                if 'accessories' not in extracted_data:
                    extracted_data['accessories'] = line
                else:
                    extracted_data['accessories'] += ', ' + line

        logger.info(f"📤 Extracted {len(extracted_data)} fields from structured message")
        return extracted_data

    except Exception as e:
        logger.error(f"Message extraction error: {str(e)}")
        return {}


def find_password_in_message(message):
    """Enhanced password finder - looks for actual password values"""
    try:
        lines = message.split('\n')
        for line in lines:
            line = line.strip()

            # Look for lines that have actual password values
            password_patterns = [
                'password:',
                'user profile password:',
                'profile password:',
                'account password:',
                'user password:'
            ]

            for pattern in password_patterns:
                if pattern in line.lower() and ':' in line:
                    password_part = line.split(':', 1)[1].strip()
                    # Make sure it's not just a status indicator
                    if (password_part and
                            password_part.lower() not in ['yes', 'no', 'provided', 'not provided', 'true', 'false'] and
                            len(password_part) > 2):  # Reasonable password length
                        logger.info(f"🔑 Found password in message: {pattern}")
                        return password_part

        return None
    except Exception as e:
        logger.error(f"Password extraction error: {str(e)}")
        return None


def extract_fault_description_from_message(message):
    """Extract fault description from message text"""
    try:
        if 'FAULT DESCRIPTION:' in message:
            lines = message.split('\n')
            capture = False
            fault_lines = []

            for line in lines:
                line = line.strip()
                if 'FAULT DESCRIPTION:' in line:
                    capture = True
                    # Get description on same line if exists
                    if ':' in line:
                        desc_part = line.split(':', 1)[1].strip()
                        if desc_part:
                            fault_lines.append(desc_part)
                    continue
                elif capture and line and not line.isupper() and ':' not in line:
                    fault_lines.append(line)
                elif capture and (line.isupper() or '===' in line):
                    break

            if fault_lines:
                return ' '.join(fault_lines)

        return None

    except Exception as e:
        logger.error(f"Fault description extraction error: {str(e)}")
        return None


def create_repair_ticket_direct(form_data):
    """直接从表单数据创建Freshdesk票据 - 简化字段映射"""
    try:
        # 提取和清理基本字段 - 使用正确的字段名
        equipment = str(form_data.get('equipment_type', 'Equipment')).strip()
        brand = str(form_data.get('equipment_brand', '')).strip()
        customer = str(form_data.get('contact_name', 'Customer')).strip()
        internal_id = str(form_data.get('internal_ticket_id', '')).strip()
        email = str(form_data.get('contact_email', '')).strip()

        # 详细的调试日志
        logger.info(f"🔍 Form data extraction:")
        logger.info(f"  - equipment: '{equipment}'")
        logger.info(f"  - brand: '{brand}'")
        logger.info(f"  - customer: '{customer}'")
        logger.info(f"  - email: '{email}'")
        logger.info(f"  - internal_id: '{internal_id}'")
        logger.info(f"  - password: {'provided' if form_data.get('user_profile_password') else 'not provided'}")

        # 额外验证
        if not email:
            logger.error("❌ Email is empty after processing")
            return {'success': False, 'error': 'Email is required'}

        if not customer:
            logger.error("❌ Customer name is empty after processing")
            return {'success': False, 'error': 'Customer name is required'}

        # 生成票据主题
        subject_parts = [equipment if equipment else 'Equipment']
        if brand:
            subject_parts.append(brand)
        subject_parts.append(f"- {customer}")
        if internal_id:
            subject_parts.append(f"(Ref: {internal_id})")

        subject = " ".join(subject_parts)
        logger.info(f"📝 Generated subject: '{subject}'")

        # 尝试先创建或更新联系人
        phone = str(form_data.get('contact_phone', '')).strip()
        contact_data = {
            "name": customer,
            "email": email,
        }
        if phone:
            contact_data["phone"] = phone

        logger.info(f"👤 Attempting to create/update contact: {json.dumps(contact_data, indent=2)}")
        contact_result = create_or_update_contact(contact_data)

        # 构建票据数据 - 使用正确的字段名
        ticket_data_v1 = {
            "subject": subject[:100],
            "description": format_ticket_description_clean(form_data),
            "email": email,
            "name": customer[:50],
            "priority": 3,  # Medium priority
            "status": 2,  # Open
            "source": 7,  # Other
            "type": "Incident",
            "tags": [
                "equipment_repair",
                "wordpress",
                "1cyber",
                equipment.lower() if equipment else "equipment",
                str(form_data.get('store_location', 'unknown')).lower().replace(' ', '_')
            ]
        }

        if phone:
            ticket_data_v1["phone"] = phone[:20]

        # 最终验证ticket_data中的email
        final_email = ticket_data_v1.get('email')
        logger.info(f"🔍 Final ticket email check: '{final_email}' (type: {type(final_email)})")

        if not final_email or final_email.strip() == '':
            logger.error("❌ Final email validation failed - email is empty!")
            return {'success': False, 'error': 'Final email validation failed'}

        # 记录票据数据用于调试
        logger.info(f"📦 Prepared ticket data (v1): {json.dumps(ticket_data_v1, ensure_ascii=False, indent=2)}")

        # 尝试创建票据
        result = create_freshdesk_ticket(ticket_data_v1)

        # 如果第一种方式失败，尝试第二种方式（如果有联系人ID）
        if not result.get('success') and contact_result:
            logger.info("🔄 First attempt failed, trying with requester_id...")
            ticket_data_v2 = ticket_data_v1.copy()
            if isinstance(contact_result, dict) and contact_result.get('id'):
                ticket_data_v2['requester_id'] = contact_result['id']
                # 移除email和name，使用requester_id
                ticket_data_v2.pop('email', None)
                ticket_data_v2.pop('name', None)
                ticket_data_v2.pop('phone', None)

                logger.info(f"📦 Prepared ticket data (v2): {json.dumps(ticket_data_v2, ensure_ascii=False, indent=2)}")
                result = create_freshdesk_ticket(ticket_data_v2)

        return result

    except Exception as e:
        error_msg = f"Ticket creation error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': error_msg
        }


def format_ticket_description_clean(form_data):
    """简洁的票据描述格式 - 显示实际密码值"""

    def get_value(key, default="Not provided"):
        value = form_data.get(key)
        if value is None:
            return default
        value = str(value).strip()
        return value if value else default

    # 基本信息
    description = "=== EQUIPMENT REPAIR REQUEST ===\n\n"

    # 客户信息
    description += "CUSTOMER DETAILS:\n"
    description += f"Contact Name: {get_value('contact_name')}\n"
    description += f"Business Name: {get_value('business_name')}\n"
    description += f"Phone: {get_value('contact_phone')}\n"
    description += f"Email: {get_value('contact_email')}\n\n"

    # 设备信息
    description += "EQUIPMENT INFORMATION:\n"
    description += f"Equipment Type: {get_value('equipment_type', 'Not specified')}\n"
    description += f"Brand: {get_value('equipment_brand', 'Not specified')}\n"
    description += f"Model: {get_value('equipment_model', 'Not specified')}\n"
    description += f"Serial Number: {get_value('serial_number')}\n\n"

    # 服务详情
    description += "SERVICE DETAILS:\n"
    description += f"Store Location: {get_value('store_location', 'Not specified')}\n"
    description += f"Preferred Date: {get_value('repair_date', 'Not specified')}\n"
    description += f"Preferred Time: {get_value('repair_time', 'Not specified')}\n\n"

    # 故障描述
    description += f"FAULT DESCRIPTION:\n{get_value('fault_description', 'No description provided')}\n\n"

    # 配件
    accessories = get_value('accessories', 'None specified')
    if accessories != 'None specified':
        description += f"ACCESSORIES INCLUDED:\n{accessories}\n\n"

    # 额外备注
    comments = get_value('additional_comments', '')
    if comments:
        description += f"ADDITIONAL COMMENTS:\n{comments}\n\n"

    # 用户账户信息 - 显示实际密码值
    profile_name = get_value('user_profile_name', '')
    password = get_value('user_profile_password', '')

    if profile_name or password:
        description += "USER ACCOUNT:\n"
        if profile_name:
            description += f"Profile Name: {profile_name}\n"
        if password:
            # 显示实际密码值（根据用户需求）
            description += f"Password: {password}\n"
        description += "\n"

    # 内部参考
    internal_id = get_value('internal_ticket_id', '')
    if internal_id:
        description += f"INTERNAL REFERENCE:\nInternal Ticket ID: {internal_id}\n\n"

    description += "=== END OF REPAIR REQUEST ==="

    return description


# ===================
# Freshdesk Integration
# ===================

@app.route('/webhook/freshdesk', methods=['POST', 'GET'])
def freshdesk_webhook():
    """Handle webhook from Freshdesk"""
    try:
        # Handle GET request (endpoint verification)
        if request.method == 'GET':
            logger.info("Received Freshdesk webhook GET request - endpoint verification")
            return jsonify({
                "status": "ok",
                "message": "1Cyber Freshdesk webhook endpoint is active",
                "timestamp": datetime.now().isoformat(),
                "endpoint": "/webhook/freshdesk"
            })

        # Handle POST request
        logger.info("Received Freshdesk webhook POST request")

        payload = request.get_data()
        signature = request.headers.get('X-Freshdesk-Signature', '')

        # Log received webhook
        logger.info(f"Freshdesk webhook signature: {signature[:20] if signature else 'None'}...")

        # Verify signature (if WEBHOOK_SECRET configured)
        if WEBHOOK_SECRET and signature:
            if not verify_webhook_signature(payload, signature):
                logger.warning("Freshdesk webhook signature verification failed")
                return jsonify({"error": "Invalid signature"}), 403

        webhook_data = request.get_json()

        if not webhook_data:
            logger.error("No Freshdesk webhook data received")
            return jsonify({"error": "No JSON data received"}), 400

        event_type = webhook_data.get('event_type', 'unknown')
        ticket_data = webhook_data.get('ticket', {})

        logger.info(f"Received Freshdesk webhook: {event_type} - Ticket ID: {ticket_data.get('id', 'unknown')}")

        # Process different event types
        result = {"processed": False, "action": "none"}

        if event_type == 'ticket_created':
            result = handle_ticket_created(ticket_data)
        elif event_type == 'ticket_updated':
            result = handle_ticket_updated(ticket_data)
        elif event_type == 'ticket_resolved':
            result = handle_ticket_resolved(ticket_data)
            # Create invoice for resolved tickets if needed
            if should_create_invoice(ticket_data):
                invoice_result = create_invoice_for_resolved_ticket(ticket_data)
                result["invoice_created"] = invoice_result
        else:
            logger.info(f"Unhandled event type: {event_type}")
            result = {"processed": True, "action": "ignored", "reason": "unsupported_event_type"}

        return jsonify({
            "status": "success",
            "message": "Webhook processed successfully",
            "event_type": event_type,
            "ticket_id": ticket_data.get('id'),
            "result": result,
            "timestamp": datetime.now().isoformat()
        }), 200

    except json.JSONDecodeError:
        logger.error("Freshdesk webhook JSON parsing error")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"Freshdesk webhook processing error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e) if os.getenv('FLASK_DEBUG') == 'True' else "Please contact administrator",
            "timestamp": datetime.now().isoformat()
        }), 500


def handle_ticket_created(ticket_data):
    """Handle new ticket creation"""
    ticket_id = ticket_data.get('id')
    subject = ticket_data.get('subject')
    logger.info(f"New ticket created: ID {ticket_id}, Subject: {subject}")

    # Send notification email (if configured)
    if NOTIFICATION_EMAIL:
        send_notification_email("New Equipment Repair Ticket", f"Ticket #{ticket_id} created: {subject}")

    return {"processed": True, "action": "logged", "ticket_id": ticket_id}


def handle_ticket_updated(ticket_data):
    """Handle ticket update"""
    ticket_id = ticket_data.get('id')
    status = ticket_data.get('status')
    logger.info(f"Ticket {ticket_id} updated. New status: {status}")

    return {"processed": True, "action": "logged", "ticket_id": ticket_id}


def handle_ticket_resolved(ticket_data):
    """Handle ticket resolution"""
    ticket_id = ticket_data.get('id')
    logger.info(f"Ticket {ticket_id} resolved")

    return {"processed": True, "action": "resolved_processed", "ticket_id": ticket_id}


def create_freshdesk_ticket(ticket_data):
    """Create ticket in Freshdesk"""
    try:
        if not FRESHDESK_DOMAIN or not FRESHDESK_API_KEY:
            logger.error("Freshdesk configuration incomplete")
            return {
                "success": False,
                "error": "Freshdesk configuration incomplete"
            }

        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets"
        headers = {
            "Authorization": f"Basic {freshdesk_auth}",
            "Content-Type": "application/json"
        }

        # 详细记录发送给Freshdesk的数据
        logger.info(f"🚀 Sending request to Freshdesk: {url}")
        logger.info(f"📧 Freshdesk API Headers: {headers}")
        logger.info(f"📦 Freshdesk API Payload: {json.dumps(ticket_data, ensure_ascii=False, indent=2)}")

        # 特别检查email字段
        email_value = ticket_data.get('email')
        logger.info(f"🔍 Email field check: email='{email_value}' (type: {type(email_value)})")

        if not email_value:
            logger.error("❌ Email field is empty or None before sending to Freshdesk!")
            return {
                "success": False,
                "error": "Email field is empty before sending to Freshdesk"
            }

        response = requests.post(url, headers=headers, json=ticket_data, timeout=30)

        logger.info(f"📥 Freshdesk API response status: {response.status_code}")
        logger.info(f"📥 Freshdesk API response headers: {dict(response.headers)}")
        logger.info(f"📥 Freshdesk API response content: {response.text}")

        if response.status_code == 201:
            ticket = response.json()
            logger.info(f"✅ Successfully created ticket: {ticket.get('id')}")
            return {
                "success": True,
                "ticket_data": ticket
            }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"❌ Ticket creation failed: {error_msg}")

            # 尝试解析Freshdesk错误响应
            try:
                error_detail = response.json()
                logger.error(f"❌ Freshdesk error details: {json.dumps(error_detail, indent=2)}")
            except:
                logger.error(f"❌ Could not parse Freshdesk error response")

            return {
                "success": False,
                "error": error_msg
            }

    except requests.exceptions.Timeout:
        error_msg = "Request timeout"
        logger.error(f"❌ Freshdesk ticket creation timeout")
        return {"success": False, "error": error_msg}
    except requests.exceptions.ConnectionError:
        error_msg = "Connection error"
        logger.error(f"❌ Failed to connect to Freshdesk")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unknown error: {str(e)}"
        logger.error(f"❌ Freshdesk ticket creation error: {error_msg}")
        return {"success": False, "error": error_msg}


def create_or_update_contact(contact_data):
    """Create or update Freshdesk contact"""
    try:
        email = contact_data.get('email')
        if not email:
            return None

        # Search for existing contact
        url = f"https://{FRESHDESK_DOMAIN}/api/v2/contacts"
        headers = {
            "Authorization": f"Basic {freshdesk_auth}",
            "Content-Type": "application/json"
        }

        search_url = f"{url}?email={email}"
        response = requests.get(search_url, headers=headers, timeout=30)

        if response.status_code == 200 and response.json():
            # Update existing contact
            contact_id = response.json()[0]['id']
            update_url = f"{url}/{contact_id}"
            response = requests.put(update_url, headers=headers, json=contact_data, timeout=30)
            logger.info(f"Updated contact: {email}")
        else:
            # Create new contact
            response = requests.post(url, headers=headers, json=contact_data, timeout=30)
            logger.info(f"Created new contact: {email}")

        return response.json() if response.status_code in [200, 201] else None

    except Exception as e:
        logger.error(f"Contact creation/update error: {str(e)}")
        return None


# ===================
# Xero Integration
# ===================

@app.route('/xero/auth')
def xero_auth():
    """Start Xero OAuth authentication flow"""
    if not XERO_CLIENT_ID:
        return jsonify({"error": "Xero client ID not configured"}), 400

    auth_url = "https://login.xero.com/identity/connect/authorize"
    params = {
        "response_type": "code",
        "client_id": XERO_CLIENT_ID,
        "redirect_uri": XERO_REDIRECT_URI,
        "scope": XERO_SCOPE,
        "state": "random_state_string"
    }

    url = f"{auth_url}?{urlencode(params)}"
    return f'''
    <html>
        <head><title>1Cyber - Xero Authorization</title></head>
        <body>
            <h2>1Cyber Xero Authorization</h2>
            <p>Click the link below to authorize Xero access:</p>
            <a href="{url}" style="display: inline-block; padding: 10px 20px; background-color: #13B5EA; color: white; text-decoration: none; border-radius: 5px;">Authorize Xero</a>
        </body>
    </html>
    '''


@app.route('/xero/callback')
def xero_callback():
    """Handle Xero OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        logger.error(f"Xero authorization error: {error}")
        return jsonify({"error": f"Authorization failed: {error}"}), 400

    if code:
        token_data = exchange_xero_token(code)
        if token_data:
            logger.info("Xero authorization successful")
            return jsonify({
                "message": "Xero authentication successful",
                "access_token": token_data.get('access_token', '')[:20] + "...",
                "expires_in": token_data.get('expires_in')
            })

    return jsonify({"error": "Xero authentication failed"}), 400


def exchange_xero_token(auth_code):
    """Exchange Xero access token"""
    try:
        token_url = "https://identity.xero.com/connect/token"

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": XERO_REDIRECT_URI
        }

        auth_header = base64.b64encode(f"{XERO_CLIENT_ID}:{XERO_CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(token_url, data=data, headers=headers, timeout=30)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Xero token exchange failed: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Xero token exchange error: {str(e)}")
        return None


def should_create_invoice(ticket_data):
    """Determine if invoice should be created for this ticket"""
    tags = ticket_data.get('tags', [])
    ticket_type = ticket_data.get('type', '')

    return (
            'billing' in [tag.lower() for tag in tags] or
            'invoice' in [tag.lower() for tag in tags] or
            ticket_type.lower() == 'billing'
    )


def create_invoice_for_resolved_ticket(ticket_data):
    """Create invoice for resolved ticket"""
    try:
        invoice_data = extract_billing_info_from_ticket(ticket_data)
        if invoice_data:
            result = create_xero_invoice_from_form(invoice_data)
            logger.info(f"Created invoice for ticket {ticket_data.get('id')}")
            return result
    except Exception as e:
        logger.error(f"Invoice creation error for ticket: {str(e)}")
        return None


def extract_billing_info_from_ticket(ticket_data):
    """Extract billing information from ticket"""
    return {
        "name": "Customer Name",  # Extract from ticket
        "email": "customer@example.com",  # Extract from ticket
        "service_description": ticket_data.get('subject', 'Service Fee'),
        "amount": 100  # Extract from ticket description or custom fields
    }


def create_xero_invoice_from_form(form_data):
    """Create Xero invoice from form data"""
    try:
        if not XERO_ACCESS_TOKEN:
            logger.warning("Xero access token not configured, cannot create invoice")
            return {"message": "Xero authorization required", "auth_url": "/xero/auth"}

        invoice_data = {
            "Type": "ACCREC",
            "Contact": {
                "Name": form_data.get('name', 'Unknown Customer'),
                "EmailAddress": form_data.get('email')
            },
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "DueDate": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "LineItems": [
                {
                    "Description": form_data.get('service_description', 'Equipment Repair Service'),
                    "Quantity": 1,
                    "UnitAmount": float(form_data.get('amount', 0)),
                    "AccountCode": "200"  # Replace with actual account code
                }
            ],
            "Reference": f"1CYBER-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }

        # This should call actual Xero API
        logger.info(f"Prepared Xero invoice: {json.dumps(invoice_data, indent=2)}")
        return {"message": "Invoice data prepared", "data": invoice_data}

    except Exception as e:
        logger.error(f"Xero invoice creation error: {str(e)}")
        return None


# ===================
# Notification Functions
# ===================

def send_notification_email(subject, message):
    """Send notification email"""
    try:
        # Implement email sending logic here
        # Use SMTP_* environment variables for configuration
        logger.info(f"Notification email: {subject} - {message}")
    except Exception as e:
        logger.error(f"Email notification error: {str(e)}")


# ===================
# API Endpoints
# ===================

@app.route('/api/tickets', methods=['POST'])
def create_ticket_api():
    """API endpoint: Create new ticket"""
    try:
        ticket_data = request.get_json()
        if not ticket_data:
            return jsonify({"error": "No ticket data provided"}), 400

        result = create_freshdesk_ticket(ticket_data)
        if result and result.get('success'):
            return jsonify(result.get('ticket_data')), 201
        else:
            return jsonify(
                {"error": result.get('error', 'Ticket creation failed') if result else "Ticket creation failed"}), 500

    except Exception as e:
        logger.error(f"API ticket creation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    """Get specific ticket"""
    try:
        url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"
        headers = {
            "Authorization": f"Basic {freshdesk_auth}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": "Failed to retrieve ticket",
                "status_code": response.status_code
            }), response.status_code

    except Exception as e:
        logger.error(f"Get ticket error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/test/connection', methods=['GET'])
def test_all_connections():
    """Test all system connections"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv('FLASK_ENV', 'production'),
        "company": "1Cyber Computer Services",
        "version": "1.3.0",
        "features": [
            "Simplified password handling",
            "Direct password display",
            "Enhanced field mapping",
            "WordPress integration"
        ]
    }

    # Test Freshdesk connection
    try:
        if FRESHDESK_DOMAIN and FRESHDESK_API_KEY:
            url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets?per_page=1"
            headers = {
                "Authorization": f"Basic {freshdesk_auth}",
                "Content-Type": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=10)
            results['freshdesk'] = {
                "status": "success" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "domain": FRESHDESK_DOMAIN
            }
        else:
            results['freshdesk'] = {"status": "not_configured", "error": "Missing configuration"}
    except Exception as e:
        results['freshdesk'] = {"status": "error", "error": str(e)}

    # Check Xero configuration
    results['xero'] = {
        "status": "configured" if XERO_CLIENT_ID else "not_configured",
        "has_access_token": bool(XERO_ACCESS_TOKEN),
        "auth_url": "/xero/auth" if XERO_CLIENT_ID else None
    }

    # Check environment variables
    results['configuration'] = {
        "webhook_secret_set": bool(WEBHOOK_SECRET),
        "flask_secret_set": bool(app.config['SECRET_KEY']),
        "notification_email_set": bool(NOTIFICATION_EMAIL),
        "allowed_origins_count": len(ALLOWED_ORIGINS) if ALLOWED_ORIGINS else 0,
        "wordpress_form_id": WP_FORM_ID,
        "wordpress_site_url": WP_SITE_URL
    }

    return jsonify(results)


# ===================
# Error Handlers
# ===================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({"error": "Server error"}), 500


# ===================
# Application Startup
# ===================

if __name__ == '__main__':
    # Ensure log directory exists
    os.makedirs('logs', exist_ok=True)

    # Development environment configuration
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Starting 1Cyber Equipment Repair Integration v1.3.0 - Debug: {debug_mode}, Port: {port}")
    logger.info(
        f"Freshdesk configuration: Domain={FRESHDESK_DOMAIN}, API Key={'configured' if FRESHDESK_API_KEY else 'not configured'}")
    logger.info(f"WordPress Form ID: {WP_FORM_ID}, Site URL: {WP_SITE_URL}")
    logger.info("✅ Simplified password field mapping with direct display enabled")

    # Start application
    app.run(debug=debug_mode, host=host, port=port)