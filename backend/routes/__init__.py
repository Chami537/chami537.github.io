from backend.routes import about, contact, dashboard, essays, friends, git_api, health, music, photos, readme, stack, work

_BLUEPRINTS = (
    about.bp, contact.bp, dashboard.bp, essays.bp, friends.bp,
    git_api.bp, health.bp, music.bp, photos.bp, readme.bp, stack.bp, work.bp,
)


def register_blueprints(app):
    """Register all API blueprints on an application instance."""
    for blueprint in _BLUEPRINTS:
        app.register_blueprint(blueprint)
