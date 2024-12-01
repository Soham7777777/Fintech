from flask import Blueprint

bp = Blueprint(
    'Blog',
    __name__,
    url_prefix='/blog',
    static_folder='static',
    template_folder='templates'
)