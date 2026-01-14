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
        # 使用 progress=False 和較短的 period 來加快速度
        data = yf.download(ticker_list, period="1d", interval="1h", progress=False, group_by='ticker', threads=True)
        return data
    except Exception as e:
        print(f"數據抓取失敗: {e}")  # 使用 print 而不是 st.error（在緩存函數中）
        return None

def get_price_data(raw_data, ticker):
    """從 yfinance 返回的數據中提取指定股票的價格數據"""
    try:
        if raw_data is None or raw_data.empty:
            return None, None
            
        # 處理 MultiIndex 結構（多個股票）
        if isinstance(raw_data.columns, pd.MultiIndex):
            if ticker in raw_data.columns.levels[0]:
                close_data = raw_data[(ticker, 'Close')]
                if len(close_data) > 0:
                    current = float(close_data.iloc[-1])
                    previous = float(close_data.iloc[0])
                    return current, previous
        else:
            # 單個股票的情況
            if 'Close' in raw_data.columns:
                close_data = raw_data['Close']
                if len(close_data) > 0:
                    current = float(close_data.iloc[-1])
                    previous = float(close_data.iloc[0])
                    return current, previous
    except Exception as e:
        print(f"提取 {ticker} 價格時發生錯誤: {e}")
    return None, None

@st.cache_data(ttl=600)  # 新聞快取 10 分鐘
def get_news(query):
    try:
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        return feed.entries[:3] if feed.entries else []
    except Exception as e:
        print(f"新聞抓取失敗: {e}")
        return []

# --- 4. 網頁 UI 佈局 ---

# 整理所有代號
all_tickers = []
for cat in STOCKS.values():
    all_tickers.extend(cat["台股"] + cat["美股"])

# 添加載入指示器
with st.spinner("正在載入數據，請稍候..."):
    raw_data = fetch_data(all_tickers)

if raw_data is not None:
    # A. 頂部快訊指標卡
    st.subheader("📊 關鍵標的即時行情")
    # 挑選四個最具指標性的標的顯示在最上方
    key_metrics = ["1519.TW", "VRT", "6781.TW", "EOSE"]
    m_cols = st.columns(len(key_metrics))
    
    for i, t in enumerate(key_metrics):
        try:
            current_p, prev_p = get_price_data(raw_data, t)
            if current_p is not None and prev_p is not None:
                change_pct = (current_p - prev_p) / prev_p * 100
                m_cols[i].metric(label=t, value=f"{current_p:.2f}", delta=f"{change_pct:.2f}%")
        except Exception as e:
            print(f"處理 {t} 時發生錯誤: {e}")
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
                tw_rows = []
                for t in market_data["台股"]:
                    current, previous = get_price_data(raw_data, t)
                    if current is not None and previous is not None:
                        change_pct = (current - previous) / previous * 100
                        tw_rows.append({"代號": t, "現價": f"{current:.2f}", "漲跌幅": f"{change_pct:.2f}%"})
                    else:
                        tw_rows.append({"代號": t, "現價": "N/A", "漲跌幅": "N/A"})
                if tw_rows:
                    tw_df = pd.DataFrame(tw_rows)
                    st.table(tw_df)

            with col_r:
                st.write(f"### {category} - 美股追蹤")
                us_rows = []
                for t in market_data["美股"]:
                    current, previous = get_price_data(raw_data, t)
                    if current is not None and previous is not None:
                        change_pct = (current - previous) / previous * 100
                        us_rows.append({"代號": t, "現價": f"{current:.2f}", "漲跌幅": f"{change_pct:.2f}%"})
                    else:
                        us_rows.append({"代號": t, "現價": "N/A", "漲跌幅": "N/A"})
                if us_rows:
                    us_df = pd.DataFrame(us_rows)
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

