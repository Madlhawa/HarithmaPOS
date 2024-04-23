from flask import Blueprint, render_template

error_blueprint = Blueprint('error_blueprint', __name__)

@error_blueprint.app_errorhandler(404)
def error_404(error):
    return render_template('error/404.html'), 404

@error_blueprint.app_errorhandler(403)
def error_403(error):
    return render_template('error/403.html'), 403

@error_blueprint.app_errorhandler(500)
def error_500(error):
    return render_template('error/500.html'), 500