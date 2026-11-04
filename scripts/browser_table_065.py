"""Real CDN rendering/interaction contract for CTM shared tables (fictional rows)."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE="https://design-system.lighthouseway.org/cdn/0.76.0/"
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={"width":1280,"height":900})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content('<html lang="en" data-plx-density="compact"><head></head><body><div id="root"></div></body></html>')
    page.add_style_tag(url=BASE+"fonts.css")
    page.add_style_tag(url=BASE+"plenix.css")
    for asset in ["vendor/react.production.min.js","vendor/react-dom.production.min.js","plenix.js"]:
        page.add_script_tag(url=BASE+asset)
    page.add_script_tag(path="static/ctm/shell-layout.js")
    page.evaluate("""() => {
      const h=React.createElement,P=Plenix;
      window.opened=null;
      const rows=[{id:'one',code:'CTM-2026-101',name:{name:'Alex Morgan',gender:'male'},count:0},
                  {id:'two',code:'CTM-2026-102',name:{name:'Emma Wilson',gender:'female'},count:2}];
      const columns=[{title:'Case',field:'code',kind:'data'}, {title:'Spouse',field:'name',type:'person'}, {title:'Count',field:'count',type:'number'}];
      ReactDOM.createRoot(document.getElementById('root')).render(h(P.Stack,{gap:'section'},
        h(CTMShell.Table,{label:'Reference facts',rows,columns}),
        h(CTMShell.Table,{label:'Case records',rows,columns,onSelect:id=>window.opened=id})));
    }""")
    page.get_by_text('Alex Morgan').first.wait_for()
    page.get_by_text('CTM-2026-102').last.click()
    assert page.evaluate('window.opened')=='two'
    first=page.get_by_text('CTM-2026-101').last.locator('xpath=ancestor::*[@role="row"]')
    first.focus()
    first.press('Enter')
    assert page.evaluate('window.opened')=='one'
    metrics=page.locator('.plx-data-pill').evaluate_all('(els)=>els.map(e=>({height:e.getBoundingClientRect().height,text:e.textContent}))')
    row_heights=page.locator('[role="row"]').filter(has=page.locator('[role="gridcell"]')).evaluate_all('(els)=>els.map(e=>e.getBoundingClientRect().height)')
    assert row_heights and all(abs(height-36)<=1 for height in row_heights),row_heights
    assert metrics and all(abs(x['height']-24)<1 for x in metrics),metrics
    assert page.get_by_text('0',exact=True).count()>=2
    for lang,width in [('en',1280),('ar',390)]:
        page.set_viewport_size({'width':width,'height':900})
        page.evaluate("lang=>{document.documentElement.lang=lang;document.documentElement.dir=lang==='ar'?'rtl':'ltr'}",lang)
        page.screenshot(path=f'.tmp/table-065-{lang}.png',full_page=True)
    assert not errors,errors
    print(json.dumps({'cdn':'0.76.0','row_open':True,'zero_preserved':True,'row_heights':sorted(set(row_heights)),'pill_heights':sorted(set(x['height'] for x in metrics)),'browser_errors':errors}))
    browser.close()
