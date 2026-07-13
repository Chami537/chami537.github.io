"""Essay-specific projections shared by routes and static generation."""


class EssayService:
    """Apply essay domain rules without coupling callers to JSON storage."""

    def __init__(self, repository):
        self.repository = repository

    def list_for_admin(self, parse_date, has_password):
        essays = self.repository.list()
        for essay in essays:
            essay['date_display'] = parse_date(essay.get('date', ''))
            essay['password_set'] = has_password(essay['slug'])
        return essays

    def public_listing(self, essays, parse_date, get_password):
        visible = []
        all_tags = set()
        for essay in essays:
            password_protected = bool(get_password(essay.get('slug', '')))
            for tag in essay.get('tag', '').replace(',', '，').split('，'):
                tag = tag.strip()
                if tag:
                    all_tags.add(tag)
            item = {key: value for key, value in essay.items() if key != 'password'}
            item['date_display'] = parse_date(essay.get('date', ''))
            item['password_protected'] = password_protected
            visible.append(item)
        return visible, all_tags
