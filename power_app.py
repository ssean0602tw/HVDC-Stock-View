import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
from datetime import datetime
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

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

# 股票代號對應公司名稱
COMPANY_NAMES = {
    # 台股 - 重電/變壓器
    "1519.TW": "華城",
    "1503.TW": "士電",
    "2371.TW": "大同",
    "1514.TW": "亞力",
    # 台股 - AI 供電/800V
    "2308.TW": "台達電",
    "2301.TW": "光寶科",
    "2360.TW": "致茂",
    # 台股 - BBU/長時儲能
    "6781.TW": "AES-KY",
    "3211.TWO": "順達",
    "4931.TWO": "新盛力",
    "2327.TW": "國巨",
    # 台股 - 基建與連接器
    "3665.TW": "貿聯-KY",
    "2317.TW": "鴻海",
    "2382.TW": "廣達",
    "6669.TW": "緯穎",
    # 美股 - 重電/變壓器
    "ETN": "Eaton Corporation",
    "GEV": "GE Vernova",
    "HUBB": "Hubbell Incorporated",
    # 美股 - AI 供電/800V
    "VRT": "Vertiv Holdings Co",
    "VICR": "Vicor Corporation",
    "MPWR": "Monolithic Power Systems",
    # 美股 - BBU/長時儲能
    "EOSE": "Eos Energy Enterprises",
    "VST": "Vistra Corp",
    "CEG": "Constellation Energy",
    # 美股 - 基建與連接器
    "PWR": "Quanta Services",
    "NVT": "nVent Electric"
}

# --- 3. 數據抓取邏輯 ---
@st.cache_data(ttl=300)  # 數據快取5分鐘
def fetch_ticker_data(ticker):
    """獲取股票數據（15分鐘內），如果沒有開盤則使用最新價格"""
    try:
        stock = yf.Ticker(ticker)
        
        # 嘗試獲取15分鐘間隔的數據（最近15分鐘）
        try:
            hist_15m = stock.history(period="1d", interval="15m")
            if not hist_15m.empty and len(hist_15m) > 0:
                # 只取最後1個數據點（最近15分鐘）
                hist_15m = hist_15m.tail(1)
                if len(hist_15m) > 0:
                    current_price = float(hist_15m['Close'].iloc[-1])
                    # 獲取前一個價格點用於計算漲跌幅
                    hist_full = stock.history(period="2d", interval="1d")
                    if not hist_full.empty and len(hist_full) >= 2:
                        previous_price = float(hist_full['Close'].iloc[-2])
                    elif not hist_full.empty:
                        previous_price = float(hist_full['Close'].iloc[0])
                    else:
                        previous_price = current_price
                    return current_price, previous_price, hist_15m
        except:
            pass
        
        # 如果沒有15分鐘數據（未開盤），使用最新日線數據
        try:
            hist_5d = stock.history(period="5d", interval="1d")
            if not hist_5d.empty and len(hist_5d) > 0:
                current_price = float(hist_5d['Close'].iloc[-1])
                previous_price = float(hist_5d['Close'].iloc[-2]) if len(hist_5d) >= 2 else float(hist_5d['Close'].iloc[0])
                return current_price, previous_price, hist_5d
        except:
            pass
        
        return None, None, None
        
    except:
        return None, None, None

@st.cache_data(ttl=300)
def fetch_multiple_tickers_batch(tickers):
    """批量獲取多個股票的數據（使用 yfinance 批量下載，15分鐘數據）"""
    results = {}
    
    try:
        # 使用 yfinance 的批量下載功能（內建並行處理，非常快）
        # 先嘗試獲取15分鐘間隔的數據
        data = yf.download(
            tickers, 
            period="1d", 
            interval="15m", 
            progress=False, 
            group_by='ticker', 
            threads=True,
            timeout=30
        )
        
        # 獲取日線數據用於計算前一個價格
        data_daily = yf.download(
            tickers,
            period="5d",
            interval="1d",
            progress=False,
            group_by='ticker',
            threads=True,
            timeout=30
        )
        
        # 處理批量下載的數據
        if isinstance(data.columns, pd.MultiIndex):
            # 多個股票的情況（MultiIndex）
            for ticker in tickers:
                try:
                    # 獲取15分鐘數據
                    if ticker in data.columns.levels[0]:
                        ticker_data = data[ticker]
                        if not ticker_data.empty and 'Close' in ticker_data.columns:
                            close_data = ticker_data['Close'].tail(1)
                            if len(close_data) > 0:
                                current_price = float(close_data.iloc[-1])
                                # 從日線數據獲取前一個價格
                                if isinstance(data_daily.columns, pd.MultiIndex) and ticker in data_daily.columns.levels[0]:
                                    daily_data = data_daily[ticker]
                                    if not daily_data.empty and 'Close' in daily_data.columns:
                                        if len(daily_data) >= 2:
                                            previous_price = float(daily_data['Close'].iloc[-2])
                                        else:
                                            previous_price = float(daily_data['Close'].iloc[0])
                                    else:
                                        previous_price = current_price
                                else:
                                    previous_price = current_price
                                
                                company_name = COMPANY_NAMES.get(ticker, ticker)
                                results[ticker] = {
                                    "current": current_price,
                                    "previous": previous_price,
                                    "name": company_name,
                                    "history": ticker_data.tail(1)
                                }
                                continue
                    
                    # 如果15分鐘數據沒有，使用日線數據
                    if ticker in data_daily.columns.levels[0]:
                        daily_data = data_daily[ticker]
                        if not daily_data.empty and 'Close' in daily_data.columns:
                            current_price = float(daily_data['Close'].iloc[-1])
                            previous_price = float(daily_data['Close'].iloc[-2]) if len(daily_data) >= 2 else float(daily_data['Close'].iloc[0])
                            company_name = COMPANY_NAMES.get(ticker, ticker)
                            results[ticker] = {
                                "current": current_price,
                                "previous": previous_price,
                                "name": company_name,
                                "history": daily_data.tail(1)
                            }
                except Exception as e:
                    # 如果這個股票處理失敗，稍後用逐個獲取補上
                    continue
        elif len(tickers) == 1:
            # 單個股票的情況
            ticker = tickers[0]
            if not data.empty and 'Close' in data.columns:
                close_data = data['Close'].tail(1)
                if len(close_data) > 0:
                    current_price = float(close_data.iloc[-1])
                    if not data_daily.empty and 'Close' in data_daily.columns:
                        if len(data_daily) >= 2:
                            previous_price = float(data_daily['Close'].iloc[-2])
                        else:
                            previous_price = float(data_daily['Close'].iloc[0])
                    else:
                        previous_price = current_price
                    company_name = COMPANY_NAMES.get(ticker, ticker)
                    results[ticker] = {
                        "current": current_price,
                        "previous": previous_price,
                        "name": company_name,
                        "history": data.tail(1)
                    }
        
        # 如果批量下載沒有獲取到所有股票，回退到逐個獲取
        missing_tickers = [t for t in tickers if t not in results]
        if missing_tickers:
            for ticker in missing_tickers:
                try:
                    current, previous, hist = fetch_ticker_data(ticker)
                    if current is not None:
                        company_name = COMPANY_NAMES.get(ticker, ticker)
                        results[ticker] = {
                            "current": current,
                            "previous": previous,
                            "name": company_name,
                            "history": hist
                        }
                except:
                    pass
    
    except Exception as e:
        # 如果批量下載完全失敗，回退到逐個獲取
        print(f"批量下載失敗，回退到逐個獲取: {str(e)[:100]}")
        for ticker in tickers:
            try:
                current, previous, hist = fetch_ticker_data(ticker)
                if current is not None:
                    company_name = COMPANY_NAMES.get(ticker, ticker)
                    results[ticker] = {
                        "current": current,
                        "previous": previous,
                        "name": company_name,
                        "history": hist
                    }
            except:
                pass
    
    return results


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
    if 'tw_data' not in st.session_state:
        st.session_state.tw_data = {}
    
    # 載入按鈕
    if st.button("🔄 載入台股數據", key="load_tw", use_container_width=True):
        with st.spinner("正在載入台股數據..."):
            tw_tickers = get_tw_tickers()
            results = fetch_multiple_tickers_batch(tw_tickers)
            st.session_state.tw_data = results
            
            # 檢查失敗的股票
            failed_tickers = [t for t in tw_tickers if t not in results]
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
    if 'us_data' not in st.session_state:
        st.session_state.us_data = {}
    
    # 載入按鈕
    if st.button("🔄 載入美股數據", key="load_us", use_container_width=True):
        with st.spinner("正在載入美股數據..."):
            us_tickers = get_us_tickers()
            results = fetch_multiple_tickers_batch(us_tickers)
            st.session_state.us_data = results
            
            # 檢查失敗的股票
            failed_tickers = [t for t in us_tickers if t not in results]
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
