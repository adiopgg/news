import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# ==========================================
# 🔑 API CONFIG
# ==========================================
MY_API_KEY = "akr4lUAIsmZqm0lTH60LPdGhCbnxeICg"
# ==========================================

st.set_page_config(page_title="Global Macro: NSE Edition", layout="wide")

# --- 1. THE FOREX FACTORY "LOGIC MAP" ---
BENCHMARK_LOGIC = {
    "cpi": -1, "inflation": -1, "ppi": -1, "unemployment": -1, "jobless": -1,
    "gdp": 1, "pmi": 1, "sales": 1, "production": 1, "confidence": 1,
    "payroll": 1, "earnings": 1, "sentiment": 1, "order": 1
}

# --- 2. THE UI STYLING ---
st.markdown("""
    <style>
    .main { background: #ffffff; color: #333; }
    .ff-header-text { color: #000000 !important; font-weight: bold !important; font-size: 14px; }
    .ff-row { border-bottom: 1px solid #e0e0e0; padding: 8px 0; display: flex; align-items: center; }
    .val-green { color: #008000; font-weight: bold; }
    .val-red { color: #cc0000; font-weight: bold; }
    .val-black { color: #000000; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR FILTERS (Now including CN, EU, GB) ---
st.sidebar.title("Global Filters")
target_date = st.sidebar.date_input("Calendar Date", value=date.today())
impact_filter = st.sidebar.multiselect("Impact", ['High', 'Medium', 'Low'], default=['High', 'Medium'])
country_filter = st.sidebar.multiselect(
    "Affecting Nifty", 
    ['IN', 'US', 'CN', 'EU', 'GB', 'JP'], 
    default=['IN', 'US', 'CN', 'EU']
)

# --- 4. THE MULTI-COUNTRY NSE LOGIC ENGINE ---
def calculate_nse_global_logic(row):
    event = str(row.get('event', '')).lower()
    country = str(row.get('country', '')).upper()
    act, est = row.get('actual'), row.get('estimate')
    
    color_class, nse_sentiment = "val-black", "Neutral"
    
    if act is not None and est is not None:
        try:
            a, e = float(act), float(est)
            if a == e: return pd.Series(["val-black", "Neutral"])
            
            # Determine Color (Forex Factory Standard)
            direction = 0
            for key, val in BENCHMARK_LOGIC.items():
                if key in event:
                    direction = val
                    break
            if direction == 0: direction = 1
            
            is_positive_data = (a > e and direction == 1) or (a < e and direction == -1)
            color_class = "val-green" if is_positive_data else "val-red"
                
            # --- GLOBAL NSE SENTIMENT LOGIC ---
            if country == 'IN':
                nse_sentiment = "Bullish" if is_positive_data else "Bearish"
            
            elif country == 'US':
                # Strong US = High Yields = FII Outflow from India
                nse_sentiment = "Bearish" if is_positive_data else "Bullish"
            
            elif country == 'CN':
                # Strong China = Competitor for Funds = Often Bearish for Nifty
                nse_sentiment = "Bearish" if is_positive_data else "Bullish"
            
            elif country == 'EU':
                # Strong EU = Export Demand = Bullish for India
                nse_sentiment = "Bullish" if is_positive_data else "Bearish"
                
        except: pass
    return pd.Series([color_class, nse_sentiment])

# --- 5. DATA FLOW ---
@st.cache_data(ttl=300)
def get_data(dt):
    url = f"https://financialmodelingprep.com/stable/economic-calendar"
    params = {"from": dt, "to": dt, "apikey": MY_API_KEY}
    res = requests.get(url, params=params)
    return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()

df = get_data(target_date.strftime("%Y-%m-%d"))

# --- 6. RENDER ---
st.title(f"🌍 Global Macro Calendar (Nifty Impact)")
st.subheader(target_date.strftime("%A, %b %d, %Y"))

if not df.empty:
    df[['Color', 'NSE_Sent']] = df.apply(calculate_nse_global_logic, axis=1)
    df = df[df['impact'].isin(impact_filter)]
    if country_filter:
        df = df[df['country'].isin(country_filter)]

    # Header Row
    st.markdown("""
        <div class="ff-row" style="background:#f4f4f4; border-top:2px solid #333;">
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
        time = row['date'].split(" ")[1][:5] if " " in row['date'] else "Day"
        icon = "🔴" if row['impact'] == 'High' else "🟠" if row['impact'] == 'Medium' else "🟡"
        
        # Currency Labels
        curr_map = {'IN': 'INR', 'US': 'USD', 'CN': 'CNY', 'EU': 'EUR', 'GB': 'GBP', 'JP': 'JPY'}
        curr = curr_map.get(row['country'], row['country'])
        
        # Impact Styling
        sent_color = "#00ff41" if row['NSE_Sent'] == "Bullish" else "#ff4b4b" if row['NSE_Sent'] == "Bearish" else "#808495"
        sent_label = f"<span style='color:{sent_color}; font-weight:bold;'>{row['NSE_Sent']}</span>"

        st.markdown(f"""
            <div class="ff-row">
                <div style="width:10%">{time}</div>
                <div style="width:8%; font-weight:bold;">{curr}</div>
                <div style="width:8%">{icon}</div>
                <div style="width:40%">{row['event']}</div>
                <div style="width:11%" class="{row['Color']}">{row['actual'] if row['actual'] else ''}</div>
                <div style="width:11%">{row['estimate'] if row['estimate'] else ''}</div>
                <div style="width:12%">{sent_label}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("No major data found for this date. Check tomorrow!")
