import streamlit as st
import yfinance as yf
import pandas as pd
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
        "美股": ["VRT", "VICR", "MPWR"]
    },
    "BBU/長時儲能": {
        "台股": ["6781.TW", "3211.TWO", "4931.TWO", "2327.TW"],
        "美股": ["EOSE", "VST", "CEG"]
    },
    "基建與連接器": {
        "台股": ["3665.TW", "2317.TW", "2382.TW", "6669.TW"],
        "美股": ["PWR", "NVT"]
    }
}

# --- 3. 數據抓取邏輯 ---
@st.cache_data(ttl=60)  # 即時數據快取1分鐘
def fetch_ticker_data_realtime(ticker):
    """獲取即時數據（最近5-15分鐘），如果開盤；否則使用最新收盤價"""
    try:
        stock = yf.Ticker(ticker)
        
        # 優化：先獲取價格數據，成功後再獲取公司名稱
        # 嘗試獲取即時數據（使用5分鐘間隔）
        try:
            hist_5m = stock.history(period="1d", interval="5m")
            if not hist_5m.empty and len(hist_5m) > 0:
                hist_5m = hist_5m.tail(15)  # 只取最後15個數據點
                if len(hist_5m) > 0:
                    current_price = float(hist_5m['Close'].iloc[-1])
                    previous_price = float(hist_5m['Close'].iloc[0]) if len(hist_5m) > 1 else current_price
                    # 延遲獲取公司名稱，只在成功時獲取
                    try:
                        info = stock.info
                        company_name = info.get('longName', info.get('shortName', ticker))
                    except:
                        company_name = ticker
                    return current_price, previous_price, company_name, hist_5m
        except Exception as e:
            # 靜默處理錯誤，繼續嘗試其他方法
            pass
        
        # 如果沒有即時數據，使用日線數據
        try:
            hist_5d = stock.history(period="5d", interval="1d")
            if not hist_5d.empty and len(hist_5d) > 0:
                current_price = float(hist_5d['Close'].iloc[-1])
                previous_price = float(hist_5d['Close'].iloc[-2]) if len(hist_5d) >= 2 else float(hist_5d['Close'].iloc[0])
                # 延遲獲取公司名稱
                try:
                    info = stock.info
                    company_name = info.get('longName', info.get('shortName', ticker))
                except:
                    company_name = ticker
                return current_price, previous_price, company_name, hist_5d
        except Exception as e:
            # 日線數據也失敗，返回 None
            pass
        
        return None, None, None, None
        
    except Exception as e:
        # 所有嘗試都失敗，靜默返回 None
        return None, None, None, None

@st.cache_data(ttl=300)  # 一日內數據快取5分鐘
def fetch_ticker_data_1day(ticker):
    """獲取一日內數據"""
    try:
        stock = yf.Ticker(ticker)
        
        # 優化：使用15分鐘間隔而不是1分鐘，大幅減少數據量
        try:
            # 使用15分鐘間隔，只取最後24個數據點（約6小時）
            hist = stock.history(period="1d", interval="15m")
            if not hist.empty and len(hist) > 0:
                hist = hist.tail(24)  # 只取最後24個數據點
                current_price = float(hist['Close'].iloc[-1])
                previous_price = float(hist['Close'].iloc[0]) if len(hist) > 1 else current_price
                # 延遲獲取公司名稱
                try:
                    info = stock.info
                    company_name = info.get('longName', info.get('shortName', ticker))
                except:
                    company_name = ticker
                return current_price, previous_price, company_name, hist
        except Exception as e:
            # 靜默處理錯誤，繼續嘗試其他方法
            pass
        
        # 如果沒有分鐘數據，使用日線數據
        try:
            hist = stock.history(period="2d", interval="1d")
            if not hist.empty and len(hist) > 0:
                current_price = float(hist['Close'].iloc[-1])
                previous_price = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else float(hist['Close'].iloc[0])
                
                # 延遲獲取公司名稱
                try:
                    info = stock.info
                    company_name = info.get('longName', info.get('shortName', ticker))
                except:
                    company_name = ticker
                
                return current_price, previous_price, company_name, hist
        except Exception as e:
            # 日線數據也失敗，返回 None
            pass
        
        return None, None, None, None
        
    except Exception as e:
        # 所有嘗試都失敗，靜默返回 None
        return None, None, None, None


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
    if 'tw_mode' not in st.session_state:
        st.session_state.tw_mode = None
    if 'tw_data' not in st.session_state:
        st.session_state.tw_data = {}
    
    # 模式選擇按鈕
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏱️ 即時", key="tw_realtime", use_container_width=True):
            st.session_state.tw_mode = "realtime"
            st.session_state.tw_data = {}
            st.rerun()
    with col2:
        if st.button("📅 一日內", key="tw_1day", use_container_width=True):
            st.session_state.tw_mode = "1day"
            st.session_state.tw_data = {}
            st.rerun()
    
    # 載入數據
    if st.session_state.tw_mode:
        with st.spinner(f"正在載入台股數據（{'即時' if st.session_state.tw_mode == 'realtime' else '一日內'}）..."):
            tw_tickers = get_tw_tickers()
            failed_tickers = []
            for ticker in tw_tickers:
                try:
                    if st.session_state.tw_mode == "realtime":
                        current, previous, name, hist = fetch_ticker_data_realtime(ticker)
                    else:
                        current, previous, name, hist = fetch_ticker_data_1day(ticker)
                    
                    if current is not None:
                        st.session_state.tw_data[ticker] = {
                            "current": current,
                            "previous": previous,
                            "name": name,
                            "history": hist
                        }
                    else:
                        failed_tickers.append(ticker)
                except Exception as e:
                    print(f"載入 {ticker} 時發生錯誤: {e}")
                    failed_tickers.append(ticker)
            
            # 如果有失敗的股票，顯示警告
            if failed_tickers:
                st.warning(f"以下股票無法載入數據：{', '.join(failed_tickers)}")
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
                cols[i].metric(
                    f"{t}\n{d.get('name', '')}", 
                    f"{d['current']:.2f}", 
                    f"{change:.2f}%"
                )
        
        st.divider()
        
        # 分類標籤
        cat_tabs = st.tabs(list(STOCKS.keys()))
        for i, (category, market_data) in enumerate(STOCKS.items()):
            with cat_tabs[i]:
                for t in market_data["台股"]:
                    if t in st.session_state.tw_data:
                        d = st.session_state.tw_data[t]
                        change = (d["current"] - d["previous"]) / d["previous"] * 100
                        
                        # 顯示股票資訊
                        col_info, col_change = st.columns([3, 1])
                        with col_info:
                            st.markdown(f"### {t} - {d.get('name', 'N/A')}")
                        with col_change:
                            st.metric("漲跌幅", f"{change:.2f}%", f"{change:.2f}%")
                        
                        # 顯示價格資訊
                        col_price1, col_price2, col_price3 = st.columns(3)
                        with col_price1:
                            st.metric("現價", f"{d['current']:.2f}")
                        with col_price2:
                            st.metric("前價", f"{d['previous']:.2f}")
                        with col_price3:
                            st.metric("變化", f"{change:.2f}%", f"{change:.2f}%")
                        
                        st.divider()

# --- 美股標籤 ---
with main_tab2:
    st.subheader("📊 美股數據")
    
    # 初始化 session_state
    if 'us_mode' not in st.session_state:
        st.session_state.us_mode = None
    if 'us_data' not in st.session_state:
        st.session_state.us_data = {}
    
    # 模式選擇按鈕
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏱️ 即時", key="us_realtime", use_container_width=True):
            st.session_state.us_mode = "realtime"
            st.session_state.us_data = {}
            st.rerun()
    with col2:
        if st.button("📅 一日內", key="us_1day", use_container_width=True):
            st.session_state.us_mode = "1day"
            st.session_state.us_data = {}
            st.rerun()
    
    # 載入數據
    if st.session_state.us_mode:
        with st.spinner(f"正在載入美股數據（{'即時' if st.session_state.us_mode == 'realtime' else '一日內'}）..."):
            us_tickers = get_us_tickers()
            failed_tickers = []
            for ticker in us_tickers:
                try:
                    if st.session_state.us_mode == "realtime":
                        current, previous, name, hist = fetch_ticker_data_realtime(ticker)
                    else:
                        current, previous, name, hist = fetch_ticker_data_1day(ticker)
                    
                    if current is not None:
                        st.session_state.us_data[ticker] = {
                            "current": current,
                            "previous": previous,
                            "name": name,
                            "history": hist
                        }
                    else:
                        failed_tickers.append(ticker)
                except Exception as e:
                    print(f"載入 {ticker} 時發生錯誤: {e}")
                    failed_tickers.append(ticker)
            
            # 如果有失敗的股票，顯示警告
            if failed_tickers:
                st.warning(f"以下股票無法載入數據：{', '.join(failed_tickers)}")
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
                cols[i].metric(
                    f"{t}\n{d.get('name', '')}", 
                    f"{d['current']:.2f}", 
                    f"{change:.2f}%"
                )
        
        st.divider()
        
        # 分類標籤
        cat_tabs = st.tabs(list(STOCKS.keys()))
        for i, (category, market_data) in enumerate(STOCKS.items()):
            with cat_tabs[i]:
                for t in market_data["美股"]:
                    if t in st.session_state.us_data:
                        d = st.session_state.us_data[t]
                        change = (d["current"] - d["previous"]) / d["previous"] * 100
                        
                        # 顯示股票資訊
                        col_info, col_change = st.columns([3, 1])
                        with col_info:
                            st.markdown(f"### {t} - {d.get('name', 'N/A')}")
                        with col_change:
                            st.metric("漲跌幅", f"{change:.2f}%", f"{change:.2f}%")
                        
                        # 顯示價格資訊
                        col_price1, col_price2, col_price3 = st.columns(3)
                        with col_price1:
                            st.metric("現價", f"{d['current']:.2f}")
                        with col_price2:
                            st.metric("前價", f"{d['previous']:.2f}")
                        with col_price3:
                            st.metric("變化", f"{change:.2f}%", f"{change:.2f}%")
                        
                        st.divider()

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
