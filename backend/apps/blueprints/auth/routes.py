from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

# POST /register, POST /login, POST /refresh, GET /me — Phase 1
