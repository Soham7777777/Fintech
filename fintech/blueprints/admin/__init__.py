from flask import Blueprint, render_template
from fintech.blueprints.admin.forms import AllTimeHighForm, PatternsForm
from fintech.blueprints.admin.algos import all_time_high_algo, get_plotting_data, get_symbols
from fintech.blueprints.admin.patterns import get_chart


bp = Blueprint(
    'Admin',
    __name__,
    url_prefix='/admin',
    static_folder='static',
    template_folder='templates'
)


@bp.route('/', methods=['GET', 'POST'])
def home() -> str:
    form = AllTimeHighForm()
    data = None
    if form.validate_on_submit():
        data = sorted(all_time_high_algo(form.date.data), key=lambda x : x[1]) # type: ignore
    return render_template('admin/alltimehigh.html', form=form, data=data)


@bp.route('/chart-patterns', methods=['GET', 'POST'])
def chart_patterns() -> str:
    form = PatternsForm()
    form.symbol.choices = [(x['Symbol'], x['Symbol']) for x in get_symbols()]
    
    if form.validate_on_submit():
        symbol = form.symbol.data
        pattern = form.pattern.data
        rows = get_plotting_data(symbol)
        chart = get_chart(symbol, pattern)
        return render_template('admin/chartpatterns.j2', rows=rows, chart=chart, form=form, pattern_name=pattern, symbol=symbol)
    return render_template('admin/chartpatterns.j2', form=form)
