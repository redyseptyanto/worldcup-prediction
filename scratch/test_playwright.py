import time
from playwright.sync_api import sync_playwright
import urllib.parse

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Login
    page.goto('http://127.0.0.1:8080')
    page.select_option('select[name="auth[driver]"]', 'pgsql')
    page.fill('input[name="auth[server]"]', 'postgres')
    page.fill('input[name="auth[username]"]', 'test_user')
    page.fill('input[name="auth[password]"]', 'test_password')
    page.fill('input[name="auth[db]"]', 'bank_sempurna')
    page.click('input[type="submit"]')

    page.wait_for_selector('text=SQL command')
    page.click('text=SQL command')
    page.wait_for_selector('textarea[name="query"]', state='attached')

    sql = "SELECT nama_customer, tanggal_lahir FROM customers;"
    
    with page.expect_navigation():
        page.evaluate(f'''
            var btn = document.querySelector('input[value="Execute"]');
            var form = btn.closest('form');
            var ta = document.querySelector('textarea[name="query"]');
            ta.value = `{sql}`;
            form.submit();
        ''')
        
    print("Executed 1. Checking content...")
    content = page.locator('#content').inner_text()
    print(content[:200])
    
    sql2 = "SELECT c.nama_customer, t.no_rekening FROM customers c JOIN master_data_tabungan t ON c.customer_id = t.customer_id;"
    with page.expect_navigation():
        page.evaluate(f'''
            var btn = document.querySelector('input[value="Execute"]');
            var form = btn.closest('form');
            var ta = document.querySelector('textarea[name="query"]');
            ta.value = `{sql2}`;
            form.submit();
        ''')
        
    print("Executed 2. Checking content...")
    content = page.locator('#content').inner_text()
    print(content[:200])

    browser.close()
