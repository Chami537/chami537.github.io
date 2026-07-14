"""Register focused photo routes and expose their Blueprint."""

from backend.routes import photo_details, photo_files, photo_stories  # noqa: F401
from backend.routes.photo_context import bp
