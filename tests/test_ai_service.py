"""DeepSeek editorial service contract tests."""

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from backend.ai_service import AIServiceError, assist_essay


class FakeResponse:
    def __init__(self, payload):
        self._stream = BytesIO(json.dumps(payload).encode('utf-8'))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self._stream.read(size)


def _deepseek_response(content):
    return {
        'id': 'chat-test',
        'choices': [{
            'index': 0,
            'message': {'role': 'assistant', 'content': content},
            'finish_reason': 'stop',
        }],
        'usage': {
            'prompt_tokens': 10,
            'completion_tokens': 4,
            'total_tokens': 14,
        },
    }


def test_assist_essay_sends_json_mode_request_and_returns_summary(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')
    seen = {}

    def opener(request, timeout):
        seen['headers'] = dict(request.header_items())
        seen['body'] = json.loads(request.data)
        seen['timeout'] = timeout
        return FakeResponse(_deepseek_response('{"excerpt":"精炼摘要"}'))

    result = assist_essay(
        'summary',
        '正文',
        title='标题',
        existing_tags=['技术'],
        opener=opener,
    )

    assert result == {
        'result': {'excerpt': '精炼摘要'},
        'usage': {'prompt_tokens': 10, 'completion_tokens': 4},
    }
    assert seen['body']['model'] == 'deepseek-chat'
    assert seen['body']['response_format'] == {'type': 'json_object'}
    assert seen['body']['max_tokens'] == 1500
    assert seen['body']['stream'] is False
    assert seen['timeout'] == 30
    assert seen['headers']['Authorization'] == 'Bearer test-secret'


def test_assist_essay_passes_timeout_as_keyword(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')
    seen = {}

    def opener(_request, *, timeout):
        seen['timeout'] = timeout
        return FakeResponse(_deepseek_response('{"excerpt":"摘要"}'))

    assist_essay('summary', '正文', opener=opener)

    assert seen == {'timeout': 30}


@pytest.mark.parametrize(
    ('task', 'content', 'expected'),
    [
        (
            'tags',
            '{"tags":["技术","Python","教程"]}',
            {'tags': ['技术', 'Python', '教程']},
        ),
        (
            'polish',
            '{"content":"润色正文"}',
            {'content': '润色正文'},
        ),
        (
            'review',
            '{"issues":[{"type":"文字","message":"重复","suggestion":"删除"}]}',
            {'issues': [{'type': '文字', 'message': '重复', 'suggestion': '删除'}]},
        ),
        (
            'title',
            '{"titles":["标题一","标题二","标题三"]}',
            {'titles': ['标题一', '标题二', '标题三']},
        ),
        (
            'continue',
            '{"content":"自然续写"}',
            {'content': '自然续写'},
        ),
    ],
)
def test_assist_essay_returns_task_specific_result(monkeypatch, task, content, expected):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    def opener(_request, timeout):
        return FakeResponse(_deepseek_response(content))

    assert assist_essay(task, '正文', opener=opener)['result'] == expected


def test_assist_essay_requires_api_key(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)

    with pytest.raises(AIServiceError, match='DeepSeek API 密钥未配置'):
        assist_essay('summary', '正文')


@pytest.mark.parametrize('task', ['', 'translate', None, True])
def test_assist_essay_rejects_unknown_tasks(monkeypatch, task):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    with pytest.raises(ValueError, match='不支持的 AI 任务'):
        assist_essay(task, '正文')


@pytest.mark.parametrize(
    'content',
    ['', '  ', None, 123, True, '字' * 20001],
    ids=['empty', 'spaces', 'none', 'number', 'boolean', 'too-long'],
)
def test_assist_essay_rejects_invalid_content(monkeypatch, content):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    with pytest.raises(ValueError, match='正文'):
        assist_essay('summary', content)


@pytest.mark.parametrize(
    ('title', 'tags'),
    [
        (None, []),
        (123, []),
        ('标题', '技术'),
        ('标题', [True]),
        ('标题', ['技术', '']),
    ],
)
def test_assist_essay_rejects_invalid_context(monkeypatch, title, tags):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    with pytest.raises(ValueError):
        assist_essay('summary', '正文', title=title, existing_tags=tags)


@pytest.mark.parametrize(
    'upstream',
    [
        {},
        {'choices': []},
        {'choices': [{'message': {}}]},
        _deepseek_response(''),
        _deepseek_response('not json'),
        _deepseek_response('```json\n{"excerpt":"摘要"}\n```'),
    ],
)
def test_assist_essay_rejects_malformed_upstream_payload(monkeypatch, upstream):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    def opener(_request, timeout):
        return FakeResponse(upstream)

    with pytest.raises(AIServiceError, match='返回格式异常'):
        assist_essay('summary', '正文', opener=opener)


@pytest.mark.parametrize(
    ('task', 'content'),
    [
        ('summary', '{"excerpt":123}'),
        ('summary', '{"excerpt":"' + ('字' * 161) + '"}'),
        ('tags', '{"tags":"技术"}'),
        ('tags', '{"tags":["技术",""]}'),
        ('polish', '{"content":false}'),
        ('review', '{"issues":"无"}'),
        ('review', '{"issues":[{"type":"文字","message":"问题"}]}'),
        ('review', '{"issues":[{"type":"文字","message":"问题","suggestion":1}]}'),
    ],
)
def test_assist_essay_rejects_invalid_task_result(monkeypatch, task, content):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    def opener(_request, timeout):
        return FakeResponse(_deepseek_response(content))

    with pytest.raises(AIServiceError, match='返回格式异常'):
        assist_essay(task, '正文', opener=opener)


@pytest.mark.parametrize(
    'error',
    [
        URLError('offline'),
        TimeoutError(),
        OSError('network down'),
        HTTPError(
            'https://api.deepseek.com/chat/completions',
            401,
            'Unauthorized',
            {},
            BytesIO(b'{"error":"test-secret"}'),
        ),
    ],
)
def test_assist_essay_hides_upstream_failures(monkeypatch, error):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    def opener(_request, timeout):
        raise error

    with pytest.raises(AIServiceError, match='DeepSeek 暂时不可用') as caught:
        assist_essay('summary', '正文', opener=opener)

    assert 'test-secret' not in str(caught.value)


def test_assist_essay_normalizes_invalid_usage_counts(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')
    upstream = _deepseek_response('{"excerpt":"摘要"}')
    upstream['usage'] = {'prompt_tokens': '10', 'completion_tokens': True}

    def opener(_request, timeout):
        return FakeResponse(upstream)

    assert assist_essay('summary', '正文', opener=opener)['usage'] == {
        'prompt_tokens': 0,
        'completion_tokens': 0,
    }


@pytest.mark.parametrize(
    ('task', 'response_content', 'expects_samples'),
    [
        ('summary', '{"excerpt":"摘要"}', True),
        ('polish', '{"content":"润色"}', True),
        ('review', '{"issues":[]}', True),
        ('title', '{"titles":["一","二","三"]}', True),
        ('continue', '{"content":"续写"}', True),
        ('tags', '{"tags":["技术"]}', False),
    ],
)
def test_assist_essay_uses_style_samples_only_for_prose_tasks(
    monkeypatch, task, response_content, expects_samples,
):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')
    seen = {}

    def opener(request, timeout):
        seen['body'] = json.loads(request.data)
        return FakeResponse(_deepseek_response(response_content))

    assist_essay(
        task,
        '当前正文',
        style_samples=[{'title': '旧文', 'content': '旧文片段'}],
        opener=opener,
    )

    context = json.loads(seen['body']['messages'][1]['content'])
    assert ('style_samples' in context) is expects_samples
    system = seen['body']['messages'][0]['content']
    assert '不可信数据' in system
    assert '不得复用样本中的事实' in system


@pytest.mark.parametrize(
    'style_samples',
    [
        '旧文',
        [None],
        [{'title': '', 'content': '正文'}],
        [{'title': '旧文', 'content': 123}],
    ],
)
def test_assist_essay_rejects_invalid_style_samples(monkeypatch, style_samples):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    with pytest.raises(ValueError, match='文风样本'):
        assist_essay('summary', '正文', style_samples=style_samples)


@pytest.mark.parametrize(
    ('task', 'response_content'),
    [
        ('title', '{"titles":["一","二"]}'),
        ('title', '{"titles":["重复","重复","第三条"]}'),
        ('title', '{"titles":["' + ('长' * 41) + '","二","三"]}'),
        ('continue', '{"content":"' + ('续' * 4001) + '"}'),
        ('tags', '{"tags":["一","二","三","四","五","六","七"]}'),
        ('tags', '{"tags":["' + ('长' * 31) + '"]}'),
        (
            'review',
            '{"issues":[' + ','.join(
                '{"type":"文字","message":"问题","suggestion":"建议"}' for _ in range(13)
            ) + ']}',
        ),
        (
            'review',
            '{"issues":[{"type":"文字","message":"' + ('长' * 501) + '","suggestion":"建议"}]}',
        ),
        ('polish', '{"content":"' + ('长' * 4001) + '"}'),
    ],
)
def test_assist_essay_rejects_bounded_task_results(monkeypatch, task, response_content):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    def opener(_request, timeout):
        return FakeResponse(_deepseek_response(response_content))

    with pytest.raises(AIServiceError, match='返回格式异常'):
        assist_essay(task, '短正文', opener=opener)


def test_assist_essay_normalizes_and_deduplicates_tags(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    def opener(_request, timeout):
        return FakeResponse(_deepseek_response('{"tags":[" 技术 ","Python","技术"]}'))

    assert assist_essay('tags', '正文', opener=opener)['result'] == {
        'tags': ['技术', 'Python'],
    }


def test_polish_uses_mode_instruction_and_surrounding_context(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')
    seen = {}

    def opener(request, timeout):
        seen['body'] = json.loads(request.data)
        return FakeResponse(_deepseek_response(
            '{"content":"改写结果","changes":["收紧句子"]}'
        ))

    response = assist_essay(
        'polish',
        '待润色段落',
        polish_mode='rewrite',
        instruction='保留口语',
        surrounding_context={'before': '上一段', 'after': '下一段'},
        opener=opener,
    )

    assert response['result'] == {
        'content': '改写结果',
        'changes': ['收紧句子'],
    }
    system = seen['body']['messages'][0]['content']
    context = json.loads(seen['body']['messages'][1]['content'])
    assert '深度改写' in system
    assert '保留口语' in system
    assert '通用 AI 腔' in system
    assert context['surrounding_context'] == {'before': '上一段', 'after': '下一段'}


@pytest.mark.parametrize(
    ('kwargs', 'message'),
    [
        ({'polish_mode': 'wild'}, '润色强度'),
        ({'instruction': '字' * 301}, '润色要求'),
        ({'surrounding_context': {'before': '字' * 2501}}, '上下文'),
        ({'surrounding_context': {'unknown': '正文'}}, '上下文'),
    ],
)
def test_assist_essay_rejects_invalid_polish_options(monkeypatch, kwargs, message):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    with pytest.raises(ValueError, match=message):
        assist_essay('polish', '正文', **kwargs)


def test_assist_essay_bounds_polish_input_for_complete_output(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')

    with pytest.raises(ValueError, match='单次润色'):
        assist_essay('polish', '字' * 3001)


def test_assist_essay_uses_confirmed_style_profile_before_samples(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')
    seen = {}

    def opener(request, timeout):
        seen['body'] = json.loads(request.data)
        return FakeResponse(_deepseek_response('{"content":"润色"}'))

    assist_essay(
        'polish',
        '正文',
        style_profile='已确认：保留对照句',
        style_samples=[{'title': '旧文', 'content': '样本'}],
        opener=opener,
    )

    system = seen['body']['messages'][0]['content']
    context = json.loads(seen['body']['messages'][1]['content'])
    assert '已确认文风画像' in system
    assert context['confirmed_style_profile'] == '已确认：保留对照句'
    assert context['style_samples'][0]['title'] == '旧文'


def test_assist_essay_returns_generated_style_profile(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-secret')
    seen = {}

    def opener(request, timeout):
        seen['body'] = json.loads(request.data)
        return FakeResponse(_deepseek_response('{"profile":"## 语气\\n克制直接"}'))

    response = assist_essay(
        'style',
        '总结文风',
        style_samples=[{'title': '旧文', 'content': '样本正文'}],
        opener=opener,
    )

    assert response['result'] == {'profile': '## 语气\n克制直接'}
    system = seen['body']['messages'][0]['content']
    assert '不得预设作者' in system
    assert '保持作者克制' not in system
