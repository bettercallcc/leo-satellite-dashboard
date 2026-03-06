import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 設定網頁標題
st.set_page_config(page_title='🛰️ 低軌衛星概念股追蹤儀表板', layout='wide')
st.title('🛰️ 低軌衛星概念股追蹤儀表板')

# 定義低軌衛星概念股清單 (依產業分類)
ticker_categories = {
    'PCB/基板': {
        '華通 (2313)': '2313.TW',
        '燿華 (2367)': '2367.TW',
        '台光電 (2383)': '2383.TW',
        '騰輝電子 (4967)': '4967.TW'
    },
    '高頻/通訊元件': {
        '昇達科 (3491)': '3491.TWO',
        '穩懋 (3105)': '3105.TWO',
        '全訊 (5222)': '5222.TW',
        '泰藝 (3429)': '3429.TWO',
        '宏觀 (6568)': '6568.TWO'
    },
    '地面設備/網通': {
        '啟碁 (6285)': '6285.TW',
        '建漢 (3062)': '3062.TW',
        '台揚 (2314)': '2314.TW',
        '仲琦 (2419)': '2419.TW'
    },
    '組裝/系統/其他': {
        '鴻海 (2317)': '2317.TW',
        '金寶 (2312)': '2312.TW',
        '同欣電 (6271)': '6271.TW',
        '亞光 (3019)': '3019.TW',
        '瀚荃 (8103)': '8103.TW',
        '公準 (3178)': '3178.TWO'
    }
}

# 讓使用者在側邊欄選擇產業與個股
st.sidebar.header('🔍 篩選條件')
selected_category = st.sidebar.selectbox('請選擇產業類別：', list(ticker_categories.keys()))
selected_stock = st.sidebar.selectbox('請選擇個股：', list(ticker_categories[selected_category].keys()))
ticker_symbol = ticker_categories[selected_category][selected_stock]

st.subheader(f'正在分析：{selected_stock}')

# --- 資料處理函數 ---
@st.cache_data
def load_data(ticker):
    data = yf.download(ticker, period='6mo')
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

def calculate_technical_indicators(df):
    if df.empty: return df
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['VMA5'] = df['Volume'].rolling(window=5).mean()
    return df

def find_last_gap(df):
    """偵測最近一次的跳空缺口 (多頭)"""
    if len(df) < 2: return None
    # 找最近 60 天內的缺口
    for i in range(len(df)-1, 0, -1):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 多頭跳空缺口：今日最低價 > 昨日最高價
        if curr['Low'] > prev['High']:
            gap_top = curr['Low']
            gap_bottom = prev['High']
            
            # 判斷目前狀態 (以最新收盤價判定)
            latest_price = df.iloc[-1]['Close']
            status = ""
            if latest_price >= gap_top:
                status = "✅ 站上缺口（強勢）"
            elif latest_price > gap_bottom:
                status = "⚠️ 正在回補缺口中"
            else:
                status = "❌ 缺口已完全回補（弱勢）"
                
            return {
                '日期': df.index[i].strftime('%Y-%m-%d'),
                '缺口上緣': f"{gap_top:.2f}",
                '缺口下緣': f"{gap_bottom:.2f}",
                '目前狀態': status
            }
    return None

def scan_strong_stocks(categories):
    results = []
    all_tickers = []
    for cat in categories.values():
        for name, sym in cat.items():
            all_tickers.append((name, sym))
    
    progress_bar = st.progress(0)
    for i, (name, sym) in enumerate(all_tickers):
        df = load_data(sym)
        df = calculate_technical_indicators(df)
        if len(df) < 21: continue
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 條件 1: 成交量為五日均量的兩倍
        cond1 = last['Volume'] >= (last['VMA5'] * 2)
        
        # 條件 2: 成交價高於五日、十日、二十日均線
        cond2 = (last['Close'] > last['MA5']) and (last['Close'] > last['MA10']) and (last['Close'] > last['MA20'])
        
        # 條件 3: 五日、十日、二十日均線趨勢均向上 (今日均線 > 昨日均線)
        cond3 = (last['MA5'] > prev['MA5']) and (last['MA10'] > prev['MA10']) and (last['MA20'] > prev['MA20'])
        
        # 計算符合條件的數量
        conditions_met = sum([cond1, cond2, cond3])
        
        if conditions_met >= 2:
            results.append({
                '股票名稱': name,
                '今日收盤': f"{last['Close']:.2f}",
                '漲跌幅': f"{((last['Close']-prev['Close'])/prev['Close']*100):.2f}%",
                '符合條件數': f"{conditions_met}/3",
                '符合項目': (['✅量增'] if cond1 else []) + (['✅價強'] if cond2 else []) + (['✅多頭趨勢'] if cond3 else [])
            })
        progress_bar.progress((i + 1) / len(all_tickers))
    return results

# --- 主要導航 ---
tab1, tab2 = st.tabs(["📈 個股走勢分析", "🔍 強勢股熱選掃描"])

with tab1:
    st.subheader(f'正在分析：{selected_stock}')
    data = load_data(ticker_symbol)
    data = calculate_technical_indicators(data)

    if data.empty:
        st.error(f"無法取得 {selected_stock} 的數據。")
    else:
        # 指標顯示
        col1, col2, col3, col4 = st.columns(4)
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        change = latest['Close'] - prev['Close']
        pct = (change / prev['Close']) * 100
        
        col1.metric("最新收盤", f"{latest['Close']:.2f}", f"{change:.2f} ({pct:.2f}%)")
        col2.metric("5日均線 (MA5)", f"{latest['MA5']:.2f}")
        col3.metric("10日均線 (MA10)", f"{latest['MA10']:.2f}")
        col4.metric("20日均線 (MA20)", f"{latest['MA20']:.2f}")

        # K 線圖
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], name='MA5', line=dict(color='yellow', width=1)))
        fig.add_trace(go.Scatter(x=data.index, y=data['MA10'], name='MA10', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], name='MA20', line=dict(color='magenta', width=1)))

        fig.update_layout(template='plotly_dark', xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)

        # 新增：跳空缺口分析顯示
        gap_info = find_last_gap(data)
        if gap_info:
            st.markdown(f"#### 🔍 最近一次跳空缺口分析 ({gap_info['日期']})")
            gcol1, gcol2, gcol3 = st.columns(3)
            gcol1.write(f"**缺口上緣：** {gap_info['缺口上緣']}")
            gcol2.write(f"**缺口下緣：** {gap_info['缺口下緣']}")
            gcol3.write(f"**目前狀態：** {gap_info['目前狀態']}")
        else:
            st.info("💡 最近 60 天內未偵測到明顯的多頭跳空缺口。")
        
        st.markdown("### 📊 近期數據詳情")
        st.dataframe(data.tail(10).style.highlight_max(axis=0), use_container_width=True)

with tab2:
    st.markdown("### 🚀 強勢股選股條件 (符合任兩項即列出)")
    st.info("""
    1. **量增**：今日成交量 ≥ 5日均量的 2 倍。
    2. **價強**：股價站上 5日、10日、20日均線。
    3. **多頭趨勢**：5日、10日、20日均線皆比昨日上揚。
    """)
    
    if st.button('開始全自動熱選掃描 (16 檔概念股)'):
        strong_stocks = scan_strong_stocks(ticker_categories)
        if strong_stocks:
            st.success(f"找到 {len(strong_stocks)} 檔符合任兩項條件的個股！")
            st.dataframe(pd.DataFrame(strong_stocks), use_container_width=True)
        else:
            st.warning("目前沒有個股符合至少兩項條件。")
