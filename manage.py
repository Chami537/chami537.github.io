#!/usr/bin/env python3
"""Chami 个人网站管理工具 — 微型 SSG + 无头 CMS"""

import sys

if __name__ == '__main__':
    from backend.app import app
    from backend.data import load_json

    if len(sys.argv) > 1:
        if sys.argv[1] == 'build':
            from backend.ssg import _sync_essay_html, _generate_feeds
            print("Building static site...")
            essays = load_json('essays.json')
            for e in essays:
                _sync_essay_html(e)
                print(f"  ✓ essays/{e['slug']}.html")
            _generate_feeds()
            print()
            print(f"Done: {len(essays)} essays + archive + map + RSS + sitemap generated.")
        elif sys.argv[1] in ('process-images', 'sync-photos'):
            import sys as _sys; _sys.path.insert(0, 'tools')
            import process_images
            process_images.process_all_images()
        elif sys.argv[1] == 'set-gps':
            from backend.ssg import _set_gps
            if len(sys.argv) < 5:
                print("Usage: python manage.py set-gps <filename> <lat> <lng>")
            else:
                _set_gps(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python manage.py [build|sync-photos|process-images|set-gps]")
    else:
        import webbrowser, threading
        print("  Admin  → http://127.0.0.1:5000")
        print("  网站预览 → http://127.0.0.1:5000/index.html")
        threading.Timer(0.5, lambda: (
            webbrowser.open('http://127.0.0.1:5000'),
            webbrowser.open('http://127.0.0.1:5000/index.html')
        )).start()
        app.run(host='127.0.0.1', port=5000, debug=False)
