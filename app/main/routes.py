# app/main/routes.py
# from sqlalchemy import func
from flask import render_template
from datetime import datetime, timedelta
from . import bp
from ..models import AuditLog, User, VinRecord


@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/governance")
def governance():
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    total_lookups = AuditLog.query.filter(
        AuditLog.action=="vin_search",
        AuditLog.timestamp>=one_week_ago).count()
    vins_added = AuditLog.query.filter(
        AuditLog.action=="vin_create",
        AuditLog.timestamp>=one_week_ago).count()
    verifiers_count = User.query.filter_by(role="verifier").count()
    admins_count = User.query.filter_by(role="admin").count()
    total_vins = VinRecord.query.count()
    return render_template("main/governance.html",
        total_lookups=total_lookups,
        vins_added=vins_added,
        verifiers_count=verifiers_count,
        admins_count=admins_count,
        total_vins=total_vins)
    
    