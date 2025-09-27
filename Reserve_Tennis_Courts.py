from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
from time import sleep

def Reserve_Tennis_Court():
    with sync_playwright() as p:

        future_date = (datetime.now() + timedelta(days = 2)).strftime("%B %d, %Y")
        current_hour = datetime.now().hour

        first_name = "Matthew"
        last_name = "Bandos"
        email = "mbandos@terpmail.umd.edu"

        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.planyo.com/booking.php?calendar=36698&planyo_lang=EN&mode=reserve&prefill=true&one_date=May%2006%2C%202025&start_date=May%2006%2C%202025&start_time=15&resource_id=118770")

        main_frame = page.frames[0]

        input_box_date = main_frame.locator('.with-status-border.form-control').nth(0)
        input_box_date.wait_for(timeout=5000)
        input_box_date.fill(future_date)

        dropdown_for_time = main_frame.locator('.with-status-border.form-control').nth(1)
        dropdown_for_time.wait_for(timeout=5000)
        if(current_hour == 18):
            dropdown_for_time.select_option("18")
        if(current_hour == 17):
            dropdown_for_time.select_option("17")

        dropdown_for_court = main_frame.locator('.with-status-border.form-control').nth(2)
        dropdown_for_court.wait_for(timeout=5000)
        dropdown_for_court.select_option("Court 1")

        input_box_first_name = main_frame.locator('.with-status-border.form-control').nth(3)
        input_box_first_name.wait_for(timeout=5000)
        input_box_first_name.fill(first_name)

        input_box_last_name = main_frame.locator('.with-status-border.form-control').nth(4)
        input_box_last_name.wait_for(timeout=5000)
        input_box_last_name.fill(last_name)

        input_box_email = main_frame.locator('.with-status-border.form-control').nth(5)
        input_box_email.wait_for(timeout=5000)
        input_box_email.fill(email)

        reserve_button = main_frame.locator('.btn.btn-primary.btn-lg')
        reserve_button.wait_for(timeout=5000)
        reserve_button.click()

Reserve_Tennis_Court()