"""
Shared access-control decorators, applied on top of Flask-JWT-Extended's
@jwt_required(). One place for the four-tier access model from PLAN.md:
Anonymous / Free / Premium / Admin.

Phase 1 will fill these in, e.g.:
"""
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import User

def login_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = User.query.get(get_jwt_identity())
        if not user or not user.is_admin():

            return {"error": "Admin access required"}, 403
        return fn(*args, **kwargs)
    return wrapper

