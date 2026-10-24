"""Real pinned CDN regression: Card icon, avatar surface and authorized PDF."""
import json
import os
import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={"width":1440,"height":1100},color_scheme="light")
    page.set_default_timeout(10000)
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    def identity(route):
        response=route.fetch()
        route.fulfill(response=response,json={**response.json(),"avatar_url":"/__portrait.svg"})
    page.route("**/api/session/",identity)
    page.route("**/__portrait.svg",lambda route:route.fulfill(content_type="image/svg+xml",body='<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><circle cx="16" cy="16" r="6" fill="black"/></svg>'))
    page.goto(os.environ.get("CTM_REVIEW_URL","http://127.0.0.1:18860/"))
    page.get_by_role("heading",name="Home",exact=True).wait_for()
    avatar=page.locator(".plx-app-header__item--account .plx-avatar")
    avatar.locator("img").evaluate("e=>e.decode()")
    surface=avatar.evaluate("e=>{const s=getComputedStyle(e);return {background:s.backgroundColor,border:s.borderTopWidth,color:s.borderTopColor}}")
    assert surface['background']=="rgb(255, 255, 255)" and surface['border']=="1px",surface
    card=page.locator(".plx-card").filter(has_text="Council Session 2026-11-05")
    assert card.locator(".plx-icon--calendar").count()==1,"Session Card must use documented icon slot"
    page.get_by_role("button",name="Cases",exact=True).first.click()
    page.get_by_text("20261001-01",exact=True).first.click()
    page.get_by_role("button",name="Open case",exact=True).click()
    page.locator(".plx-secondary-pane").get_by_role("button",name="Documents",exact=True).click()
    page.get_by_role("grid").get_by_role("row").nth(1).click()
    reader=page.locator(".plx-reading-pane")
    reader.locator("canvas").first.wait_for(state="visible")
    reader.get_by_role("link",name="Open in browser",exact=True).wait_for()
    assert not errors,errors
    print(json.dumps({"avatar":surface,"card_icon":True,"pdf_rendered":True,"browser_errors":errors}))
    browser.close()
