"""
Identity interfaces - HTTP routes and API endpoints.
Flask blueprints for REST API.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Tuple
import os

from ..application import (
    RegisterUserDTO,
    UserLoginDTO,
    RegisterUserHandler,
    LoginUserHandler,
)
from ...shared.domain import ValidationException, ConflictError, UnauthorizedError
from ...shared.security import JWTHandler, AuthRateLimiter

# Create blueprint
identity_bp = Blueprint("identity", __name__, url_prefix="/api/v1/identity")


class IdentityAPI:
    """HTTP API endpoints for identity domain."""

    def __init__(self, register_handler: RegisterUserHandler, login_handler: LoginUserHandler):
        self.register_handler = register_handler
        self.login_handler = login_handler
        self.rate_limiter = AuthRateLimiter()
        self.jwt_handler = JWTHandler(os.getenv("JWT_SECRET_KEY", "dev-secret"))

    async def register(self) -> Tuple[Dict[str, Any], int]:
        """POST /register - Register a new user."""
        try:
            # Check rate limiting
            client_ip = request.remote_addr
            if not self.rate_limiter.check_registration_attempt(client_ip):
                return {"error": "TOO_MANY_REQUESTS", "message": "Registration limit exceeded"}, 429

            # Validate input
            data = request.get_json()
            dto = UserRegisterDTO(**data)

            # Handle command
            user = await self.register_handler.handle(
                RegisterUserCommand(
                    username=dto.username,
                    email=dto.email,
                    phone=dto.phone,
                    password=dto.password,
                )
            )

            return {
                "id": user.id,
                "username": user.username,
                "email": str(user.email),
                "message": "User registered successfully",
            }, 201

        except ValidationException as e:
            return e.to_dict(), 400
        except ConflictError as e:
            return e.to_dict(), 409
        except Exception as e:
            return {"error": "INTERNAL_ERROR", "message": str(e)}, 500

    async def login(self) -> Tuple[Dict[str, Any], int]:
        """POST /login - Authenticate user and get tokens."""
        try:
            # Validate input
            data = request.get_json()
            dto = UserLoginDTO(**data)

            # Check rate limiting
            if not self.rate_limiter.check_login_attempt(dto.username):
                return {
                    "error": "TOO_MANY_REQUESTS",
                    "message": "Too many login attempts. Please try again later.",
                }, 429

            # Handle command
            access_token, refresh_token, profile = await self.login_handler.handle(
                LoginUserCommand(
                    username=dto.username,
                    password=dto.password,
                    device_id=dto.device_id,
                    device_name=dto.device_name,
                )
            )

            # Reset rate limiter on successful login
            self.rate_limiter.check_login_attempt(dto.username)  # Clear attempts
            self.rate_limiter.reset_user_limits(dto.username)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "user": profile.dict(),
            }, 200

        except ValidationException as e:
            return e.to_dict(), 400
        except UnauthorizedError as e:
            return e.to_dict(), 401
        except Exception as e:
            return {"error": "INTERNAL_ERROR", "message": str(e)}, 500

    async def refresh(self) -> Tuple[Dict[str, Any], int]:
        """POST /refresh - Get new access token from refresh token."""
        try:
            data = request.get_json()
            refresh_token = data.get("refresh_token")

            if not refresh_token:
                return {"error": "VALIDATION_ERROR", "message": "Refresh token required"}, 400

            # Refresh the token
            new_access_token = self.jwt_handler.refresh_access_token(refresh_token)

            return {
                "access_token": new_access_token,
                "token_type": "Bearer",
            }, 200

        except UnauthorizedError as e:
            return e.to_dict(), 401
        except Exception as e:
            return {"error": "INTERNAL_ERROR", "message": str(e)}, 500


# Route handlers (to be registered with Flask app)
def register_routes(app, register_handler, login_handler):
    """Register identity routes with Flask app."""
    api = IdentityAPI(register_handler, login_handler)

    @identity_bp.route("/register", methods=["POST"])
    async def register():
        return await api.register()

    @identity_bp.route("/login", methods=["POST"])
    async def login():
        return await api.login()

    @identity_bp.route("/refresh", methods=["POST"])
    async def refresh():
        return await api.refresh()

    app.register_blueprint(identity_bp)
