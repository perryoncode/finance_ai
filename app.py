from flask import Flask
from config import settings
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.chat import chat_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(chat_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True,port=8080)
