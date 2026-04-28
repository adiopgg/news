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

# --- 3. LOGIC ENGINE ---
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

# --- 4. DATA FETCH (3-DAY SAFETY WINDOW) ---
@st.cache_data(ttl=20)
def get_live_data(dt):
    try:
        # Fetch window: Yesterday to Tomorrow
        start = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://financialmodelingprep.com/stable/economic-calendar"
        params = {"from": start, "to": end, "apikey": MY_API_KEY}
        headers = {"Cache-Control": "no-cache"}
        
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            full_df = pd.DataFrame(res.json())
            if not full_df.empty:
                # Convert API date strings to actual date objects for comparison
                full_df['dt_obj'] = pd.to_datetime(full_df['date']).dt.date
                # Only return the rows that match the user's selected date
                return full_df[full_df['dt_obj'] == dt]
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 5. SIDEBAR ---
st.sidebar.title("Global Controls")
target_date = st.sidebar.date_input("Calendar Date", value=date.today())
impact_filter = st.sidebar.multiselect("Impact", ['High', 'Medium', 'Low'], default=['High', 'Medium'])
country_filter = st.sidebar.multiselect(
    "Nifty Drivers", 
    ['IN', 'US', 'CN', 'EU', 'GB', 'JP'], 
    default=['IN', 'US', 'CN', 'EU', 'JP', 'GB']
)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("Auto-Refresh (30s)", value=True)

if st.sidebar.button("🔄 Force Refresh API"):
    st.cache_data.clear()
    st.rerun()

# --- 6. DASHBOARD FRAGMENT ---
@st.fragment(run_every="30s" if live_mode else None)
def show_dashboard(dt, impacts, countries):
    df = get_live_data(dt)
    
    st.title(f"🌍 Global Nifty Macro Calendar")
    st.caption(f"Last Sync: {time.strftime('%H:%M:%S')} | Target: {dt.strftime('%d %b %Y')}")

    if not df.empty:
        # Initial Logic Run
        df[['Color', 'NSE_Sent']] = df.apply(calculate_nse_global_logic, axis=1)
        
        # Filtering
        df = df[df['impact'].isin(impacts)]
        if countries:
            df = df[df['country'].isin(countries)]

        # Table Header
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

        # Table Rows
        for _, row in df.sort_values('date').iterrows():
            time_str = row['date'].split(" ")[1][:5] if " " in row['date'] else "Day"
            icon = "🔴" if row['impact'] == 'High' else "🟠" if row['impact'] == 'Medium' else "🟡"
            curr_map = {'IN':'INR', 'US':'USD', 'CN':'CNY', 'EU':'EUR', 'GB':'GBP', 'JP':'JPY'}
            curr = curr_map.get(row['country'], row['country'])
            
            s_color = "#00ff41" if row['NSE_Sent'] == "Bullish" else "#ff4b4b" if row['NSE_Sent'] == "Bearish" else "#808495"
            s_label = f"<span style='color:{s_color}; font-weight:bold;'>{row['NSE_Sent']}</span>"
            
            act_val = row['actual']
            act_disp = act_val if pd.notna(act_val) and str(act_val).strip() != "" else "⏳"

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
        st.info("No data found for this specific date. Try selecting another date or hit refresh.")

# Start
show_dashboard(target_date, impact_filter, country_filter)
