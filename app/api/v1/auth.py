"""Authentication routes — login, signup, refresh, logout."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.extensions import limiter
from app.middleware.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    jwt_required,
)
from app.services import identity_service
from app.services.audit_service import log_event
from app.utils.validators import validate_signup_payload


@api_v1_bp.route("/auth/signup", methods=["POST"])
@limiter.limit("10/minute")
def signup():
    data = validate_signup_payload(request.get_json(force=True))
    user = identity_service.signup(**data)
    access = create_access_token(user.id, [r.name for r in user.roles])
    refresh = create_refresh_token(user.id)
    return jsonify({
        "user": user.to_dict(),
        "access_token": access,
        "refresh_token": refresh,
    }), 201


@api_v1_bp.route("/auth/login", methods=["POST"])
@limiter.limit("20/minute")
def login():
    body = request.get_json(force=True)
    user = identity_service.authenticate(body.get("email", ""), body.get("password", ""))
    access = create_access_token(user.id, [r.name for r in user.roles])
    refresh = create_refresh_token(user.id)
    return jsonify({
        "user": user.to_dict(),
        "access_token": access,
        "refresh_token": refresh,
    })


@api_v1_bp.route("/auth/refresh", methods=["POST"])
def refresh():
    body = request.get_json(force=True)
    token = body.get("refresh_token", "")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        return jsonify({"error": "Invalid token type"}), 401
    user = identity_service.get_user(payload["sub"])
    access = create_access_token(user.id, [r.name for r in user.roles])
    return jsonify({"access_token": access})


@api_v1_bp.route("/auth/validate", methods=["GET"])
@jwt_required
def validate_token():
    from flask import g
    return jsonify({"valid": True, "user_id": g.current_user_id})


@api_v1_bp.route("/auth/logout", methods=["POST"])
@jwt_required
def logout():
    from flask import g
    log_event("auth.logout", user_id=g.current_user_id, entity_type="user", entity_id=g.current_user_id)
    return jsonify({"message": "Logged out"})
