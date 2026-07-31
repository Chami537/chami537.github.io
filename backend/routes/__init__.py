from backend.routes import ai, about, contact, dashboard, essays, friends, git_api, health, music, photos, readme, stack, tracks, work

_BLUEPRINTS = (
    ai.bp, about.bp, contact.bp, dashboard.bp, essays.bp, friends.bp,
    git_api.bp, health.bp, music.bp, photos.bp, readme.bp, stack.bp, tracks.bp, work.bp,
)


def register_blueprints(app):
    """Register all API blueprints on an application instance."""
    for blueprint in _BLUEPRINTS:
        app.register_blueprint(blueprint)
