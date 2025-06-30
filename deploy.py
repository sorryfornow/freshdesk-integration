#!/usr/bin/env python3
"""
部署脚本
用于部署 WordPress + Freshdesk + Xero 集成系统到生产环境
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime


class Deployer:
    def __init__(self, environment='production'):
        self.environment = environment
        self.project_root = Path(__file__).parent
        self.backup_dir = self.project_root / 'backups'
        self.deploy_dir = self.project_root / 'deploy'

    def log(self, message, level='INFO'):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def run_command(self, command, check=True, capture_output=False):
        """运行系统命令"""
        self.log(f"执行命令: {command}")

        try:
            if capture_output:
                result = subprocess.run(
                    command,
                    shell=True,
                    check=check,
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
            else:
                subprocess.run(command, shell=True, check=check)
                return True
        except subprocess.CalledProcessError as e:
            self.log(f"命令执行失败: {e}", 'ERROR')
            return False

    def check_prerequisites(self):
        """检查部署前提条件"""
        self.log("检查部署前提条件...")

        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 7):
            self.log("需要Python 3.7或更高版本", 'ERROR')
            return False

        # 检查必需文件
        required_files = [
            'app.py',
            'requirements.txt',
            '.env.example',
            'config.py',
            'utils.py'
        ]

        missing_files = []
        for file in required_files:
            if not (self.project_root / file).exists():
                missing_files.append(file)

        if missing_files:
            self.log(f"缺少必需文件: {', '.join(missing_files)}", 'ERROR')
            return False

        # 检查环境变量文件
        if not (self.project_root / '.env').exists():
            self.log("未找到.env文件，请从.env.example复制并配置", 'ERROR')
            return False

        self.log("前提条件检查通过")
        return True

    def create_backup(self):
        """创建备份"""
        self.log("创建部署备份...")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{self.environment}_{timestamp}"
        backup_path = self.backup_dir / backup_name

        # 创建备份目录
        backup_path.mkdir(parents=True, exist_ok=True)

        # 备份重要文件
        files_to_backup = [
            '.env',
            'logs/',
            'instance/',
            'data/'
        ]

        for item in files_to_backup:
            source = self.project_root / item
            if source.exists():
                if source.is_file():
                    shutil.copy2(source, backup_path)
                else:
                    shutil.copytree(source, backup_path / item, dirs_exist_ok=True)

        self.log(f"备份创建完成: {backup_path}")
        return backup_path

    def setup_virtual_environment(self):
        """设置虚拟环境"""
        self.log("设置虚拟环境...")

        venv_path = self.project_root / 'venv'

        # 创建虚拟环境（如果不存在）
        if not venv_path.exists():
            self.log("创建新虚拟环境...")
            if not self.run_command(f"python3 -m venv {venv_path}"):
                return False

        # 激活虚拟环境并安装依赖
        if os.name == 'nt':  # Windows
            activate_script = venv_path / 'Scripts' / 'activate.bat'
            pip_cmd = f"{venv_path}/Scripts/pip"
        else:  # Unix/Linux/Mac
            activate_script = venv_path / 'bin' / 'activate'
            pip_cmd = f"{venv_path}/bin/pip"

        # 升级pip
        if not self.run_command(f"{pip_cmd} install --upgrade pip"):
            return False

        # 安装依赖
        if not self.run_command(f"{pip_cmd} install -r requirements.txt"):
            return False

        self.log("虚拟环境设置完成")
        return True

    def run_tests(self):
        """运行测试"""
        self.log("运行部署前测试...")

        # 运行集成测试
        test_result = self.run_command(
            "python test_integration.py --quick",
            check=False
        )

        if not test_result:
            self.log("测试失败，建议修复后再部署", 'WARNING')
            return False

        self.log("测试通过")
        return True

    def setup_systemd_service(self, service_name="freshdesk-integration"):
        """设置systemd服务（Linux）"""
        if os.name == 'nt':
            self.log("Windows系统跳过systemd配置")
            return True

        self.log("配置systemd服务...")

        service_content = f"""[Unit]
Description=Freshdesk Integration Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory={self.project_root}
Environment=PATH={self.project_root}/venv/bin
ExecStart={self.project_root}/venv/bin/python run.py --env production --no-debug
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

        service_file = f"/etc/systemd/system/{service_name}.service"

        try:
            with open(service_file, 'w') as f:
                f.write(service_content)

            # 重新加载systemd配置
            self.run_command("systemctl daemon-reload")
            self.run_command(f"systemctl enable {service_name}")

            self.log(f"Systemd服务配置完成: {service_name}")
            return True

        except PermissionError:
            self.log("需要sudo权限来配置systemd服务", 'WARNING')
            self.log(f"请手动创建 {service_file}")
            self.log("内容:")
            print(service_content)
            return False

    def setup_nginx_config(self):
        """设置Nginx配置"""
        self.log("生成Nginx配置...")

        nginx_config = """
server {
    listen 80;
    server_name your-domain.com;  # 修改为你的域名

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;  # 修改为你的域名

    # SSL证书配置
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 日志
    access_log /var/log/nginx/freshdesk-integration.access.log;
    error_log /var/log/nginx/freshdesk-integration.error.log;

    # 代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # 静态文件
    location /static {
        alias /path/to/your/project/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
}
"""

        config_path = self.project_root / 'nginx.conf'
        with open(config_path, 'w') as f:
            f.write(nginx_config)

        self.log(f"Nginx配置已生成: {config_path}")
        self.log("请根据你的域名和SSL证书路径修改配置")

        return True

    def setup_production_env(self):
        """设置生产环境配置"""
        self.log("配置生产环境...")

        # 创建生产环境配置文件
        prod_env_path = self.project_root / '.env.production'

        if not prod_env_path.exists():
            # 从.env复制并修改
            env_content = (self.project_root / '.env').read_text()

            # 修改关键配置
            env_content = env_content.replace('FLASK_ENV=development', 'FLASK_ENV=production')
            env_content = env_content.replace('FLASK_DEBUG=True', 'FLASK_DEBUG=False')
            env_content = env_content.replace('LOG_LEVEL=DEBUG', 'LOG_LEVEL=INFO')

            prod_env_path.write_text(env_content)
            self.log(f"生产环境配置已创建: {prod_env_path}")

        # 设置目录权限
        os.makedirs(self.project_root / 'logs', exist_ok=True)
        os.makedirs(self.project_root / 'instance', exist_ok=True)

        return True

    def deploy(self, skip_tests=False, skip_backup=False):
        """执行部署"""
        self.log(f"开始部署到 {self.environment} 环境...")

        # 检查前提条件
        if not self.check_prerequisites():
            self.log("前提条件检查失败，部署终止", 'ERROR')
            return False

        # 创建备份
        if not skip_backup:
            backup_path = self.create_backup()

        # 设置虚拟环境
        if not self.setup_virtual_environment():
            self.log("虚拟环境设置失败", 'ERROR')
            return False

        # 运行测试
        if not skip_tests:
            if not self.run_tests():
                response = input("测试失败，是否继续部署? (y/N): ")
                if response.lower() != 'y':
                    self.log("部署取消")
                    return False

        # 生产环境特定配置
        if self.environment == 'production':
            self.setup_production_env()
            self.setup_systemd_service()
            self.setup_nginx_config()

        self.log("部署完成！")

        # 显示后续步骤
        self.show_post_deploy_instructions()

        return True

    def show_post_deploy_instructions(self):
        """显示部署后说明"""
        self.log("部署后配置说明:")

        instructions = [
            "1. 检查并修改生产环境配置文件 .env.production",
            "2. 配置SSL证书（如果使用HTTPS）",
            "3. 修改nginx.conf中的域名和证书路径",
            "4. 启动服务:",
            "   sudo systemctl start freshdesk-integration",
            "   sudo systemctl reload nginx",
            "5. 检查服务状态:",
            "   sudo systemctl status freshdesk-integration",
            "   sudo journalctl -f -u freshdesk-integration",
            "6. 测试应用:",
            "   python test_integration.py --url https://your-domain.com",
            "7. 配置防火墙允许HTTP/HTTPS流量",
            "8. 设置日志轮转（logrotate）"
        ]

        for instruction in instructions:
            print(f"   {instruction}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='部署Freshdesk集成应用')
    parser.add_argument('--env', choices=['development', 'staging', 'production'],
                        default='production', help='部署环境')
    parser.add_argument('--skip-tests', action='store_true', help='跳过测试')
    parser.add_argument('--skip-backup', action='store_true', help='跳过备份')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行（不执行实际部署）')

    args = parser.parse_args()

    deployer = Deployer(args.env)

    if args.dry_run:
        deployer.log("模拟运行模式 - 不会执行实际部署")
        deployer.check_prerequisites()
        return

    # 确认部署
    if args.env == 'production':
        response = input(f"确认部署到 {args.env} 环境? 这将影响生产系统 (y/N): ")
        if response.lower() != 'y':
            print("部署取消")
            return

    # 执行部署
    success = deployer.deploy(
        skip_tests=args.skip_tests,
        skip_backup=args.skip_backup
    )

    if success:
        print("🎉 部署成功！")
        sys.exit(0)
    else:
        print("❌ 部署失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()