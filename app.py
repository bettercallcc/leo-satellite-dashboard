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
    # 使用 auto_adjust=True 排除除權息產生的物理缺口，只看價格走勢缺口
    data = yf.download(ticker, period='6mo', auto_adjust=True)
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
        latest_price = df.iloc[-1]['Close']
        
        if type == 'up':
            if curr['Low'] > prev['High']:
                gap_top, gap_bottom = curr['Low'], prev['High']
                if latest_price >= gap_top: status = "✅ 站穩缺口"
                elif latest_price > gap_bottom: status = "⚠️ 正在回補中"
                else: status = "❌ 已回補跌破"
                return {'日期': df.index[i].strftime('%Y-%m-%d'), '上緣': f"{gap_top:.2f}", '下緣': f"{gap_bottom:.2f}", '狀態': status, '價位': gap_top}
        else:
            # 下跌缺口：昨日最低 > 今日最高
            if prev['Low'] > curr['High']:
                gap_top, gap_bottom = prev['Low'], curr['High']
                # 關鍵修正：站上缺口定義為 收盤價 >= 下跌前之最低價 (gap_top)
                if latest_price >= gap_top: status = "🚀 已站上缺口"
                elif latest_price > gap_bottom: status = "⚠️ 正在回補中"
                else: status = "❌ 尚未回補"
                return {'日期': df.index[i].strftime('%Y-%m-%d'), '上緣': f"{gap_top:.2f}", '下緣': f"{gap_bottom:.2f}", '狀態': status, '價位': gap_top}
    return None

def scan_stocks(categories, min_count):
    results = []
    all_tickers = []
    for cat in categories.values():
        for name, sym in cat.items():
            all_tickers.append((name, sym))
    
    progress_bar = st.progress(0)
    for i, (name, sym) in enumerate(all_tickers):
        df = load_data(sym)
        df = calculate_technical_indicators(df)
        if len(df) < 5: continue
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. 量增
        cond1 = last['Volume'] >= (last['VMA5'] * 2)
        # 2. 價強
        cond2 = (last['Close'] > last['MA5']) and (last['Close'] > last['MA10']) and (last['Close'] > last['MA20'])
        # 3. 趨勢向上
        cond3 = (last['MA5'] > prev['MA5']) and (last['MA10'] > prev['MA10']) and (last['MA20'] > prev['MA20'])
        # 4. 站上最近下跌缺口 (精確判斷)
        down_gap = find_last_gap(df, type='down')
        cond4 = False
        if down_gap and "已站上" in down_gap['狀態']:
            cond4 = True
        
        conditions_met = sum([cond1, cond2, cond3, cond4])
        
        if conditions_met >= min_count:
            # 決定顯示的狀態
            gap_info = down_gap['狀態'] if down_gap else "無缺口"
            results.append({
                '股票名稱': name,
                '收盤價': f"{last['Close']:.2f}",
                '符合數': f"{conditions_met}/4",
                '符合項目': (['量'] if cond1 else []) + (['價'] if cond2 else []) + (['線'] if cond3 else []) + (['缺'] if cond4 else []),
                '下跌缺口狀態': gap_info,
                '缺口日期': down_gap['日期'] if down_gap else "-"
            })
        progress_bar.progress((i + 1) / len(all_tickers))
    return results

# --- 主要導航 ---
tab1, tab2 = st.tabs(["📈 個股走勢分析", "🔍 多功能熱選掃描"])

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

        fig.update_layout(template='plotly_dark', xaxis_rangeslider_visible=False, height=500, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # 缺口分析顯示
        up_gap = find_last_gap(data, type='up')
        down_gap = find_last_gap(data, type='down')
        
        col_gap1, col_gap2 = st.columns(2)
        with col_gap1:
            if up_gap:
                st.markdown(f"#### 🟢 最近一次上漲跳空 ({up_gap['日期']})")
                st.write(f"區間: {up_gap['下緣']} ~ {up_gap['上緣']}")
                st.write(f"狀態: {up_gap['狀態']}")
            else: st.info("💡 60天內無上漲跳空")
            
        with col_gap2:
            if down_gap:
                st.markdown(f"#### 🔴 最近一次下跌跳空 ({down_gap['日期']})")
                st.write(f"區間: {down_gap['下緣']} ~ {down_gap['上緣']}")
                st.write(f"狀態: {down_gap['狀態']}")
            else: st.info("💡 60天內無下跌跳空")
        
        st.markdown("### 📊 近期數據詳情")
        st.dataframe(data.tail(10).style.highlight_max(axis=0), use_container_width=True)

with tab2:
    st.markdown("### 🚀 熱選條件篩選器")
    
    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        min_cond = st.radio("篩選要求：", ["符合全部 (4項)", "符合 3 項以上", "符合 2 項以上", "符合 1 項以上"], index=2)
        map_cond = {"符合全部 (4項)": 4, "符合 3 項以上": 3, "符合 2 項以上": 2, "符合 1 項以上": 1}
    
    with col_sel2:
        st.write("**當前 4 大指標說明：**")
        st.write("1. 💎 **量增**：五日均量 2 倍 | 2. 📈 **價強**：股價 > 5/10/20MA")
        st.write("3. 🔋 **趨勢**：5/10/20MA 向上 | 4. 🎯 **站上缺口**：股價 >= 最近一次下跌缺口上緣")

    if st.button('🎯 開始全自動掃描並選股'):
        res = scan_stocks(ticker_categories, map_cond[min_cond])
        if res:
            st.success(f"掃描完畢！共找到 {len(res)} 檔個股符合篩選要求。")
            st.dataframe(pd.DataFrame(res), use_container_width=True)
        else:
            st.warning("目前市場狀況下，沒有個股符合此組合條件。")
