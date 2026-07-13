from backend.essay_service import EssayService


class MemoryEssayRepository:
    def __init__(self, essays):
        self.essays = essays

    def list(self):
        return self.essays


def test_essay_service_public_listing_marks_protected_metadata_only():
    service = EssayService(MemoryEssayRepository([]))
    essays = [{'slug': 'secret', 'title': 'Secret', 'tag': '技术', 'password': 'never-public'}]

    public, tags = service.public_listing(essays, lambda value: 'formatted', lambda slug: 'pw')

    assert public == [{
        'slug': 'secret', 'title': 'Secret', 'tag': '技术',
        'date_display': 'formatted', 'password_protected': True,
    }]
    assert tags == {'技术'}


def test_essay_service_admin_listing_adds_status_without_password_value():
    essays = [{'slug': 'secret', 'title': 'Secret'}]
    service = EssayService(MemoryEssayRepository(essays))

    result = service.list_for_admin(lambda value: 'formatted', lambda slug: True)

    assert result[0]['date_display'] == 'formatted'
    assert result[0]['password_set'] is True
    assert 'password' not in result[0]
