"""Static checks for password essays, Giscus, and CSP configuration."""

from .report import check, problem_check


def check_security(root, essays, has_password, slug_re):
    details = []
    template = root / 'templates' / 'essay.html'
    try:
        template_html = template.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        template_html = ''
        details.append('templates/essay.html: 文件无法读取')
    if any(token not in template_html for token in ('https://giscus.app', 'connect-src', 'frame-src')):
        details.append('templates/essay.html: Giscus CSP 配置不完整')
    if 'essay-gate' not in template_html or 'essay-giscus.js' not in template_html:
        details.append('templates/essay.html: 密码门或 Giscus 入口缺失')
    for essay in essays or []:
        slug = str(essay.get('slug', ''))
        if not slug_re.fullmatch(slug) or not has_password(slug):
            continue
        html_path = root / 'essays' / f'{slug}.html'
        if not html_path.is_file():
            continue
        try:
            html = html_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            details.append(f'essays/{slug}.html: 文件无法读取')
        else:
            if 'essay-gate' not in html:
                details.append(f'essays/{slug}.html: 密码门缺失')
            if 'https://giscus.app' not in html:
                details.append(f'essays/{slug}.html: Giscus 配置缺失')
    return problem_check(
        'security.comments', '密码随笔与评论安全', details,
        '密码门或 Giscus/CSP 存在问题' if details else '密码门与 Giscus/CSP 正常',
    ) if details else check('security.comments', '密码随笔与评论安全', 'passed', '密码门与 Giscus/CSP 正常')
