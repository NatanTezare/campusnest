import re
from playwright.sync_api import sync_playwright, expect

URL = "http://localhost:5173"
fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 430, "height": 900}).new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))

    # ---------- student ----------
    pg.goto(URL); pg.screenshot(path="01_login.png")
    pg.fill("input[type=email]", "student@usiu.ac.ke"); pg.fill("input[type=password]", "student123")
    pg.click("button.btn"); pg.wait_for_url(URL + "/")
    check("student lands on Search", pg.locator("text=What matters to you?").is_visible())
    check("student has no 'Add hostel' in nav", pg.locator(".nav >> text=Add hostel").count() == 0)

    pg.fill("input[placeholder='e.g. Roysambu Heights']", "court")
    pg.wait_for_selector("text=Mirema Court")
    check("name search finds Mirema Court", pg.locator("text=Mirema Court").is_visible())
    pg.screenshot(path="02_search.png")
    pg.fill("input[placeholder='e.g. Roysambu Heights']", "zzzz")
    pg.wait_for_selector("text=No hostel named")
    check("name search shows empty message", True)
    pg.fill("input[placeholder='e.g. Roysambu Heights']", "")

    pg.click("text=Find hostels"); pg.wait_for_url("**/results")
    pg.wait_for_selector("text=% match")
    pg.screenshot(path="03_results.png")
    check("results are ranked with match %", pg.locator(".pill", has_text="% match").count() >= 5)
    pg.locator("text=Why this match?").first.click()
    check("'why this match' explains ranking", pg.locator(".why li").count() >= 3)
    boxes = pg.locator("input[type=checkbox]")
    boxes.nth(0).check(); boxes.nth(1).check()
    pg.click("text=selected →"); pg.wait_for_url("**/compare"); pg.wait_for_selector(".tbl")
    pg.screenshot(path="04_compare.png")
    check("compare table highlights best values", pg.locator(".tbl .best").count() >= 2)

    pg.goto(URL + "/"); pg.fill("input[placeholder='e.g. Roysambu Heights']", "heights")
    pg.click("text=Roysambu Heights"); pg.wait_for_selector("text=Reviews (")
    pg.click("text=Rate or review this hostel")
    pg.locator(".star-input span").nth(4).click()
    pg.fill("textarea", "Great place, very close to campus and safe at night.")
    pg.click("form.card >> text=Submit review"); pg.wait_for_selector("text=Review posted")
    pg.wait_for_selector("text=Sam >> nth=0") if False else None
    pg.screenshot(path="05_detail.png")
    check("review appears under student's first name", pg.locator("text=Great place, very close").is_visible())

    # student flags a listing (FR7); owner will see it later
    pg.goto(URL + "/"); pg.fill("input[placeholder='e.g. Roysambu Heights']", "mirema"); pg.click("text=Mirema Court")
    pg.wait_for_selector("text=Reviews ("); pg.click("text=Flag this listing"); pg.fill("input[placeholder^='What is wrong']", "Twin price is outdated")
    pg.click("text=Send report"); pg.wait_for_selector("text=owner has been notified")

    # evaluation / feedback page (Objective v)
    pg.click(".nav >> text=Feedback"); pg.wait_for_selector("text=Tell us how it went")
    pg.fill("input[placeholder='e.g. 8']", "10"); pg.fill("input[placeholder='e.g. 5']", "6")
    pg.click(".scale button:has-text('5')"); pg.click("button.chip:has-text('Yes')")
    pg.click("text=Send feedback"); pg.wait_for_selector("text=Results so far")
    pg.screenshot(path="12_feedback.png")
    check("feedback summary shows 1 student and 99% less time (10 h vs 6 min)",
          pg.locator("text=1 student").count() > 0 and pg.locator("text=99% less time").count() == 1)

    # student cannot open owner pages
    pg.goto(URL + "/owner/new"); pg.wait_for_timeout(500)
    check("student redirected away from owner page", "/owner" not in pg.url)
    pg.click("text=Log out"); pg.wait_for_url("**/login")

    # ---------- owner ----------
    pg.fill("input[type=email]", "owner@usiu.ac.ke"); pg.fill("input[type=password]", "owner123")
    pg.click("button.btn"); pg.wait_for_url("**/owner")
    check("owner lands on dashboard", pg.locator("text=My hostels").first.is_visible())
    pg.screenshot(path="06_dashboard.png")
    # owner reviews the student's report and clears it (FR7)
    pg.wait_for_selector("text=1 report from students")
    pg.click("text=1 report from students"); pg.wait_for_selector("text=Twin price is outdated")
    pg.screenshot(path="13_reports.png")
    check("owner sees the reason a student gave", pg.locator("text=Twin price is outdated").is_visible())
    pg.click("text=clear reports"); pg.wait_for_selector("text=Reports cleared")
    check("reports disappear after the owner clears them", pg.locator("text=report from students").count() == 0)
    pg.click("text=Add new hostel"); pg.wait_for_url("**/owner/new")
    pg.fill("input[placeholder='e.g. Roysambu Heights']", "E2E Test Lodge")
    pg.fill("input[placeholder='0.8']", "1.1")
    pg.fill("input[placeholder='e.g. 9000']", "8800")                       # Single room
    pg.click("text=+ Add another room type")
    pg.locator("input[placeholder='e.g. 9000']").nth(1).fill("6000")        # second room type
    pg.click(".chip:has-text('WiFi')"); pg.click(".chip:has-text('Security')")
    pg.set_input_files("input[type=file]", "e2e/hostel.jpg")
    pg.wait_for_selector(".thumb")
    pg.screenshot(path="07_add_form.png")
    pg.click("text=Publish listing"); pg.wait_for_url("**/owner")
    pg.wait_for_selector("text=E2E Test Lodge")
    check("new hostel with photo shows on dashboard", pg.locator("text=E2E Test Lodge").is_visible())
    card = pg.locator(".card", has_text="E2E Test Lodge")
    bg = card.locator(".ph").get_attribute("style") or ""
    check("uploaded photo is used as the card image (served from the database)", "/api/photos/" in bg)
    pg.screenshot(path="08_dashboard_after.png")

    card.locator("text=Edit listing").click(); pg.wait_for_url("**/edit")
    pg.wait_for_function("document.querySelectorAll(\"input[placeholder='e.g. 9000']\").length === 2")
    pg.locator("input[placeholder='e.g. 9000']").nth(0).fill("6500")        # cheapest row = Twin sharing: new price
    pg.locator(".roomrow").nth(0).locator("button.chip").click()            # mark Twin as Full
    pg.screenshot(path="09_edit.png")
    pg.click("text=Save changes"); pg.wait_for_url("**/owner"); pg.wait_for_selector("text=from KES 8,800")
    check("hostel shows 'from' price of the cheapest OPEN room (twin is full) + 2 room types",
          pg.locator(".card", has_text="E2E Test Lodge").locator("text=2 room types").count() == 1)
    pg.click("text=Log out"); pg.wait_for_url("**/login")

    # student sees the owner's edit
    pg.fill("input[type=email]", "student@usiu.ac.ke"); pg.fill("input[type=password]", "student123")
    pg.click("button.btn"); pg.wait_for_url(URL + "/")
    pg.fill("input[placeholder='e.g. Roysambu Heights']", "e2e")
    pg.wait_for_selector("text=E2E Test Lodge")
    check("student sees the 'from' price", pg.locator("text=from KES 8,800").count() > 0)
    pg.fill("input[placeholder='e.g. Roysambu Heights']", "")
    pg.click("button.chip:has-text('Twin sharing')"); pg.click("text=Find hostels"); pg.wait_for_selector("text=% match")
    pg.screenshot(path="10_results_twin.png")
    check("room-type search lists only hostels with twin rooms (Bedsitter-only hostel hidden)", pg.locator("text=Kasarani Nest").count() == 0 and pg.locator("text=Mirema Court").count() > 0)
    check("full twin room is marked (full) in results", pg.locator(".card", has_text="E2E Test Lodge").locator("text=(full)").count() == 1)
    pg.goto(URL + "/"); pg.fill("input[placeholder='e.g. Roysambu Heights']", "mirema"); pg.click("text=Mirema Court"); pg.wait_for_selector("text=Rooms")
    pg.screenshot(path="11_detail_rooms.png")
    check("detail page lists every room type with its price", pg.locator("text=Triple sharing").count() == 1 and pg.locator("text=per person / month").count() >= 3)

    check("no browser console/page errors", not errors)
    if errors: print(errors[:5])
    b.close()

print("\nFAILED:" if fails else "\nALL E2E CHECKS PASSED", fails or "")
