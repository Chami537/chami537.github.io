#!/usr/bin/env python3
"""Chami 个人网站管理工具 — 微型 SSG + 无头 CMS"""

import sys

if __name__ == '__main__':
    import os
    from backend.app import app
    from backend.data import load_json, ESSAYS_DIR, MD_DIR, DATA_DIR, BASE_DIR

    if len(sys.argv) > 1:
        if sys.argv[1] == 'build':
            from backend.ssg import _sync_essay_html, _generate_feeds, _cache_bust_assets
            force = '--force' in sys.argv
            print("Building static site..." + (" (incremental)" if not force else " (full)"))

            essays = load_json('essays.json')
            essays_json = os.path.join(DATA_DIR, 'essays.json')
            essay_template = os.path.join(BASE_DIR, 'templates', 'essay.html')
            if not os.path.exists(essay_template):
                print("ERROR: templates/essay.html not found")
                sys.exit(1)
            template_mtime = os.path.getmtime(essay_template)

            rebuilt = 0
            skipped = 0
            for e in essays:
                slug = e['slug']
                html_path = os.path.join(ESSAYS_DIR, f'{slug}.html')
                md_path = os.path.join(MD_DIR, f'{slug}.md')

                if not force and os.path.exists(html_path):
                    html_mtime = os.path.getmtime(html_path)
                    md_mtime = os.path.getmtime(md_path) if os.path.exists(md_path) else 0
                    if html_mtime >= md_mtime and html_mtime >= os.path.getmtime(essays_json) and html_mtime >= template_mtime:
                        skipped += 1
                        continue

                _sync_essay_html(e)
                print(f"  ✓ essays/{slug}.html")
                rebuilt += 1

            feeds_need_rebuild = force or rebuilt > 0
            if feeds_need_rebuild:
                _generate_feeds()
                _cache_bust_assets()
            else:
                print("  (feeds unchanged — skipped)")

            # Pre-fetch GitHub stars (rate-limited, only on full or when work data changed)
            from backend.ssg import _fetch_stars
            _fetch_stars()

            print()
            print(f"Done: {rebuilt} rebuilt, {skipped} skipped — {len(essays)} essays + feeds + cache bust.")
        elif sys.argv[1] in ('process-images', 'sync-photos'):
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
            import process_images
            process_images.process_all_images()
        elif sys.argv[1] == 'set-gps':
            from backend.ssg import _set_gps
            if len(sys.argv) < 5:
                print("Usage: python manage.py set-gps <filename> <lat> <lng>")
            else:
                try:
                    _set_gps(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
                except ValueError:
                    print("ERROR: lat/lng must be numbers, e.g. 39.9042 116.4074")
                    sys.exit(1)
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
