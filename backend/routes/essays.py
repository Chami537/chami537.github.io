"""Register focused essay routes and expose their Blueprint."""

from backend.routes import essay_catalog, essay_content, essay_media, essay_metadata  # noqa: F401
from backend.routes.essay_context import bp
from backend.routes.essay_metadata import _apply_meta_updates, _validate_meta_slug
