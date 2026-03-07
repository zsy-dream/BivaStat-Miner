from flask import Flask, jsonify, request, send_file
import os
import sys
from flask_cors import CORS

# 1. 确保能找到项目里的其他文件夹
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.data_routes import data_bp
from routes.algorithm_routes import algorithm_bp
from routes.analysis_routes import analysis_bp
from routes.report_routes import report_bp
# 修复：导入可视化蓝图
from routes.visualization_routes import visualization_bp
from routes.ai_routes import ai_bp
from utils.config import config_manager
from utils.json_utils import AppJSONProvider


def create_app():
    app = Flask(__name__,
                static_folder='static')
    app.json = AppJSONProvider(app)
    
    # 跨域支持：读取环境变量，支持本地开发和生产部署
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*')
    if allowed_origins != '*':
        origins_list = [o.strip() for o in allowed_origins.split(',')]
        CORS(app, origins=origins_list)
    else:
        CORS(app)

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
    # 增加上传限制到 100MB
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 
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
    # 修复：注册可视化接口
    app.register_blueprint(visualization_bp, url_prefix='/api/visualization')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')

    @app.route('/')
    def health_check():
        return jsonify({"status": "healthy", "message": "API Server is running"})

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", "8001"))
    print(f"Service started: http://127.0.0.1:{port}")
    # 关键：关闭自动重载（reloader），否则上传文件会触发重启，导致缓存/任务/结果丢失
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False), use_reloader=False)

