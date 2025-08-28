# app/main/routes.py
from flask import render_template
from datetime import datetime, timedelta
from . import bp
from ..models import AuditLog, User, VinRecord, Role


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/governance")
def governance():
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    # Counts for VIN lookups and additions in the past week
    total_lookups = AuditLog.query.filter(
        AuditLog.action == "vin_search",
        AuditLog.timestamp >= one_week_ago
    ).count()

    vins_added = AuditLog.query.filter(
        AuditLog.action == "vin_create",
        AuditLog.timestamp >= one_week_ago
    ).count()

    # Role-based user counts using .has() for single-role relationship
    verifiers_count = User.query.filter(
        User.role.has(Role.name == "verifier")
    ).count()

    admins_count = User.query.filter(
        User.role.has(Role.name == "admin")
    ).count()

    # Total VIN records in the system
    total_vins = VinRecord.query.count()

    return render_template(
        "main/governance.html",
        total_lookups=total_lookups,
        vins_added=vins_added,
        verifiers_count=verifiers_count,
        admins_count=admins_count,
        total_vins=total_vins
    )

from flask_login import current_user

@bp.route("/debug-role")
def debug_role():
    "Debug route to check current user's role"
    if current_user.is_authenticated:
        role_name = current_user.role.name if current_user.role else "No role assigned"
        print(f"[DEBUG] Current user role: {role_name}")
        return f"Current user role: {role_name}"
    else:
        print("[DEBUG] No user is logged in")
        return "No user logged in"
