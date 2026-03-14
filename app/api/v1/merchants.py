"""Merchant onboarding routes."""

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.middleware.auth import jwt_required
from app.middleware.rbac import roles_required
from app.services import merchant_service
from app.utils.validators import validate_merchant_payload


@api_v1_bp.route("/merchants", methods=["POST"])
@jwt_required
@roles_required("admin")
def onboard_merchant():
    data = validate_merchant_payload(request.get_json(force=True))
    merchant = merchant_service.onboard_merchant(data, onboarded_by=g.current_user_id)
    return jsonify(merchant.to_dict(include_keys=True)), 201


@api_v1_bp.route("/merchants", methods=["GET"])
@jwt_required
@roles_required("admin", "staff")
def list_merchants():
    page = request.args.get("page", 1, type=int)
    result = merchant_service.list_merchants(page=page)
    return jsonify({
        "items": [m.to_dict() for m in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    })


@api_v1_bp.route("/merchants/<merchant_id>", methods=["GET"])
@jwt_required
@roles_required("admin", "staff")
def get_merchant(merchant_id: str):
    merchant = merchant_service.get_merchant(merchant_id)
    return jsonify(merchant.to_dict(include_keys="admin" in g.current_roles))


@api_v1_bp.route("/merchants/<merchant_id>", methods=["PUT"])
@jwt_required
@roles_required("admin")
def update_merchant(merchant_id: str):
    data = request.get_json(force=True)
    merchant = merchant_service.update_merchant(merchant_id, data)
    return jsonify(merchant.to_dict())


@api_v1_bp.route("/merchants/<merchant_id>/deactivate", methods=["POST"])
@jwt_required
@roles_required("admin")
def deactivate_merchant(merchant_id: str):
    merchant = merchant_service.deactivate_merchant(merchant_id)
    return jsonify(merchant.to_dict())
