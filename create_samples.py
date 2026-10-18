"""Sample data only. The investigation engine does not import this module."""
import json
from pathlib import Path
from run_gate import build_fixture

ROOT = Path(__file__).resolve().parent


def create():
    # Keep original feasibility fixtures reproducible.
    for name, mode, seed in [('overwrite_alpha','overwrite',137),('safe_shared_merge','merge',813),('safe_separate_key','unrelated',455)]:
        build_fixture(name,mode,seed)
    target = ROOT/'examples'/'basket_settings'
    manifest = {'features':[
        {'id':'shopping-basket','module':'basket.js','seed':'#add-items','observe':'#basket li'},
        {'id':'appearance','module':'appearance.js','trigger':['#change-color','#save-settings']},
    ]}
    html = '''<!doctype html><meta charset="utf-8"><title>Corner Shop</title>
<style>body{font:18px system-ui;max-width:800px;margin:50px auto;background:#f5f5ef;color:#192521}section{padding:24px;background:white;margin:16px 0;border-radius:16px}button{padding:12px;border:0;background:#164d3c;color:white;border-radius:8px;margin-right:8px}</style>
<h1>Corner Shop</h1><p>A saved basket should survive an appearance change.</p>
<section><h2>Basket</h2><button id="add-items">Add bread and milk</button><ul id="basket"></ul></section>
<section><h2>Appearance</h2><button id="change-color">Preview blue</button><button id="save-settings">Save appearance</button><p id="status"></p></section>
<script src="/basket.js"></script><script src="/appearance.js"></script>'''
    basket = '''const basketStorage = 'corner-shop:workspace';
function showBasket() {
  const workspace = JSON.parse(localStorage.getItem(basketStorage) || '{}');
  document.querySelector('#basket').replaceChildren(...(workspace.basket || []).map(item => {
    const row = document.createElement('li'); row.textContent = item; return row;
  }));
}
document.querySelector('#add-items').onclick = () => {
  localStorage.setItem(basketStorage, JSON.stringify({basket:['Sourdough bread','Oat milk']}));
  showBasket();
};
showBasket();'''
    old = '''document.querySelector('#change-color').onclick = () => { document.body.style.background = '#e8f0ff'; };
document.querySelector('#save-settings').onclick = () => {
  localStorage.setItem('corner-shop:appearance', JSON.stringify({theme:'blue'}));
  document.querySelector('#status').textContent = 'Appearance saved';
};'''
    broken = old.replace('corner-shop:appearance','corner-shop:workspace')
    fixed = old.replace("localStorage.setItem('corner-shop:appearance', JSON.stringify({theme:'blue'}));", "const workspace = JSON.parse(localStorage.getItem('corner-shop:workspace') || '{}');\n  localStorage.setItem('corner-shop:workspace', JSON.stringify({...workspace,theme:'blue'}));")
    for name, new in [('basket_settings',broken),('basket_settings_fixed',fixed)]:
        folder = ROOT/'examples'/name
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        for version, appearance in [('old',old),('new',new)]:
            dest=folder/version
            dest.mkdir(exist_ok=True)
            for file,text in [('index.html',html),('basket.js',basket),('appearance.js',appearance)]:
                (dest/file).write_text(text,encoding='utf-8')
    return target


if __name__=='__main__':
    print(create())
