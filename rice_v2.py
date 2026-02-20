import streamlit as st
import requests
import unicodedata
import re
import time
from playwright.sync_api import sync_playwright

# --- 辻川家専用：激安お米レスキュー・完全体（Yahoo×楽天×メルカリ） ---

st.title("🍚お米レスキュー検索くん🍚")
st.write("Yahoo!ショッピング、楽天市場、そしてメルカリの農家直販を横断検索し、最強コスパのお米を抽出します！")

YAHOO_CLIENT_ID = "dmVyPTIwMjUwNyZpZD01dVQyc3d3a3RWJmhhc2g9WmpNNU4yRTVNams1TXpSalkyWXlPQQ"
RAKUTEN_APP_ID = "d12b361c-8f1d-4151-8aa7-9f62789ac135"
RAKUTEN_ACCESS_KEY = "pk_PWxxiLmRNkRSwyefkmECzgrN2yalhIQQGVhCnHpAoSj"

st.sidebar.header("🔍 検索条件")
weight = st.sidebar.selectbox("何キロのお米を探す？", [5, 10, 20, 30])
max_price = st.sidebar.number_input("予算の上限（円）", value=4000 if weight==5 else (8000 if weight==10 else 12000), step=500)

ng_words = [
    "くず", "シラタ", "未検査", "訳あり", "ブレンド", "複数原料", "欠け", 
    "鳥の餌", "エサ", "えさ", "砕米", "着色米", "飼料",
    "米粉", "お米の粉", "大麦", "丸麦", "もち麦", "トレハ", 
    "米びつ", "ストッカー", "ダンボール", "段ボール", "梱包", "米袋", "カート", "保存容器",
    "選択可能", "オプション", "選べる", "組み合わせ","ふるさと納税", "まで", "定期便", "／", "/",
    "1.5kg", "1kg", "2kg", "一升米", "一升餅", "お試し", "発芽米","玉ねぎ", "たまねぎ", 
    "みかん", "木炭", "炭", "たれ", "タレ", "米ぬか", "ぬか","ドッグフード","チキン","ブラックウッド"
]

if st.button("🔥 3大モールで最強コスパ米を検索！"):
    good_items = []
    all_weights = [5, 10, 20, 30] 
    
    # ＝＝＝ 🎯 1. Yahoo!ショッピングの探索 ＝＝＝
    with st.spinner("🟡 Yahoo!ショッピングを探索中..."):
        yahoo_url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
        yahoo_params = {
            "appid": YAHOO_CLIENT_ID,
            "query": f"お米 {weight}kg",
            "price_to": max_price,
            "in_stock": "true",
            "results": 50
        }
        res_y = requests.get(yahoo_url, params=yahoo_params)
        if res_y.status_code == 200:
            for item in res_y.json().get("hits", []):
                name = item["name"]
                price = item["price"]
                item_url = item["url"]
                
                norm_name = unicodedata.normalize('NFKC', name).lower()
                is_ng = False
                
                for ng in ng_words:
                    if ng in norm_name: is_ng = True
                
                weight_str, weight_kiro = f"{weight}kg", f"{weight}キロ"
                if (weight_str not in norm_name) and (weight_kiro not in norm_name): is_ng = True
                
                for w in all_weights:
                    if w > weight and ((f"{w}kg" in norm_name) or (f"{w}キロ" in norm_name)): is_ng = True
                            
                if not is_ng and int(price / weight) < 350: is_ng = True
                if not is_ng: good_items.append({"shop": "Yahoo!", "name": name, "price": price, "price_per_kg": int(price / weight), "url": item_url})

    # ＝＝＝ 🎯 2. 楽天市場の探索 ＝＝＝
    with st.spinner("🔴 楽天市場を探索中..."):
        rakuten_url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
        rakuten_params = {
            "applicationId": RAKUTEN_APP_ID, "accessKey": RAKUTEN_ACCESS_KEY,
            "keyword": f"米 {weight}kg", "maxPrice": max_price, "availability": 1, "hits": 30
        }
        headers = {"Origin": "https://ken-mama-movie.streamlit.app/", "Referer": "https://ken-mama-movie.streamlit.app/"}
        res_r = requests.get(rakuten_url, params=rakuten_params, headers=headers)
        
        if res_r.status_code == 200:
            for item in res_r.json().get("Items", []):
                item_info = item["Item"]
                name, price, item_url = item_info["itemName"], item_info["itemPrice"], item_info["itemUrl"]
                
                norm_name = unicodedata.normalize('NFKC', name).lower()
                is_ng = False
                
                for ng in ng_words:
                    if ng in norm_name: is_ng = True
                
                weight_str, weight_kiro = f"{weight}kg", f"{weight}キロ"
                if (weight_str not in norm_name) and (weight_kiro not in norm_name): is_ng = True
                
                for w in all_weights:
                    if w > weight and ((f"{w}kg" in norm_name) or (f"{w}キロ" in norm_name)): is_ng = True
                            
                if not is_ng and int(price / weight) < 350: is_ng = True
                if not is_ng: good_items.append({"shop": "楽天市場", "name": name, "price": price, "price_per_kg": int(price / weight), "url": item_url})
        else:
            st.error(f"🚨 楽天APIのエラー詳細: {res_r.text}")

    # ＝＝＝ 🎯 3. メルカリの探索（Playwright自動操縦） ＝＝＝
    with st.spinner("🟢 メルカリの奥底から新着激安米を引っこ抜いています...（約10〜15秒かかります）"):
        try:
            with sync_playwright() as p:
                # 🌟 アプリとして動かすため、headless=True（ブラウザを裏でコッソリ動かすモード）に変更！
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # URLに予算上限（&price_max）の魔法を追加して、最初から高すぎるお米を弾く！
                m_url = f"https://jp.mercari.com/search?keyword=米%20{weight}kg&status=on_sale&sort=created_time&order=desc&price_max={max_price}"
                page.goto(m_url)
                
                try:
                    page.wait_for_selector('a[href*="/item/"], a[href*="/shops/product/"]', timeout=15000)
                    time.sleep(2)
                    
                    for _ in range(3):
                        page.keyboard.press("End")
                        time.sleep(2)
                        
                    m_items = page.locator('a[href*="/item/"], a[href*="/shops/product/"]').all()
                    
                    for item in m_items:
                        href = str(item.get_attribute("href"))
                        item_url = href if href.startswith("http") else "https://jp.mercari.com" + href
                        text_info = item.inner_text().replace('\n', ' ')
                        
                        match = re.search(r'[¥￥]\s*([\d,]+)\s*(.*)', text_info)
                        if match:
                            price = int(match.group(1).replace(',', ''))
                            name = match.group(2)
                            
                            # 🛡️ メルカリのデータにも「最強の盾」を発動！
                            norm_name = unicodedata.normalize('NFKC', name).lower()
                            is_ng = False
                            
                            for ng in ng_words:
                                if ng in norm_name: is_ng = True
                            
                            weight_str, weight_kiro = f"{weight}kg", f"{weight}キロ"
                            if (weight_str not in norm_name) and (weight_kiro not in norm_name): is_ng = True
                            
                            for w in all_weights:
                                if w > weight and ((f"{w}kg" in norm_name) or (f"{w}キロ" in norm_name)): is_ng = True
                                        
                            if not is_ng and int(price / weight) < 350: is_ng = True
                            if not is_ng: good_items.append({"shop": "メルカリ", "name": name, "price": price, "price_per_kg": int(price / weight), "url": item_url})
                except Exception:
                    st.warning("メルカリの読み込みでタイムアウトしました。")
                finally:
                    browser.close()
        except Exception as e:
            st.error(f"メルカリ検索中にエラーが発生しました: {e}")

    # ＝＝＝ 🌟 4. 三大モールの結果を合体して並び替え ＝＝＝
    good_items = sorted(good_items, key=lambda x: x["price_per_kg"])
    
    if good_items:
        st.success(f"🎉 厳しい審査を通過した {len(good_items)} 件の精鋭お米を発見しました！")
        for item in good_items:
            # ショップごとにアイコンを変える
            if item["shop"] == "楽天市場": shop_mark = "🔴"
            elif item["shop"] == "Yahoo!": shop_mark = "🟡"
            else: shop_mark = "🟢"
            
            st.markdown(f"### {shop_mark} [{item['shop']}] [{item['name']}]({item['url']})")
            st.write(f"**価格: {item['price']}円** （1kgあたり約 **{item['price_per_kg']}円**）")
            st.markdown("---")
    else:
        st.warning("条件に合うお米が見つかりませんでした。")