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
@st.cache_data(ttl=60)  # 即時數據快取1分鐘
def fetch_ticker_data_realtime(ticker):
    """獲取即時數據（如果開盤），否則使用最新收盤價"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 獲取公司名稱
        company_name = info.get('longName', info.get('shortName', ticker))
        
        # 嘗試獲取即時數據（1分鐘間隔）
        try:
            hist_1m = stock.history(period="1d", interval="1m")
            if not hist_1m.empty and len(hist_1m) > 0:
                # 有今日數據，使用最新價格
                current_price = float(hist_1m['Close'].iloc[-1])
                hist_data = hist_1m
                previous_price = float(hist_1m['Close'].iloc[0]) if len(hist_1m) > 1 else current_price
                return current_price, previous_price, company_name, hist_data
        except:
            pass
        
        # 如果沒有即時數據，使用日線數據
        hist_5d = stock.history(period="5d", interval="1d")
        if not hist_5d.empty:
            current_price = float(hist_5d['Close'].iloc[-1])
            hist_data = hist_5d
            previous_price = float(hist_5d['Close'].iloc[-2]) if len(hist_5d) >= 2 else float(hist_5d['Close'].iloc[0])
            return current_price, previous_price, company_name, hist_data
        
        return None, None, None, None
        
    except Exception as e:
        print(f"獲取 {ticker} 即時數據失敗: {e}")
        return None, None, None, None

@st.cache_data(ttl=300)  # 一日內數據快取5分鐘
def fetch_ticker_data_1day(ticker):
    """獲取一日內數據"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 獲取公司名稱
        company_name = info.get('longName', info.get('shortName', ticker))
        
        # 獲取1日內數據（每分鐘）
        try:
            hist = stock.history(period="1d", interval="1m")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                previous_price = float(hist['Close'].iloc[0]) if len(hist) > 1 else current_price
                return current_price, previous_price, company_name, hist
        except:
            pass
        
        # 如果沒有分鐘數據，使用日線數據
        hist = stock.history(period="2d", interval="1d")
        if hist.empty:
            return None, None, None, None
        
        current_price = float(hist['Close'].iloc[-1])
        previous_price = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else float(hist['Close'].iloc[0])
        
        return current_price, previous_price, company_name, hist
        
    except Exception as e:
        print(f"獲取 {ticker} 一日內數據失敗: {e}")
        return None, None, None, None

def create_candlestick_chart(hist_data, ticker, company_name):
    """創建K線圖"""
    try:
        if hist_data is None or hist_data.empty or len(hist_data) < 2:
            return None
        
        # 確保數據有足夠的列
        if 'Open' not in hist_data.columns or 'High' not in hist_data.columns or 'Low' not in hist_data.columns or 'Close' not in hist_data.columns:
            return None
        
        # 重置索引
        df = hist_data.reset_index()
        
        # 確定日期列名稱
        date_col = df.columns[0]
        
        fig = go.Figure(data=[go.Candlestick(
            x=df[date_col] if date_col in df.columns else df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=ticker
        )])
        
        fig.update_layout(
            title=f"{ticker} - {company_name} K線圖",
            xaxis_title="時間",
            yaxis_title="價格",
            xaxis_rangeslider_visible=False,
            height=400,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        return fig
    except Exception as e:
        print(f"創建K線圖失敗 {ticker}: {e}")
        return None

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
            for ticker in tw_tickers:
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
                        
                        # 顯示K線圖
                        if d.get('history') is not None:
                            fig = create_candlestick_chart(d['history'], t, d.get('name', ''))
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                        
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
            for ticker in us_tickers:
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
                        
                        # 顯示K線圖
                        if d.get('history') is not None:
                            fig = create_candlestick_chart(d['history'], t, d.get('name', ''))
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                        
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
