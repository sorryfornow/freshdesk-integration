import os
import logging
import smtplib
import hashlib
import hmac
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


def setup_logging():
    """设置日志配置"""
    # 确保日志目录存在
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )

    # 文件处理器
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


def verify_webhook_signature(payload, signature, secret):
    """验证webhook签名"""
    if not secret:
        return True

    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


def sanitize_input(data, max_length=None):
    """清理输入数据"""
    if isinstance(data, str):
        # 移除潜在的恶意字符
        sanitized = data.strip()
        if max_length:
            sanitized = sanitized[:max_length]
        return sanitized
    elif isinstance(data, dict):
        return {k: sanitize_input(v, max_length) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item, max_length) for item in data]
    else:
        return data


def validate_email(email):
    """验证邮箱格式"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def format_currency(amount, currency='CNY'):
    """格式化货币"""
    try:
        return f"{float(amount):.2f} {currency}"
    except (ValueError, TypeError):
        return f"0.00 {currency}"


def send_email_notification(subject, message, to_email=None):
    """发送邮件通知"""
    if not Config.is_email_configured():
        logging.warning("邮件配置不完整，无法发送通知")
        return False

    try:
        # 创建邮件
        msg = MimeMultipart()
        msg['From'] = Config.SMTP_USERNAME
        msg['To'] = to_email or Config.NOTIFICATION_EMAIL
        msg['Subject'] = subject

        # 添加邮件正文
        msg.attach(MimeText(message, 'plain', 'utf-8'))

        # 连接SMTP服务器并发送
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            server.send_message(msg)

        logging.info(f"邮件通知已发送: {subject}")
        return True

    except Exception as e:
        logging.error(f"发送邮件通知失败: {str(e)}")
        return False


def create_error_response(message, status_code=400, details=None):
    """创建标准错误响应"""
    response = {
        "error": message,
        "status_code": status_code,
        "timestamp": datetime.now().isoformat()
    }

    if details:
        response["details"] = details

    return response


def create_success_response(message, data=None):
    """创建标准成功响应"""
    response = {
        "status": "success",
        "message": message,
        "timestamp": datetime.now().isoformat()
    }

    if data:
        response["data"] = data

    return response


def log_api_request(request, response_status=None):
    """记录API请求日志"""
    logger = logging.getLogger(__name__)

    request_data = {
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "remote_addr": request.remote_addr,
        "user_agent": request.headers.get('User-Agent'),
        "timestamp": datetime.now().isoformat()
    }

    if response_status:
        request_data["response_status"] = response_status

    # 移除敏感信息
    if 'Authorization' in request_data["headers"]:
        request_data["headers"]["Authorization"] = "[REDACTED]"

    logger.info(f"API请求: {json.dumps(request_data, ensure_ascii=False)}")


def mask_sensitive_data(data, keys_to_mask=None):
    """遮盖敏感数据"""
    if keys_to_mask is None:
        keys_to_mask = ['password', 'api_key', 'token', 'secret', 'authorization']

    if isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in keys_to_mask):
                masked_data[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                masked_data[key] = mask_sensitive_data(value, keys_to_mask)
            else:
                masked_data[key] = value
        return masked_data
    elif isinstance(data, list):
        return [mask_sensitive_data(item, keys_to_mask) for item in data]
    else:
        return data


def generate_reference_number(prefix="REF"):
    """生成参考号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}"


def parse_datetime(datetime_str):
    """解析日期时间字符串"""
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"无法解析日期时间: {datetime_str}")


def validate_freshdesk_data(data):
    """验证Freshdesk数据"""
    required_fields = ['email', 'subject']
    errors = []

    for field in required_fields:
        if not data.get(field):
            errors.append(f"缺少必需字段: {field}")

    # 验证邮箱
    if data.get('email') and not validate_email(data['email']):
        errors.append("邮箱格式无效")

    # 验证优先级
    if data.get('priority') and data['priority'] not in [1, 2, 3, 4]:
        errors.append("优先级必须是1-4之间的数字")

    return errors


def validate_xero_data(data):
    """验证Xero数据"""
    required_fields = ['amount']
    errors = []

    for field in required_fields:
        if not data.get(field):
            errors.append(f"缺少必需字段: {field}")

    # 验证金额
    try:
        amount = float(data.get('amount', 0))
        if amount <= 0:
            errors.append("金额必须大于0")
    except (ValueError, TypeError):
        errors.append("金额格式无效")

    return errors


def retry_api_call(func, max_retries=3, delay=1):
    """重试API调用"""
    import time

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e

            logging.warning(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            time.sleep(delay * (attempt + 1))

    return None


def get_client_ip(request):
    """获取客户端IP地址"""
    # 检查代理头
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def rate_limit_key(request, identifier=None):
    """生成速率限制键"""
    if identifier:
        return f"rate_limit:{identifier}"
    else:
        ip = get_client_ip(request)
        return f"rate_limit:{ip}"


class DataValidator:
    """数据验证器类"""

    @staticmethod
    def validate_wordpress_form(data):
        """验证WordPress表单数据"""
        errors = []

        # 必需字段
        required_fields = ['email', 'subject', 'message']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"缺少必需字段: {field}")

        # 邮箱验证
        if data.get('email') and not validate_email(data['email']):
            errors.append("邮箱格式无效")

        # 长度验证
        if data.get('subject') and len(data['subject']) > 100:
            errors.append("主题长度不能超过100字符")

        if data.get('message') and len(data['message']) > 5000:
            errors.append("消息长度不能超过5000字符")

        return errors

    @staticmethod
    def validate_freshdesk_webhook(data):
        """验证Freshdesk webhook数据"""
        errors = []

        if not data.get('event_type'):
            errors.append("缺少event_type字段")

        if not data.get('ticket'):
            errors.append("缺少ticket数据")

        return errors


# 导出主要函数
__all__ = [
    'setup_logging',
    'verify_webhook_signature',
    'sanitize_input',
    'validate_email',
    'format_currency',
    'send_email_notification',
    'create_error_response',
    'create_success_response',
    'log_api_request',
    'mask_sensitive_data',
    'generate_reference_number',
    'parse_datetime',
    'validate_freshdesk_data',
    'validate_xero_data',
    'retry_api_call',
    'get_client_ip',
    'DataValidator'
]