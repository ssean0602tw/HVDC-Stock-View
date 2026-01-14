import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser
from datetime import datetime

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="台美 AI 電力鏈監控終端", layout="wide")
st.title("⚡ 台美 AI 電力與重電產業鏈監控 (2026 版)")
st.caption("自動追蹤：重電設備、800V 架構、BBU 儲能、電力工程")

# --- 2. 完整追蹤清單整合 ---
STOCKS = {
    "重電/變壓器": {
        "台股": ["1519.TW", "1503.TW", "2371.TW", "1514.TW"],
        "美股": ["ETN", "GEV", "HUBB"]
    },
    "AI 供電/800V": {
        "台股": ["2308.TW", "2301.TW", "2360.TW"],
        "美股": ["VRT", "VICR", "MPWR"] # MPWR 為 Monolithic Power
    },
    "BBU/長時儲能": {
        "台股": ["6781.TW", "3211.TW", "4931.TW", "2327.TW"],
        "美股": ["EOSE", "VST", "CEG"]
    },
    "基建與連接器": {
        "台股": ["3665.TW", "2317.TW", "2382.TW", "6669.TW"],
        "美股": ["PWR", "NVT"]
    }
}

# --- 3. 數據抓取邏輯 ---
@st.cache_data(ttl=300) # 每 5 分鐘快取一次，避免被 Yahoo 封鎖
def fetch_data(ticker_list):
    try:
        data = yf.download(ticker_list, period="2d", interval="15m")
        return data
    except Exception as e:
        st.error(f"數據抓取失敗: {e}")
        return None

def get_news(query):
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    return feed.entries[:3]

# --- 4. 網頁 UI 佈局 ---

# 整理所有代號
all_tickers = []
for cat in STOCKS.values():
    all_tickers.extend(cat["台股"] + cat["美股"])

raw_data = fetch_data(all_tickers)

if raw_data is not None:
    # A. 頂部快訊指標卡
    st.subheader("📊 關鍵標的即時行情")
    # 挑選四個最具指標性的標的顯示在最上方
    key_metrics = ["1519.TW", "VRT", "6781.TW", "EOSE"]
    m_cols = st.columns(len(key_metrics))
    
    for i, t in enumerate(key_metrics):
        try:
            current_p = raw_data['Close'][t].iloc[-1]
            prev_p = raw_data['Close'][t].iloc[0]
            change_pct = (current_p - prev_p) / prev_p * 100
            m_cols[i].metric(label=t, value=f"{current_p:.2f}", delta=f"{change_pct:.2f}%")
        except:
            continue

    st.divider()

    # B. 詳細分類表格與圖表
    tab1, tab2, tab3, tab4 = st.tabs(list(STOCKS.keys()))
    
    tabs = [tab1, tab2, tab3, tab4]
    for i, (category, market_data) in enumerate(STOCKS.items()):
        with tabs[i]:
            col_l, col_r = st.columns([1, 1])
            
            with col_l:
                st.write(f"### {category} - 台股追蹤")
                tw_df = pd.DataFrame({
                    "代號": market_data["台股"],
                    "現價": [f"{raw_data['Close'][t].iloc[-1]:.2f}" for t in market_data["台股"]],
                    "漲跌幅": [f"{(raw_data['Close'][t].iloc[-1]/raw_data['Close'][t].iloc[0]-1)*100:.2f}%" for t in market_data["台股"]]
                })
                st.table(tw_df)

            with col_r:
                st.write(f"### {category} - 美股追蹤")
                us_df = pd.DataFrame({
                    "代號": market_data["美股"],
                    "現價": [f"{raw_data['Close'][t].iloc[-1]:.2f}" for t in market_data["美股"]],
                    "漲跌幅": [f"{(raw_data['Close'][t].iloc[-1]/raw_data['Close'][t].iloc[0]-1)*100:.2f}%" for t in market_data["美股"]]
                })
                st.table(us_df)

    st.divider()

    # C. 全球電力鏈新聞 (依據熱點自動搜尋)
    st.subheader("📰 產業鏈即時情報")
    n_col1, n_col2, n_col3 = st.columns(3)
    
    with n_col1:
        st.info("💡 重電與電網更新")
        for item in get_news("變壓器 外銷 美國"):
            st.caption(f"[{item.title}]({item.link})")
            
    with n_col2:
        st.info("🔥 AI 資料中心供電")
        for item in get_news("NVIDIA 800V HVDC Vertiv"):
            st.caption(f"[{item.title}]({item.link})")

    with n_col3:
        st.info("🔋 儲能與 BBU 趨勢")
        for item in get_news("EOSE Energy AES-KY 順達"):
            st.caption(f"[{item.title}]({item.link})")

else:
    st.warning("請檢查網路連線或稍後再試，目前無法取得數據。")

