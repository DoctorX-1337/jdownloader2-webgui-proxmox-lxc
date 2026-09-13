"""Isolated Chrome smoke test when the in-app browser bridge is unavailable."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def main():
    output=ROOT/'artifacts'
    output.mkdir(exist_ok=True)
    password=(ROOT/'zugangspasswort wunsch.txt').read_text(encoding='utf-8-sig').strip()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        context=browser.new_context(viewport={'width':1536,'height':1024},device_scale_factor=1)
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(type(error).__name__))
        page.goto('http://192.0.2.20/',wait_until='networkidle')
        page.get_by_role('button',name='Anmelden',exact=True).wait_for()
        page.screenshot(path=str(output/'login-desktop.png'),full_page=True)
        assert page.locator('input[name=password]').get_attribute('type')=='password'
        page.locator('input[name=password]').fill(password)
        page.get_by_role('button',name='Anmelden',exact=True).click()
        page.get_by_role('heading',name='Alles im Blick.').wait_for(timeout=15000)
        page.wait_for_timeout(4000)
        page.screenshot(path=str(output/'dashboard-desktop.png'),full_page=True)
        assert page.locator('textarea#links').is_visible()
        page.get_by_role('button',name='Einstellungen',exact=True).click()
        page.locator('input[name=nas_target]').wait_for()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(output/'settings-desktop.png'),full_page=True)
        assert page.locator('input[name=nas_target]').input_value().startswith('\\\\')
        assert page.get_by_role('button',name='NAS-Ziel prüfen & übernehmen').is_enabled()
        assert page.locator('input[name=premium_password]').get_attribute('type')=='password'
        assert page.get_by_role('button',name='Account hinzufügen',exact=True).is_enabled()
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_timeout(500)
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(output/'settings-mobile.png'),full_page=True)
        page.get_by_role('button',name='Übersicht',exact=True).click()
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_timeout(500)
        page.screenshot(path=str(output/'dashboard-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        assert not errors
        print('Browserprüfung bestanden: Login, Dashboard, NAS-Einstellung und Smartphone ohne horizontales Überlaufen.')
        browser.close()

if __name__=='__main__':
    try:main()
    except Exception as error:
        # Browser call logs can contain fill values; never print exception text.
        print('Browserprüfung fehlgeschlagen:',type(error).__name__)
        sys.exit(1)
