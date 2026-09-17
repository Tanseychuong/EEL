from flask import Blueprint

admin_bp = Blueprint("admin", __name__)

# GET /opportunities/pending, POST /opportunities/<id>/approve,
# POST /opportunities/<id>/reject, GET/POST /categories,
# GET /users, POST /users/<id>/grant-premium — Phase 4
