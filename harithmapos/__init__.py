from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from harithmapos.config import Config


db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
# Checks the CSRF token on every POST, including the small delete / quantity
# buttons that are not WTForms forms.
csrf = CSRFProtect()

login_manager.login_view = 'user_blueprint.login'
login_manager.login_message = 'Please sign in to continue.'
login_manager.login_message_category = 'info'

def create_app(Config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config_class)
    # nginx sits in front and passes the real scheme and client address.
    # Trust exactly one proxy, so links in SMS and emails use https://.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    if not app.config.get('SECRET_KEY'):
        raise RuntimeError(
            "HARITHMA_SECRET_KEY is not set. Add it to the environment (.env) before starting the app; "
            "generate one with: openssl rand -hex 32"
        )

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from harithmapos.template_helpers import register_template_helpers
    register_template_helpers(app)

    from harithmapos.views.error.handlers import error_blueprint
    from harithmapos.views.user.routes import user_blueprint
    from harithmapos.views.customer.routes import customer_blueprint
    from harithmapos.views.vehicle.routes import vehicle_blueprint
    from harithmapos.views.supplier.routes import supplier_blueprint
    from harithmapos.views.main.routes import main_blueprint
    from harithmapos.views.item.routes import item_blueprint
    from harithmapos.views.washbay.routes import washbay_blueprint
    from harithmapos.views.employee.routes import employee_blueprint
    from harithmapos.views.invoice.routes import invoice_blueprint
    from harithmapos.views.purchase_order.routes import purchase_order_blueprint
    from harithmapos.views.payment.routes import payment_blueprint
    from harithmapos.views.dashboard.routes import dashboard_blueprint
    from harithmapos.views.search.routes import search_blueprint
    from harithmapos.views.settings.routes import settings_blueprint
    from harithmapos.views.reports.routes import reports_blueprint
    from harithmapos.views.staff.routes import staff_blueprint
    from harithmapos.views.floor.routes import floor_blueprint

    app.register_blueprint(error_blueprint)
    app.register_blueprint(user_blueprint)
    app.register_blueprint(customer_blueprint)
    app.register_blueprint(vehicle_blueprint)
    app.register_blueprint(supplier_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(item_blueprint)
    app.register_blueprint(washbay_blueprint)
    app.register_blueprint(employee_blueprint)
    app.register_blueprint(invoice_blueprint)
    app.register_blueprint(purchase_order_blueprint)
    app.register_blueprint(payment_blueprint)
    app.register_blueprint(dashboard_blueprint)
    app.register_blueprint(search_blueprint)
    app.register_blueprint(settings_blueprint)
    app.register_blueprint(reports_blueprint)
    app.register_blueprint(staff_blueprint)
    app.register_blueprint(floor_blueprint)

    return app
