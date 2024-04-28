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

    from harithmapos.error.handlers import error_blueprint
    from harithmapos.user.routes import user_blueprint
    from harithmapos.customer.routes import customer_blueprint
    from harithmapos.vehical.routes import vehical_blueprint
    from harithmapos.supplier.routes import supplier_blueprint
    from harithmapos.main.routes import main_blueprint
    from harithmapos.item.routes import item_blueprint
    from harithmapos.washbay.routes import washbay_blueprint
    from harithmapos.employee.routes import employee_blueprint
    from harithmapos.invoice.routes import invoice_head_blueprint

    app.register_blueprint(error_blueprint)
    app.register_blueprint(user_blueprint)
    app.register_blueprint(customer_blueprint)
    app.register_blueprint(vehical_blueprint)
    app.register_blueprint(supplier_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(item_blueprint)
    app.register_blueprint(washbay_blueprint)
    app.register_blueprint(employee_blueprint)
    app.register_blueprint(invoice_head_blueprint)

    return app