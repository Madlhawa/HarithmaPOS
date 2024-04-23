from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

import os
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['MAIL_SERVER'] = 'smtp.mailersend.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.environ.get('HARITHMA_EMAIL')
app.config['MAIL_PASSWORD'] = os.environ.get('HARITHMA_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
mail = Mail(app)

login_manager.login_view = 'user_blueprint.login'
login_manager.login_message_category = 'info'

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