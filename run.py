#!/usr/bin/env python3
"""
Flask 应用启动脚本
用于启动 WordPress + Freshdesk + Xero 集成系统
"""

import os
import sys
import argparse
from config import Config, config
from utils import setup_logging


def create_app(config_name=None):
    """创建Flask应用实例"""
    from app import app

    # 设置配置
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])

    # 验证配置
    try:
        Config.validate_required_config()
        print("✓ 配置验证通过")
    except ValueError as e:
        print(f"✗ 配置错误: {e}")
        return None

    # 设置日志
    setup_logging()
    print("✓ 日志系统已初始化")

    return app


def check_environment():
    """检查运行环境"""
    print("检查运行环境...")

    # 检查Python版本
    if sys.version_info < (3, 7):
        print("✗ 需要Python 3.7或更高版本")
        return False
    print(f"✓ Python版本: {sys.version}")

    # 检查必需的环境变量
    required_vars = ['FRESHDESK_DOMAIN', 'FRESHDESK_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"✗ 缺少环境变量: {', '.join(missing_vars)}")
        print("请检查.env文件是否正确配置")
        return False
    print("✓ 必需的环境变量已设置")

    # 检查可选配置
    optional_configs = {
        'XERO_CLIENT_ID': 'Xero集成',
        'WEBHOOK_SECRET': 'Webhook安全',
        'SMTP_SERVER': '邮件通知'
    }

    for var, description in optional_configs.items():
        if os.getenv(var):
            print(f"✓ {description}已配置")
        else:
            print(f"⚠ {description}未配置")

    return True


def test_connections():
    """测试外部服务连接"""
    print("\n测试外部服务连接...")

    import requests
    from config import Config

    # 测试Freshdesk连接
    try:
        url = f"https://{Config.FRESHDESK_DOMAIN}/api/v2/tickets?per_page=1"
        headers = {
            "Authorization": f"Basic {Config.get_freshdesk_auth_header()}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            print("✓ Freshdesk API连接成功")
        elif response.status_code == 401:
            print("✗ Freshdesk API认证失败，请检查API密钥")
            return False
        else:
            print(f"⚠ Freshdesk API返回状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ Freshdesk连接失败: {str(e)}")
        return False

    # 检查Xero配置
    if Config.is_xero_configured():
        print("✓ Xero配置已设置")
    else:
        print("⚠ Xero未配置")

    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动Freshdesk集成应用')
    parser.add_argument('--host', default='0.0.0.0', help='主机地址')
    parser.add_argument('--port', type=int, default=5001, help='端口号')
    parser.add_argument('--env', choices=['development', 'production', 'testing'],
                        default='development', help='运行环境')
    parser.add_argument('--check-only', action='store_true', help='仅检查配置不启动服务')
    parser.add_argument('--no-debug', action='store_true', help='禁用调试模式')

    args = parser.parse_args()

    # 设置环境变量
    os.environ['FLASK_ENV'] = args.env

    print(f"🚀 启动Freshdesk集成应用 (环境: {args.env})")
    print("=" * 50)

    # 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，请修复后重试")
        sys.exit(1)

    # 测试连接
    if not test_connections():
        print("\n❌ 连接测试失败，请检查配置")
        sys.exit(1)

    if args.check_only:
        print("\n✅ 所有检查通过！")
        return

    # 创建应用
    app = create_app(args.env)
    if not app:
        print("\n❌ 应用创建失败")
        sys.exit(1)

    # 设置运行参数
    debug_mode = not args.no_debug and args.env == 'development'

    print(f"\n🌐 应用将在以下地址启动:")
    print(f"   本地: http://localhost:{args.port}")
    print(f"   网络: http://{args.host}:{args.port}")
    print(f"\n📋 可用端点:")
    print(f"   健康检查: http://localhost:{args.port}/health")
    print(f"   连接测试: http://localhost:{args.port}/test/connection")
    print(f"   WordPress webhook: http://localhost:{args.port}/webhook/wordpress")
    print(f"   Freshdesk webhook: http://localhost:{args.port}/webhook/freshdesk")

    if Config.is_xero_configured():
        print(f"   Xero授权: http://localhost:{args.port}/xero/auth")

    print(f"\n🔄 调试模式: {'开启' if debug_mode else '关闭'}")
    print("=" * 50)
    print("按 Ctrl+C 停止服务")

    try:
        # 启动应用
        app.run(
            host=args.host,
            port=args.port,
            debug=debug_mode,
            use_reloader=debug_mode
        )
    except KeyboardInterrupt:
        print("\n\n👋 应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()