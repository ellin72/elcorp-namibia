"""Payment routes — create, process, list, tokenisation."""

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.middleware.auth import jwt_required
from app.services import payment_service
from app.utils.validators import validate_payment_payload


# ---- Payment tokens ----

@api_v1_bp.route("/payments/tokens", methods=["POST"])
@jwt_required
def create_token():
    body = request.get_json(force=True)
    token = payment_service.create_payment_token(
        user_id=g.current_user_id,
        instrument_type=body.get("instrument_type", ""),
        last_four=body.get("last_four", ""),
    )
    return jsonify(token.to_dict()), 201


# ---- Payments ----

@api_v1_bp.route("/payments", methods=["POST"])
@jwt_required
def create_payment():
    data = validate_payment_payload(request.get_json(force=True))
    payment = payment_service.create_payment(
        user_id=g.current_user_id,
        merchant_id=data["merchant_id"],
        amount=data["amount"],
        currency=data["currency"],
        description=data.get("description", ""),
        payment_token_id=data.get("payment_token_id"),
    )
    return jsonify(payment.to_dict()), 201


@api_v1_bp.route("/payments/<payment_id>/process", methods=["POST"])
@jwt_required
def process_payment(payment_id: str):
    payment = payment_service.process_payment(payment_id)
    return jsonify(payment.to_dict())


@api_v1_bp.route("/payments/<payment_id>", methods=["GET"])
@jwt_required
def get_payment(payment_id: str):
    payment = payment_service.get_payment(payment_id)
    return jsonify(payment.to_dict())


@api_v1_bp.route("/payments", methods=["GET"])
@jwt_required
def list_my_payments():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    result = payment_service.list_user_payments(g.current_user_id, page=page, per_page=per_page)
    return jsonify({
        "items": [p.to_dict() for p in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    })


# ---- Test payout (sandbox) ----

@api_v1_bp.route("/payments/simulate-payout", methods=["POST"])
@jwt_required
def simulate_payout():
    body = request.get_json(force=True)
    result = payment_service.simulate_payout(
        merchant_id=body.get("merchant_id", ""),
        amount=body.get("amount", 0),
        currency=body.get("currency", "NAD"),
    )
    return jsonify(result)
