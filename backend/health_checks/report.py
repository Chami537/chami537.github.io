"""Shared result and aggregation helpers for health checks."""


def check(check_id, label, status, message, details=None):
    return {
        'id': check_id,
        'label': label,
        'status': status,
        'severity': 'error' if status == 'error' else 'warning' if status == 'warning' else 'info',
        'message': message,
        'details': list(details or []),
    }


def problem_check(check_id, label, details, message, severity='error'):
    return check(check_id, label, 'warning' if severity == 'warning' else 'error', message, details)


def unavailable(check_id, label):
    return check(check_id, label, 'warning', '数据不可用，已跳过', [])


def aggregate(checks):
    counts = {
        'passed': sum(item['status'] == 'passed' for item in checks),
        'warnings': sum(item['status'] == 'warning' for item in checks),
        'errors': sum(item['status'] == 'error' for item in checks),
    }
    status = 'error' if counts['errors'] else 'warning' if counts['warnings'] else 'healthy'
    order = {'error': 0, 'warning': 1, 'passed': 2}
    return {'status': status, 'summary': counts, 'checks': sorted(checks, key=lambda item: order[item['status']])}
