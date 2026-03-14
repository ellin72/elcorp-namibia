"""Admin routes — audit logs, user management, system overview."""

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.middleware.auth import jwt_required
from app.middleware.rbac import roles_required
from app.services import audit_service, identity_service
from app.models.user import User, Role
from app.extensions import db


@api_v1_bp.route("/admin/audit-logs", methods=["GET"])
@jwt_required
@roles_required("admin")
def get_audit_logs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    user_id = request.args.get("user_id")
    action = request.args.get("action")
    entity_type = request.args.get("entity_type")

    result = audit_service.get_logs(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        page=page,
        per_page=per_page,
    )
    return jsonify({
        "items": [log.to_dict() for log in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    })


@api_v1_bp.route("/admin/users/<user_id>/roles", methods=["PUT"])
@jwt_required
@roles_required("admin")
def update_user_roles(user_id: str):
    body = request.get_json(force=True)
    role_names = body.get("roles", [])

    user = identity_service.get_user(user_id)
    roles = Role.query.filter(Role.name.in_(role_names)).all()
    user.roles = roles
    db.session.commit()

    audit_service.log_event(
        "admin.roles_updated",
        user_id=g.current_user_id,
        entity_type="user",
        entity_id=user_id,
        detail={"roles": role_names},
    )
    return jsonify(user.to_dict())


@api_v1_bp.route("/admin/users/<user_id>/deactivate", methods=["POST"])
@jwt_required
@roles_required("admin")
def deactivate_user(user_id: str):
    user = identity_service.get_user(user_id)
    user.is_active = False
    db.session.commit()
    audit_service.log_event(
        "admin.user_deactivated",
        user_id=g.current_user_id,
        entity_type="user",
        entity_id=user_id,
    )
    return jsonify(user.to_dict())


@api_v1_bp.route("/admin/stats", methods=["GET"])
@jwt_required
@roles_required("admin")
def system_stats():
    from app.models.payment import Payment
    from app.models.merchant import Merchant
    from app.models.kyc import KYCDocument

    return jsonify({
        "total_users": User.query.count(),
        "verified_users": User.query.filter_by(is_verified=True).count(),
        "total_payments": Payment.query.count(),
        "completed_payments": Payment.query.filter_by(status="completed").count(),
        "active_merchants": Merchant.query.filter_by(is_active=True).count(),
        "pending_kyc": KYCDocument.query.filter_by(status="pending").count(),
    })
