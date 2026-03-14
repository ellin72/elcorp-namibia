"""Identity routes — profile, KYC upload, verification."""

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.middleware.auth import jwt_required
from app.middleware.rbac import roles_required
from app.services import identity_service, kyc_service


# ---- Profile ----

@api_v1_bp.route("/me", methods=["GET"])
@jwt_required
def get_current_user():
    user = identity_service.get_user(g.current_user_id)
    return jsonify(user.to_dict(include_sensitive=True))


@api_v1_bp.route("/me", methods=["PUT"])
@jwt_required
def update_current_user():
    data = request.get_json(force=True)
    user = identity_service.update_profile(g.current_user_id, data)
    return jsonify(user.to_dict(include_sensitive=True))


@api_v1_bp.route("/me/permissions", methods=["GET"])
@jwt_required
def get_my_permissions():
    """Return the flattened permission set for the current user."""
    user = identity_service.get_user(g.current_user_id)
    perms: set[str] = set()
    for role in user.roles:
        for perm in getattr(role, "permissions", []):
            perms.add(perm.codename)
    return jsonify({"permissions": sorted(perms)})


@api_v1_bp.route("/users/<user_id>", methods=["GET"])
@jwt_required
@roles_required("admin", "staff")
def get_user(user_id: str):
    user = identity_service.get_user(user_id)
    return jsonify(user.to_dict(include_sensitive=True))


@api_v1_bp.route("/users", methods=["GET"])
@jwt_required
@roles_required("admin", "staff")
def list_users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    result = identity_service.list_users(page=page, per_page=per_page)
    return jsonify({
        "items": [u.to_dict() for u in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    })


# ---- KYC upload ----

@api_v1_bp.route("/kyc/upload", methods=["POST"])
@jwt_required
def upload_kyc():
    doc_type = request.form.get("document_type", "")
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "file is required"}), 400
    doc = kyc_service.upload_document(g.current_user_id, doc_type, file)
    return jsonify(doc.to_dict()), 201


@api_v1_bp.route("/kyc/documents", methods=["GET"])
@jwt_required
def get_my_documents():
    docs = kyc_service.get_documents(g.current_user_id)
    return jsonify([d.to_dict() for d in docs])


# ---- KYC review (staff/admin) ----

@api_v1_bp.route("/kyc/<doc_id>/review", methods=["POST"])
@jwt_required
@roles_required("admin", "staff")
def review_kyc(doc_id: str):
    body = request.get_json(force=True)
    doc = kyc_service.review_document(
        doc_id=doc_id,
        reviewer_id=g.current_user_id,
        decision=body.get("decision", ""),
        rejection_reason=body.get("rejection_reason", ""),
    )
    return jsonify(doc.to_dict())


@api_v1_bp.route("/kyc/pending", methods=["GET"])
@jwt_required
@roles_required("admin", "staff")
def get_pending_kyc():
    page = request.args.get("page", 1, type=int)
    result = kyc_service.get_pending_documents(page=page)
    return jsonify({
        "items": [d.to_dict() for d in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    })
