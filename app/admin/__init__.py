from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import abort
from ..extensions import db
from ..models import User, VinRecord, AuditLog

class SecureModelView(ModelView):
    can_create = True
    can_edit   = True
    can_delete = True

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == "admin"

    def inaccessible_callback(self, name, **kwargs):
        return abort(403)

class ReadOnlyModelView(SecureModelView):
    can_create = False
    can_edit   = False
    can_delete = False

    # Move filters/search out of __init__ into class attributes
    column_filters         = ["timestamp", "action", "user_id"]
    column_searchable_list = ["action", "details"]
    column_default_sort    = ("timestamp", True)
    page_size              = 50

def init_admin(app):
    admin = Admin(app, name="Elcorp Admin", template_mode="bootstrap4")
    admin.add_view(SecureModelView(User, db.session, name="Users"))
    admin.add_view(SecureModelView(VinRecord, db.session, name="VIN Records"))
    admin.add_view(ReadOnlyModelView(AuditLog, db.session, name="Audit Logs"))
    