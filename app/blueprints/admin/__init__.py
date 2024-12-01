from flask import Blueprint

bp = Blueprint(
    'Admin',
    __name__,
    url_prefix='/admin',
    static_folder='static',
    template_folder='templates'
)