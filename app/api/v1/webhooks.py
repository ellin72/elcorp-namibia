"""Webhook management routes for merchants."""

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.middleware.auth import jwt_required
from app.middleware.rbac import roles_required
from app.services import webhook_service


@api_v1_bp.route("/webhooks", methods=["POST"])
@jwt_required
@roles_required("admin")
def create_webhook():
    body = request.get_json(force=True)
    sub = webhook_service.create_subscription(
        merchant_id=body["merchant_id"],
        url=body["url"],
        events=body.get("events", "*"),
    )
    return jsonify({**sub.to_dict(), "secret": sub.secret}), 201


@api_v1_bp.route("/webhooks/<merchant_id>", methods=["GET"])
@jwt_required
@roles_required("admin", "staff")
def list_webhooks(merchant_id: str):
    subs = webhook_service.list_subscriptions(merchant_id)
    return jsonify([s.to_dict() for s in subs])


@api_v1_bp.route("/webhooks/<subscription_id>", methods=["DELETE"])
@jwt_required
@roles_required("admin")
def delete_webhook(subscription_id: str):
    webhook_service.delete_subscription(subscription_id)
    return jsonify({"deleted": True})
