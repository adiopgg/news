import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
import time

# ==========================================
# 🔑 API CONFIG
# ==========================================
MY_API_KEY = "akr4lUAIsmZqm0lTH60LPdGhCbnxeICg"
# ==========================================

st.set_page_config(page_title="Global Macro: Nifty Impact", layout="wide")

# --- 1. UI STYLING ---
st.markdown("""
    <style>
    .main { background: #ffffff; color: #333; }
    .ff-header-text { color: #000000 !important; font-weight: bold !important; font-size: 14px; }
    .ff-row { border-bottom: 1px solid #e0e0e0; padding: 12px 0; display: flex; align-items: center; }
    .val-green { color: #008000; font-weight: bold; }
    .val-red { color: #cc0000; font-weight: bold; }
    .val-black { color: #000000; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC MAP ---
BENCHMARK_LOGIC = {
    "cpi": -1, "inflation": -1, "ppi": -1, "unemployment": -1, "jobless": -1,
    "gdp": 1, "pmi": 1, "sales": 1, "production": 1, "confidence": 1,
    "payroll": 1, "earnings": 1, "sentiment": 1, "order": 1
}

# --- 3. DATA FETCH (STRENGTHENED) ---
@st.cache_data(ttl=30)
def get_live_data(dt):
    try:
        # We fetch a wider range because global news (like BoJ) 
        # often hits 'yesterday' or 'tomorrow' in US-centric APIs.
        start = (dt - timedelta(days=2)).strftime("%Y-%m-%d")
        end = (dt + timedelta(days=2)).strftime("%Y-%m-%d")
        
        # CHANGED: Using v3 endpoint (more stable for free keys)
        url = f"https://financialmodelingprep.com/api/v3/economic_calendar"
        params = {"from": start, "to": end, "apikey": MY_API_KEY}
        
        res = requests.get(url, params=params, timeout=15)
        
        if res.status_code == 403:
            st.error("🚫 API Key Error: Please check if your key is active.")
            return pd.DataFrame()
            
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            # Normalize dates to handle different API formats
            df['dt_obj'] = pd.to_datetime(df['date']).dt.date
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"📡 Connection Issue: {e}")
        return pd.DataFrame()

# --- 4. SIDEBAR ---
st.sidebar.title("Global Controls")
target_date = st.sidebar.date_input("Calendar Date", value=date.today())
impact_filter = st.sidebar.multiselect("Impact", ['High', 'Medium', 'Low'], default=['High', 'Medium', 'Low'])
country_filter = st.sidebar.multiselect(
    "Nifty Drivers", 
    ['IN', 'US', 'CN', 'EU', 'GB', 'JP'], 
    default=['IN', 'US', 'CN', 'EU', 'JP', 'GB']
)

if st.sidebar.button("🔄 Clear Cache & Force Update"):
    st.cache_data.clear()
    st.rerun()

# --- 5. LOGIC ENGINE ---
def calculate_nse_global_logic(row):
    event = str(row.get('event', '')).lower()
    country = str(row.get('country', '')).upper()
    act, est = row.get('actual'), row.get('estimate')
    color_class, nse_sentiment = "val-black", "Neutral"
    
    if pd.isna(act) or str(act).strip() == "" or str(act).lower() in ['none', 'nan']:
        return pd.Series([color_class, nse_sentiment])

    try:
        a, e = float(act), float(est)
        if a == e: return pd.Series(["val-black", "Neutral"])
        direction = next((v for k, v in BENCHMARK_LOGIC.items() if k in event), 1)
        is_pos = (a > e and direction == 1) or (a < e and direction == -1)
        color_class = "val-green" if is_pos else "val-red"
        
        if country == 'IN': nse_sentiment = "Bullish" if is_pos else "Bearish"
        elif country in ['US', 'CN']: nse_sentiment = "Bearish" if is_pos else "Bullish"
        elif country in ['EU', 'GB']: nse_sentiment = "Bullish" if is_pos else "Bearish"
        elif country == 'JP': nse_sentiment = "Bearish" if is_pos else "Bullish"
    except: pass
    return pd.Series([color_class, nse_sentiment])

# --- 6. DASHBOARD RENDER ---
st.title(f"🌍 Global Nifty Macro Calendar")
st.caption(f"Last Sync: {time.strftime('%H:%M:%S')}")

raw_df = get_live_data(target_date)

if not raw_df.empty:
    # Filter for the specific date selected
    df = raw_df[raw_df['dt_obj'] == target_date].copy()
    
    if df.empty:
        st.warning(f"No events found specifically for {target_date}. Showing next available news:")
        # Show the very next available news so the screen isn't empty
        df = raw_df[raw_df['dt_obj'] > target_date].head(5).copy()

    # Apply remaining filters
    df = df[df['impact'].isin(impact_filter)]
    if country_filter:
        df = df[df['country'].isin(country_filter)]

    # Calculate Logic
    df[['Color', 'NSE_Sent']] = df.apply(calculate_nse_global_logic, axis=1)

    # --- RENDER TABLE ---
    st.markdown("""
        <div class="ff-row" style="background:#f4f4f4; border-top:2px solid #333; margin-top:10px;">
            <div style="width:10%" class="ff-header-text">Time</div>
            <div style="width:8%" class="ff-header-text">Cur</div>
            <div style="width:8%" class="ff-header-text">Imp</div>
            <div style="width:40%" class="ff-header-text">Detail</div>
            <div style="width:11%" class="ff-header-text">Actual</div>
            <div style="width:11%" class="ff-header-text">Forecast</div>
            <div style="width:12%" class="ff-header-text">Nifty Impact</div>
        </div>
    """, unsafe_allow_html=True)

    for _, row in df.sort_values('date').iterrows():
        time_str = row['date'].split(" ")[1][:5] if " " in row['date'] else "Day"
        icon = "🔴" if row['impact'] == 'High' else "🟠" if row['impact'] == 'Medium' else "🟡"
        curr_map = {'IN':'INR', 'US':'USD', 'CN':'CNY', 'EU':'EUR', 'GB':'GBP', 'JP':'JPY'}
        curr = curr_map.get(row['country'], row['country'])
        
        s_color = "#00ff41" if row['NSE_Sent'] == "Bullish" else "#ff4b4b" if row['NSE_Sent'] == "Bearish" else "#808495"
        s_label = f"<span style='color:{s_color}; font-weight:bold;'>{row['NSE_Sent']}</span>"
        act_disp = row['actual'] if pd.notna(row['actual']) and str(row['actual']).strip() != "" else "⏳"

        st.markdown(f"""
            <div class="ff-row">
                <div style="width:10%">{time_str}</div>
                <div style="width:8%; font-weight:bold;">{curr}</div>
                <div style="width:8%">{icon}</div>
                <div style="width:40%">{row['event']}</div>
                <div style="width:11%" class="{row['Color']}">{act_disp}</div>
                <div style="width:11%">{row['estimate'] if pd.notna(row['estimate']) else ''}</div>
                <div style="width:12%">{s_label}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.error("Failed to retrieve any data. This usually means the API key has reached its daily limit or the connection is blocked.")
