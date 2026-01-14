import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser

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
        "美股": ["VRT", "VICR", "MPWR"]
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
@st.cache_data(ttl=300)
def fetch_ticker_data(ticker):
    """獲取單個股票的數據"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5d")
        if not hist.empty and 'regularMarketPrice' in info:
            current = info.get('regularMarketPrice', hist['Close'].iloc[-1])
            previous = float(hist['Close'].iloc[0])
            return current, previous
        elif not hist.empty:
            current = float(hist['Close'].iloc[-1])
            previous = float(hist['Close'].iloc[0])
            return current, previous
    except Exception as e:
        st.error(f"獲取 {ticker} 失敗: {str(e)}")
    return None, None

@st.cache_data(ttl=600)
def get_news(query):
    try:
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        return feed.entries[:3] if feed.entries else []
    except:
        return []

# --- 4. 收集代號 ---
def get_tw_tickers():
    tw_tickers = []
    for cat in STOCKS.values():
        tw_tickers.extend(cat["台股"])
    return tw_tickers

def get_us_tickers():
    us_tickers = []
    for cat in STOCKS.values():
        us_tickers.extend(cat["美股"])
    return us_tickers

# --- 5. 網頁 UI 佈局 ---
main_tab1, main_tab2 = st.tabs(["📈 台股", "📊 美股"])

# --- 台股標籤 ---
with main_tab1:
    st.subheader("📊 台股數據")
    
    # 初始化 session_state
    if 'tw_data_loaded' not in st.session_state:
        st.session_state.tw_data_loaded = False
    if 'tw_data' not in st.session_state:
        st.session_state.tw_data = {}
    
    # 載入按鈕和數據
    if st.button("🔄 載入台股數據", key="load_tw"):
        with st.spinner("正在載入台股數據，請稍候..."):
            st.session_state.tw_data = {}
            tw_tickers = get_tw_tickers()
            for ticker in tw_tickers:
                current, previous = fetch_ticker_data(ticker)
                if current is not None and previous is not None:
                    st.session_state.tw_data[ticker] = {"current": current, "previous": previous}
            st.session_state.tw_data_loaded = True
            st.rerun()
    
    # 顯示數據
    if st.session_state.tw_data:
        # 關鍵指標
        key_tw = ["1519.TW", "6781.TW", "2308.TW", "3665.TW"]
        cols = st.columns(len(key_tw))
        for i, t in enumerate(key_tw):
            if t in st.session_state.tw_data:
                d = st.session_state.tw_data[t]
                change = (d["current"] - d["previous"]) / d["previous"] * 100
                cols[i].metric(t, f"{d['current']:.2f}", f"{change:.2f}%")
        
        st.divider()
        
        # 分類標籤
        cat_tabs = st.tabs(list(STOCKS.keys()))
        for i, (category, market_data) in enumerate(STOCKS.items()):
            with cat_tabs[i]:
                rows = []
                for t in market_data["台股"]:
                    if t in st.session_state.tw_data:
                        d = st.session_state.tw_data[t]
                        change = (d["current"] - d["previous"]) / d["previous"] * 100
                        rows.append({"代號": t, "現價": f"{d['current']:.2f}", "漲跌幅": f"{change:.2f}%"})
                    else:
                        rows.append({"代號": t, "現價": "N/A", "漲跌幅": "N/A"})
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# --- 美股標籤 ---
with main_tab2:
    st.subheader("📊 美股數據")
    
    # 初始化 session_state
    if 'us_data_loaded' not in st.session_state:
        st.session_state.us_data_loaded = False
    if 'us_data' not in st.session_state:
        st.session_state.us_data = {}
    
    # 載入按鈕和數據
    if st.button("🔄 載入美股數據", key="load_us"):
        with st.spinner("正在載入美股數據，請稍候..."):
            st.session_state.us_data = {}
            us_tickers = get_us_tickers()
            for ticker in us_tickers:
                current, previous = fetch_ticker_data(ticker)
                if current is not None and previous is not None:
                    st.session_state.us_data[ticker] = {"current": current, "previous": previous}
            st.session_state.us_data_loaded = True
            st.rerun()
    
    # 顯示數據
    if st.session_state.us_data:
        # 關鍵指標
        key_us = ["VRT", "EOSE", "ETN", "VST"]
        cols = st.columns(len(key_us))
        for i, t in enumerate(key_us):
            if t in st.session_state.us_data:
                d = st.session_state.us_data[t]
                change = (d["current"] - d["previous"]) / d["previous"] * 100
                cols[i].metric(t, f"{d['current']:.2f}", f"{change:.2f}%")
        
        st.divider()
        
        # 分類標籤
        cat_tabs = st.tabs(list(STOCKS.keys()))
        for i, (category, market_data) in enumerate(STOCKS.items()):
            with cat_tabs[i]:
                rows = []
                for t in market_data["美股"]:
                    if t in st.session_state.us_data:
                        d = st.session_state.us_data[t]
                        change = (d["current"] - d["previous"]) / d["previous"] * 100
                        rows.append({"代號": t, "現價": f"{d['current']:.2f}", "漲跌幅": f"{change:.2f}%"})
                    else:
                        rows.append({"代號": t, "現價": "N/A", "漲跌幅": "N/A"})
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# --- 新聞區塊 ---
st.divider()
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
