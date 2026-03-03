from flask import Flask, jsonify, request, render_template, send_file
import os
import sys

# 1. 确保能找到项目里的其他文件夹
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.data_routes import data_bp
from routes.algorithm_routes import algorithm_bp
from routes.analysis_routes import analysis_bp
from routes.report_routes import report_bp
from utils.config import config_manager


def create_app():
    app = Flask(__name__,
                static_folder='static',
                template_folder='static/templates')

    # 使用环境变量中的密钥，如果不存在则从文件读取或生成一次并保存
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        secret_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                secret_key = f.read().strip()
        else:
            secret_key = os.urandom(24).hex()
            with open(secret_file, 'w') as f:
                f.write(secret_key)
    app.config['SECRET_KEY'] = secret_key
    app.config['UPLOAD_FOLDER'] = 'uploads'
    # 从 config.json 读取系统配置（默认关闭 debug）
    app.config['DEBUG'] = bool(config_manager.get_param("system.enable_debug", False))

    # 确保必要的文件夹存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'reports'), exist_ok=True)

    # 注册接口
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(algorithm_bp, url_prefix='/api/algorithm')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # --- 👇 页面路由配置 (修复 404 的关键) ---

    # --- 页面路由 ---

    @app.route('/')
    def index():
        """
        平台首页：对应首页/导航介绍页面。
        使用 render_template，而不是 send_file，确保后续可以在模板中使用 Jinja 变量，
        便于扩展仪表盘、动态标题等功能。
        """
        return render_template('index.html')

    @app.route('/analysis')
    def analysis_page():
        # 结果分析交互页面（旧版/高级分析页面）
        return render_template('analysis.html')

    @app.route('/report')  # 修复 500 错误
    def report_page():
        # 报告生成页面
        return render_template('report.html')

    @app.route('/data')  # 修复 /data 404
    def data_page():
        # 数据管理与预处理页面
        return render_template('data.html')

    @app.route('/algorithm')  # 修复 /algorithm 404
    def algorithm_page():
        # 算法配置页面
        return render_template('algorithm.html')

    @app.route('/monitor')
    def monitor_page():
        # 算法运行监控页面
        return render_template('monitor.html')

    @app.route('/analysis_result')
    def analysis_result_page():
        # 新版结果分析与可视化总览页面
        return render_template('analysis_result.html')

    # 可选：仪表盘/总结报告页面，如有需要可以在前端导航中挂载
    @app.route('/dashboard')
    def dashboard_page():
        return render_template(
            'dashboard.html',
            title="分析结果概览仪表盘",
            generated_at="自动生成",
            stats_summary={},
            charts=[],
        )

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", "5000"))
    print(f"🚀 服务已启动：http://127.0.0.1:{port}")
    # 关键：关闭自动重载（reloader），否则上传文件会触发重启，导致缓存/任务/结果丢失
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False), use_reloader=False)



