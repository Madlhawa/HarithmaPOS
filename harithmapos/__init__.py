from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from harithmapos.config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()

login_manager.login_view = 'user_blueprint.login'
login_manager.login_message_category = 'info'

def create_app(Config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config_class)

    db.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from harithmapos.user.routes import user_blueprint
    from harithmapos.customer.routes import customer_blueprint
    from harithmapos.vehical.routes import vehical_blueprint
    from harithmapos.supplier.routes import supplier_blueprint
    from harithmapos.main.routes import main_blueprint

    app.register_blueprint(user_blueprint)
    app.register_blueprint(customer_blueprint)
    app.register_blueprint(vehical_blueprint)
    app.register_blueprint(supplier_blueprint)
    app.register_blueprint(main_blueprint)

    return app