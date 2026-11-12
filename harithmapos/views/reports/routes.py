"""Reports for owners: the sales dashboard."""
from flask import Blueprint, render_template, request

from harithmapos import reports
from harithmapos.permissions import owner_required

reports_blueprint = Blueprint('reports_blueprint', __name__)


@reports_blueprint.route('/app/reports/sales', methods=['GET'])
@owner_required
def sales():
    period = reports.period_from_args(request.args.get('range'), request.args.get('from'), request.args.get('to'))
    data = reports.sales_report(period)
    return render_template('reports/sales.html', title='Sales', r=data, presets=reports.PRESETS)
