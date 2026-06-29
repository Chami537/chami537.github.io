#!/usr/bin/env python3
"""Chami 个人网站管理工具 — 微型 SSG + 无头 CMS"""

import sys

if __name__ == '__main__':
    from backend.app import app
    from backend.data import load_json

    if len(sys.argv) > 1:
        if sys.argv[1] == 'build':
            from backend.ssg import _sync_essay_html, _generate_feeds, _cache_bust_index
            import os
            force = '--force' in sys.argv
            print("Building static site..." + (" (incremental)" if not force else " (full)"))

            essays = load_json('essays.json')
            essays_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'essays')
            md_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'md')
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
            essays_json = os.path.join(data_dir, 'essays.json')

            rebuilt = 0
            skipped = 0
            for e in essays:
                slug = e['slug']
                html_path = os.path.join(essays_dir, f'{slug}.html')
                md_path = os.path.join(md_dir, f'{slug}.md')

                if not force and os.path.exists(html_path):
                    html_mtime = os.path.getmtime(html_path)
                    md_mtime = os.path.getmtime(md_path) if os.path.exists(md_path) else 0
                    if html_mtime >= md_mtime and html_mtime >= os.path.getmtime(essays_json):
                        skipped += 1
                        continue

                _sync_essay_html(e)
                print(f"  ✓ essays/{slug}.html")
                rebuilt += 1

            feeds_need_rebuild = force or rebuilt > 0 or skipped < len(essays)
            if feeds_need_rebuild:
                archive_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'archive.html')
                _generate_feeds()
                _cache_bust_index()
            else:
                print("  (feeds unchanged — skipped)")

            # Pre-fetch GitHub stars (rate-limited, only on full or when work data changed)
            from backend.ssg import _fetch_stars
            _fetch_stars()

            print()
            print(f"Done: {rebuilt} rebuilt, {skipped} skipped — {len(essays)} essays + feeds + cache bust.")
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
