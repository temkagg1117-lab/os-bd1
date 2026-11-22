#!/usr/bin/env python3
"""Capture *real* UI screenshot from a live mock backend (never fake kernel evidence)."""
import subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
server = subprocess.Popen([sys.executable, str(ROOT / 'ui/server.py'), '--mock', '--port', '8893'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
try:
    time.sleep(.5)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 940}, device_scale_factor=1)
        def live_backend(_source, path, method):
            url = 'http://127.0.0.1:8893' + str(path or '/')
            req = urllib.request.Request(url, data=b'' if method == 'POST' else None, method=method)
            try:
                with urllib.request.urlopen(req, timeout=8) as result:
                    return {'status': result.status, 'body': result.read().decode('utf-8', 'replace')}
            except urllib.error.HTTPError as ex:
                return {'status': ex.code, 'body': ex.read().decode('utf-8', 'replace')}
        page.expose_binding('__bd2_proxy', live_backend)
        page.evaluate("""window.fetch = (path, options) => window.__bd2_proxy(path, options?.method || 'GET').then(r => new Response(r.body, {status:r.status, headers: {'Content-Type':'application/json'}}));""")
        page.set_content((ROOT / 'ui/static/index.html').read_text(encoding='utf-8'), wait_until='load')
        page.click('#spawn')
        page.wait_for_timeout(1250)
        page.screenshot(path=str(ROOT / 'docs/evidence/real_mock_ui.png'), full_page=True)
        print('Mode:', page.locator('#mode').inner_text())
        print('Nodes:', page.locator('#nodes').inner_text())
        print('Queries:', page.locator('#queries').inner_text())
        print('Error:', page.locator('#err').inner_text())
        page.click('#clean')
        browser.close()
finally:
    server.terminate()
    server.communicate(timeout=7)
