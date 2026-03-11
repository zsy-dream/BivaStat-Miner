import os
import platform

from app import create_app


def main():
    app = create_app()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8001"))

    system_name = platform.system().lower()
    if system_name == "windows":
        from waitress import serve

        print(f"Service started with waitress: http://127.0.0.1:{port}")
        serve(app, host=host, port=port)
        return

    print("Use gunicorn in Linux production environments: gunicorn wsgi:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT")
    app.run(host=host, port=port, debug=app.config.get('DEBUG', False), use_reloader=False)


if __name__ == "__main__":
    main()
