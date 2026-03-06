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

def find_last_gap(df, type='up'):
    """偵測最近一次的跳空缺口 (up: 多頭跳空, down: 空頭跳空)"""
    if len(df) < 2: return None
    # 找最近 60 天內的缺口
    for i in range(len(df)-1, 0, -1):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        
        if type == 'up':
            # 多頭跳空缺口：今日最低價 > 昨日最高價
            if curr['Low'] > prev['High']:
                gap_top, gap_bottom = curr['Low'], prev['High']
                latest_price = df.iloc[-1]['Close']
                if latest_price >= gap_top: status = "✅ 站穩缺口（強勢）"
                elif latest_price > gap_bottom: status = "⚠️ 正在回補缺口中"
                else: status = "❌ 缺口已完全回補（轉弱）"
                return {'日期': df.index[i].strftime('%Y-%m-%d'), '上緣': f"{gap_top:.2f}", '下緣': f"{gap_bottom:.2f}", '狀態': status, '價位': gap_top}
        else:
            # 空頭(下跌)跳空缺口：今日最高價 < 昨日最低價
            if curr['High'] < prev['Low']:
                gap_top, gap_bottom = prev['Low'], curr['High']
                latest_price = df.iloc[-1]['Close']
                if latest_price >= gap_top: status = "🚀 已回補並站上缺口（強勢反轉）"
                elif latest_price > gap_bottom: status = "⚠️ 正在回補缺口中（嘗試止跌）"
                else: status = "❌ 尚未回補缺口（弱勢格局）"
                return {'日期': df.index[i].strftime('%Y-%m-%d'), '上緣': f"{gap_top:.2f}", '下緣': f"{gap_bottom:.2f}", '狀態': status, '價位': gap_top}
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
        
        # 原有條件
        cond1 = last['Volume'] >= (last['VMA5'] * 2)
        cond2 = (last['Close'] > last['MA5']) and (last['Close'] > last['MA10']) and (last['Close'] > last['MA20'])
        cond3 = (last['MA5'] > prev['MA5']) and (last['MA10'] > prev['MA10']) and (last['MA20'] > prev['MA20'])
        
        # 新增條件：站上或正在回補最近一次的下跌缺口
        down_gap = find_last_gap(df, type='down')
        cond4 = False
        gap_status = "無缺口"
        if down_gap:
            gap_status = down_gap['狀態']
            if "已回補" in gap_status or "正在回補" in gap_status:
                cond4 = True
        
        # 計算符合條件的數量 (現在總共有 4 個條件)
        conditions_met = sum([cond1, cond2, cond3, cond4])
        
        if conditions_met >= 2:
            results.append({
                '股票名稱': name,
                '今日收盤': f"{last['Close']:.2f}",
                '漲跌幅': f"{((last['Close']-prev['Close'])/prev['Close']*100):.2f}%",
                '符合條件': f"{conditions_met}/4",
                '項目': (['✅量增'] if cond1 else []) + (['✅價強'] if cond2 else []) + (['✅趨勢'] if cond3 else []) + (['✅缺口回補'] if cond4 else []),
                '下跌缺口狀態': gap_status
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
        up_gap = find_last_gap(data, type='up')
        down_gap = find_last_gap(data, type='down')
        
        col_gap1, col_gap2 = st.columns(2)
        with col_gap1:
            if up_gap:
                st.markdown(f"#### 🟢 最近一次上漲跳空 ({up_gap['日期']})")
                st.write(f"上緣: {up_gap['上緣']} / 下緣: {up_gap['下緣']}")
                st.write(f"狀態: {up_gap['狀態']}")
            else: st.info("💡 無上漲跳空缺口")
            
        with col_gap2:
            if down_gap:
                st.markdown(f"#### 🔴 最近一次下跌跳空 ({down_gap['日期']})")
                st.write(f"上緣: {down_gap['上緣']} / 下緣: {down_gap['下緣']}")
                st.write(f"狀態: {down_gap['狀態']}")
            else: st.info("💡 無下跌跳空缺口")
        
        st.markdown("### 📊 近期數據詳情")
        st.dataframe(data.tail(10).style.highlight_max(axis=0), use_container_width=True)

with tab2:
    st.markdown("### 🚀 強勢股選股條件 (符合任兩項即列出)")
    st.info("""
    1. **量增**：今日成交量 ≥ 5日均量的 2 倍。
    2. **價強**：股價站上 5日、10日、20日均線。
    3. **多頭趨勢**：5日、10日、20日均線均比昨日上揚。
    4. **缺口回補**：正在回補或已站上最近一次的「下跌跳空缺口」上緣。
    """)
    
    if st.button('開始全自動熱選掃描 (16 檔概念股)'):
        strong_stocks = scan_strong_stocks(ticker_categories)
        if strong_stocks:
            st.success(f"找到 {len(strong_stocks)} 檔符合任兩項條件的個股！")
            st.dataframe(pd.DataFrame(strong_stocks), use_container_width=True)
        else:
            st.warning("目前沒有個股符合至少兩項條件。")
