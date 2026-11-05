"""Anonymous login branding, responsive layout and provider handoff regression."""
import os
import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for width,height in [(390,844),(768,900),(1280,720),(1440,1000)]:
        page=browser.new_page(viewport={"width":width,"height":height})
        page.set_default_timeout(7000)
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.route("**/api/session/",lambda route:route.fulfill(status=401,json={"error":"unauthenticated"}))
        def boot(route):
            response=route.fetch()
            route.fulfill(response=response,body=re.sub(r'"providers":\s*\[\]','"providers":["microsoft","google","apple"]',response.text()))
        page.route(re.compile(r"^http://127\.0\.0\.1:18860/$"),boot)
        page.goto(os.environ.get("CTM_REVIEW_URL","http://127.0.0.1:18860/"))
        page.get_by_role("heading",name="Coptic Orthodox Church - Diocese of Los Angeles",exact=True).wait_for()
        page.get_by_text("Office of the Ecclesiastical Council for Family Affairs",exact=True).wait_for()
        # The sign-in card is the Auth page card (sign-in.md, #97 slice 4).
        card=page.locator(".plx-auth__card").filter(has=page.get_by_role("heading",name="Sign in",exact=True))
        assert card.count()==1
        for image in [card.get_by_role("img",name="CTM",exact=True),page.get_by_role("img",name="Diocese of Los Angeles seal",exact=True)]:
            assert image.evaluate("async e=>{await e.decode();return e.naturalWidth>0}")
        assert page.locator("header").get_by_role("img",name="Diocese of Los Angeles seal",exact=True).count()==1
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        assert not errors,errors
        page.wait_for_function("Array.from(document.images).every(e=>getComputedStyle(e).opacity===\"1\")")
        page.screenshot(path=f".tmp/login-branding-{width}x{height}.png",full_page=True)
        assert page.get_by_role("button",name="العربية",exact=True).count()==0
        assert page.get_by_text("Council members use their authorized Microsoft account.",exact=True).count()==0
        assert page.get_by_text("Access your application or council workspace securely.",exact=True).count()==0
        box=card.bounding_box()
        assert abs(box["x"]+box["width"]/2-width/2)<2
        # From Medium (600px) up the brand header floats over the Auth page, so the card is centered in the
        # viewport; on a phone the header is in the flow above the card (slice 4, app.js loginHeader).
        if width>=600:
            assert abs(box["y"]+box["height"]/2-height/2)<3, "Login card must be vertically centered in the viewport"
        logo=card.get_by_role("img",name="CTM",exact=True).bounding_box()
        assert abs(logo["x"]+logo["width"]/2-width/2)<2
        requests=[]
        def handoff(route):
            requests.append(route.request.method)
            route.fulfill(status=200,content_type="text/html",body="Provider handoff")
        page.route("**/accounts/microsoft/login/",handoff)
        card.get_by_role("button",name="Continue with Microsoft",exact=True).click()
        page.get_by_text("Provider handoff",exact=True).wait_for()
        assert requests==["POST"],requests
        page.close()
    browser.close()
print("PASS: login branding, images, three widths and unchanged POST provider handoff")
