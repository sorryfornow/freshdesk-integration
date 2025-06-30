#!/usr/bin/env python3
"""
集成测试脚本
测试WordPress + Freshdesk + Xero集成系统的各个组件
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class IntegrationTester:
    def __init__(self):
        self.base_url = f"http://{os.getenv('HOST', 'localhost')}:{os.getenv('PORT', 5000)}"
        self.test_results = []

    def log_test(self, test_name, success, message="", details=None):
        """记录测试结果"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")

        if details and not success:
            print(f"   详情: {details}")

    def test_environment_variables(self):
        """测试环境变量配置"""
        print("\n🔍 测试环境变量配置...")

        required_vars = [
            'FRESHDESK_DOMAIN',
            'FRESHDESK_API_KEY',
            'SECRET_KEY'
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.log_test(
                "环境变量检查",
                False,
                f"缺少必需变量: {', '.join(missing_vars)}"
            )
            return False
        else:
            self.log_test("环境变量检查", True, "所有必需变量已设置")
            return True

    def test_app_startup(self):
        """测试应用启动"""
        print("\n🚀 测试应用连接...")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "应用启动",
                    True,
                    f"应用运行正常 (状态: {data.get('status')})",
                    data
                )
                return True
            else:
                self.log_test(
                    "应用启动",
                    False,
                    f"健康检查失败: HTTP {response.status_code}"
                )
                return False

        except requests.exceptions.ConnectionError:
            self.log_test(
                "应用启动",
                False,
                "无法连接到应用，请确保应用正在运行"
            )
            return False
        except Exception as e:
            self.log_test("应用启动", False, f"连接错误: {str(e)}")
            return False

    def test_freshdesk_connection(self):
        """测试Freshdesk API连接"""
        print("\n🎫 测试Freshdesk连接...")

        try:
            response = requests.get(f"{self.base_url}/test/connection", timeout=15)

            if response.status_code == 200:
                data = response.json()
                freshdesk_status = data.get('freshdesk', {})

                if freshdesk_status.get('status') == '成功':
                    self.log_test(
                        "Freshdesk连接",
                        True,
                        f"API连接成功 (域名: {freshdesk_status.get('domain')})"
                    )
                    return True
                else:
                    self.log_test(
                        "Freshdesk连接",
                        False,
                        "API连接失败",
                        freshdesk_status
                    )
                    return False
            else:
                self.log_test(
                    "Freshdesk连接",
                    False,
                    f"测试请求失败: HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_test("Freshdesk连接", False, f"测试错误: {str(e)}")
            return False

    def test_wordpress_webhook(self):
        """测试WordPress webhook端点"""
        print("\n🌐 测试WordPress webhook...")

        test_data = {
            "name": "测试用户",
            "email": "test@example.com",
            "phone": "123-456-7890",
            "company": "测试公司",
            "subject": f"测试工单 - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "priority": "medium",
            "ticket_type": "Question",
            "message": "这是一个自动化测试消息，请忽略。",
            "form_id": "test_form",
            "source_url": "http://test.example.com",
            "user_agent": "IntegrationTester/1.0"
        }

        try:
            response = requests.post(
                f"{self.base_url}/webhook/wordpress",
                json=test_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    ticket_info = data.get('ticket_created', {})
                    self.log_test(
                        "WordPress webhook",
                        True,
                        f"工单创建成功 (ID: {ticket_info.get('id')})",
                        ticket_info
                    )
                    return True
                else:
                    self.log_test(
                        "WordPress webhook",
                        False,
                        "工单创建失败",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "WordPress webhook",
                    False,
                    f"请求失败: HTTP {response.status_code}",
                    response.text
                )
                return False

        except Exception as e:
            self.log_test("WordPress webhook", False, f"测试错误: {str(e)}")
            return False

    def test_xero_configuration(self):
        """测试Xero配置"""
        print("\n💰 测试Xero配置...")

        client_id = os.getenv('XERO_CLIENT_ID')
        client_secret = os.getenv('XERO_CLIENT_SECRET')

        if not client_id or not client_secret:
            self.log_test(
                "Xero配置",
                False,
                "Xero客户端ID或密钥未配置"
            )
            return False

        try:
            response = requests.get(f"{self.base_url}/test/connection", timeout=10)

            if response.status_code == 200:
                data = response.json()
                xero_status = data.get('xero', {})

                if xero_status.get('status') == '已配置':
                    self.log_test(
                        "Xero配置",
                        True,
                        f"Xero已配置 (访问令牌: {'有' if xero_status.get('has_access_token') else '无'})"
                    )
                    return True
                else:
                    self.log_test(
                        "Xero配置",
                        False,
                        "Xero未正确配置",
                        xero_status
                    )
                    return False

        except Exception as e:
            self.log_test("Xero配置", False, f"测试错误: {str(e)}")
            return False

    def test_api_endpoints(self):
        """测试API端点"""
        print("\n🔌 测试API端点...")

        endpoints = [
            ('GET', '/', '主页'),
            ('GET', '/health', '健康检查'),
            ('GET', '/test/connection', '连接测试'),
        ]

        if os.getenv('XERO_CLIENT_ID'):
            endpoints.append(('GET', '/xero/auth', 'Xero授权'))

        all_passed = True

        for method, endpoint, name in endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                else:
                    response = requests.request(method, f"{self.base_url}{endpoint}", timeout=10)

                if response.status_code in [200, 302]:  # 302 for redirects
                    self.log_test(f"API端点 {name}", True, f"{method} {endpoint} - HTTP {response.status_code}")
                else:
                    self.log_test(f"API端点 {name}", False, f"{method} {endpoint} - HTTP {response.status_code}")
                    all_passed = False

            except Exception as e:
                self.log_test(f"API端点 {name}", False, f"请求错误: {str(e)}")
                all_passed = False

        return all_passed

    def test_security_features(self):
        """测试安全功能"""
        print("\n🔒 测试安全功能...")

        # 测试无效JSON的处理
        try:
            response = requests.post(
                f"{self.base_url}/webhook/wordpress",
                data="invalid json",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 400:
                self.log_test("安全 - 无效JSON处理", True, "正确拒绝无效JSON")
            else:
                self.log_test("安全 - 无效JSON处理", False, f"未正确处理无效JSON: HTTP {response.status_code}")

        except Exception as e:
            self.log_test("安全 - 无效JSON处理", False, f"测试错误: {str(e)}")

        # 测试缺少必需字段的处理
        try:
            response = requests.post(
                f"{self.base_url}/webhook/wordpress",
                json={"incomplete": "data"},
                timeout=10
            )

            if response.status_code == 400:
                self.log_test("安全 - 字段验证", True, "正确验证必需字段")
            else:
                self.log_test("安全 - 字段验证", False, f"字段验证失败: HTTP {response.status_code}")

        except Exception as e:
            self.log_test("安全 - 字段验证", False, f"测试错误: {str(e)}")

    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始集成测试...\n")
        print("=" * 60)

        # 按顺序运行测试
        tests = [
            self.test_environment_variables,
            self.test_app_startup,
            self.test_freshdesk_connection,
            self.test_api_endpoints,
            self.test_wordpress_webhook,
            self.test_xero_configuration,
            self.test_security_features
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                time.sleep(1)  # 避免请求过快
            except Exception as e:
                print(f"❌ 测试执行错误: {str(e)}")

        print("\n" + "=" * 60)
        print("📊 测试报告")
        print("=" * 60)

        # 显示摘要
        success_rate = (passed_tests / total_tests) * 100
        print(f"通过: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

        # 显示详细结果
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}: {result['message']}")

        # 保存测试报告
        self.save_test_report()

        print("\n🎯 建议:")
        if success_rate == 100:
            print("✅ 所有测试通过！系统运行正常。")
        elif success_rate >= 80:
            print("⚠️  大部分测试通过，请检查失败的测试项。")
        else:
            print("❌ 多个测试失败，请检查配置和连接。")

        return success_rate >= 80

    def save_test_report(self):
        """保存测试报告"""
        try:
            os.makedirs('logs', exist_ok=True)

            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": len(self.test_results),
                    "passed": sum(1 for r in self.test_results if r['success']),
                    "failed": sum(1 for r in self.test_results if not r['success'])
                },
                "results": self.test_results
            }

            with open('logs/test_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"\n📄 测试报告已保存: logs/test_report.json")

        except Exception as e:
            print(f"⚠️  保存测试报告失败: {str(e)}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='运行集成测试')
    parser.add_argument('--url', default=None, help='应用基础URL')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    parser.add_argument('--quick', action='store_true', help='快速测试（跳过某些测试）')

    args = parser.parse_args()

    # 检查应用是否在运行
    tester = IntegrationTester()

    if args.url:
        tester.base_url = args.url

    print(f"🎯 测试目标: {tester.base_url}")

    # 运行测试
    success = tester.run_all_tests()

    # 退出代码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()