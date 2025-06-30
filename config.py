import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class Config:
    """基础配置类"""

    # Flask 基础配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # Freshdesk 配置
    FRESHDESK_DOMAIN = os.getenv('FRESHDESK_DOMAIN')
    FRESHDESK_API_KEY = os.getenv('FRESHDESK_API_KEY')

    # Webhook 配置
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

    # Xero 配置
    XERO_CLIENT_ID = os.getenv('XERO_CLIENT_ID')
    XERO_CLIENT_SECRET = os.getenv('XERO_CLIENT_SECRET')
    XERO_REDIRECT_URI = os.getenv('XERO_REDIRECT_URI', 'http://localhost:5000/xero/callback')
    XERO_SCOPE = os.getenv('XERO_SCOPE', 'accounting.transactions')
    XERO_ACCESS_TOKEN = os.getenv('XERO_ACCESS_TOKEN')

    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///freshdesk_integration.db')

    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

    # 安全配置
    ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv('ALLOWED_ORIGINS', '').split(',') if origin.strip()]

    # 邮件配置
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')

    # 其他配置
    WORDPRESS_WEBHOOK_URL = os.getenv('WORDPRESS_WEBHOOK_URL')

    @classmethod
    def validate_required_config(cls):
        """验证必需的配置项"""
        required_vars = [
            'FRESHDESK_DOMAIN',
            'FRESHDESK_API_KEY'
        ]

        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")

        return True

    @classmethod
    def get_freshdesk_auth_header(cls):
        """获取Freshdesk认证头"""
        import base64
        return base64.b64encode(f"{cls.FRESHDESK_API_KEY}:X".encode()).decode()

    @classmethod
    def is_xero_configured(cls):
        """检查Xero是否已配置"""
        return bool(cls.XERO_CLIENT_ID and cls.XERO_CLIENT_SECRET)

    @classmethod
    def is_email_configured(cls):
        """检查邮件是否已配置"""
        return bool(cls.SMTP_SERVER and cls.SMTP_USERNAME and cls.SMTP_PASSWORD)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'INFO'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}