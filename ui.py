import streamlit as st
import requests
from datetime import datetime
import os

# Base URL for the FastAPI backend
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="URL Shortener", page_icon="🔗", layout="centered")

st.title("🔗 URL Shortener")
st.markdown("A simple UI to test the FastAPI + Redis + ZooKeeper URL shortener.")

# --- Tab Layout ---
tab1, tab2, tab3, tab4 = st.tabs(["Shorten URL", "Click & Test", "Analytics", "System Dashboard"])

# --- Tab 1: Shorten URL ---
with tab1:
    st.header("Create a Short URL")
    
    with st.form("shorten_form"):
        original_url = st.text_input("Enter Long URL", placeholder="https://www.example.com/very/long/path")
        custom_expiry = st.number_input("Expiry (Hours)", min_value=1, max_value=720, value=24)
        
        submitted = st.form_submit_button("Shorten!")
        
        if submitted:
            if not original_url:
                st.error("Please enter a valid URL.")
            else:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/shorten",
                        json={"original_url": original_url, "expiry_hours": custom_expiry}
                    )
                    
                    if response.status_code == 201:
                        data = response.json()
                        st.success("Success!")
                        st.markdown(f"**Short URL:** [{data['short_url']}]({data['short_url']})")
                        st.markdown(f"**Short Code:** `{data['short_code']}`")
                        st.markdown(f"**Expires At:** `{data['expires_at']}`")
                        
                        # Save the short code in session state for easy access in other tabs
                        st.session_state.last_short_code = data['short_code']
                        st.session_state.last_short_url = data['short_url']
                        
                    else:
                        st.error(f"Error ({response.status_code}): {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error(f"Could not connect to the backend at {API_BASE_URL}. Is FastAPI running?")

# --- Tab 2: Test URL ---
with tab2:
    st.header("Test a Short URL")
    st.markdown("Test the redirect behaviour.")
    
    test_code = st.text_input(
        "Enter Short Code", 
        value=st.session_state.get('last_short_code', ''),
        help="Just the code (e.g., 'a' or 'b'), not the full URL"
    )
    
    if st.button("Simulate Click"):
        if test_code:
            try:
                # We use allow_redirects=False to inspect what the backend sends back
                response = requests.get(f"{API_BASE_URL}/{test_code}", allow_redirects=False)
                
                if response.status_code in (301, 302, 303, 307, 308):
                    st.success("Redirect Successful!")
                    st.markdown(f"**Redirects to:** `{response.headers.get('location')}`")
                    st.info("The backend recorded this click. Go to the Analytics tab to see the counter increase!")
                elif response.status_code == 404:
                    st.error("URL not found!")
                elif response.status_code == 410:
                    st.error("This short URL has expired.")
                else:
                    st.warning(f"Unexpected status code: {response.status_code}")
            except requests.exceptions.ConnectionError:
                st.error(f"Could not connect to the backend at {API_BASE_URL}. Is FastAPI running?")
        else:
            st.warning("Please enter a short code.")
            
    st.markdown("---")
    st.markdown("**Or test manually by clicking the link directly:**")
    if 'last_short_url' in st.session_state:
        st.markdown(f"[{st.session_state.last_short_url}]({st.session_state.last_short_url})")

# --- Tab 3: Analytics ---
with tab3:
    st.header("URL Analytics")
    
    stats_code = st.text_input(
        "Enter Short Code for Stats", 
        value=st.session_state.get('last_short_code', '')
    )
    
    if st.button("Get Stats"):
        if stats_code:
            try:
                response = requests.get(f"{API_BASE_URL}/stats/{stats_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label="Total Clicks", value=data['click_count'])
                    with col2:
                        st.metric(label="Short Code", value=data['short_code'])
                        
                    st.markdown(f"**Original URL:** `{data['original_url']}`")
                    
                    # Format dates nicely
                    created = datetime.fromisoformat(data['created_at']).strftime("%Y-%m-%d %H:%M:%S")
                    expires = datetime.fromisoformat(data['expires_at']).strftime("%Y-%m-%d %H:%M:%S") if data['expires_at'] else "Never"
                    
                    st.markdown(f"**Created At:** {created}")
                    st.markdown(f"**Expires At:** {expires}")
                    
                else:
                    st.error(f"Error ({response.status_code}): {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend. Is FastAPI running?")
        else:
            st.warning("Please enter a short code.")

# --- Tab 4: System Dashboard ---
with tab4:
    st.header("System Dashboard")
    st.markdown("Real-time analytics from the backing services.")
    
    st.button("Refresh Stats") # Pressing this replays the script and fetches fresh stats
    
    # Initialize time series if not present
    if "time_series" not in st.session_state:
        st.session_state.time_series = {
            "timestamps": [],
            "redis_keys": [],
            "zk_value": []
        }
    
    try:
        res = requests.get(f"{API_BASE_URL}/system/stats")
        if res.status_code == 200:
            sys_data = res.json()
            redis_data = sys_data.get("redis", {})
            zk_data = sys_data.get("zookeeper", {})
            
            # --- Update History ---
            ts = st.session_state.time_series
            ts["timestamps"].append(datetime.now().strftime("%H:%M:%S"))
            ts["redis_keys"].append(int(redis_data.get("total_keys", 0)))
            ts["zk_value"].append(int(zk_data.get("current_value", 0)))
            
            # Keep last 20 data points
            if len(ts["timestamps"]) > 20:
                ts["timestamps"].pop(0)
                ts["redis_keys"].pop(0)
                ts["zk_value"].pop(0)
                
            import pandas as pd
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🔴 Redis")
                for k, v in redis_data.items():
                    st.markdown(f"**{str(k).replace('_', ' ').title()}:** {v}")
            
            with col2:
                st.subheader("🦒 ZooKeeper")
                for k, v in zk_data.items():
                    st.markdown(f"**{str(k).replace('_', ' ').title()}:** {v}")
                    
            st.markdown("---")
            st.subheader("Distribution (Cache vs Total Generated)")
            
            import altair as alt
            current_redis = ts["redis_keys"][-1] if ts["redis_keys"] else 0
            current_zk = ts["zk_value"][-1] if ts["zk_value"] else 0
            
            df_pie = pd.DataFrame({
                "Metric": ["Redis Cached Keys", "Total URLs (ZK Counter)"],
                "Count": [current_redis, current_zk]
            })
            
            pie_chart = alt.Chart(df_pie).mark_arc(innerRadius=40).encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(
                    field="Metric", 
                    type="nominal", 
                    scale=alt.Scale(domain=["Redis Cached Keys", "Total URLs (ZK Counter)"], range=["#FF4B4B", "#00C2A8"]),
                    legend=alt.Legend(title=None, orient="bottom")
                ),
                tooltip=["Metric", "Count"]
            ).properties(
                width=350,
                height=350,
                title="System Objects"
            )
            
            # Render the chart centered and medium-sized
            col_spacer1, col_center, col_spacer2 = st.columns([1, 2, 1])
            with col_center:
                st.altair_chart(pie_chart, use_container_width=False)
                
            st.markdown("---")
            with st.expander("🛠 Raw Data Explorer"):
                st.markdown("Inspect all keys and values currently stored in the backend.")
                if st.button("Fetch Raw Data"):
                    data_res = requests.get(f"{API_BASE_URL}/system/data")
                    if data_res.status_code == 200:
                        raw_data = data_res.json()
                        st.subheader("🔴 Redis Keys")
                        st.json(raw_data.get("redis_keys", {}))
                        
                        st.subheader("🦒 ZooKeeper Nodes")
                        st.json(raw_data.get("zookeeper_data", {}))
                    else:
                        st.error(f"Failed to fetch raw data. ({data_res.status_code})")

        else:
            st.error(f"Failed to fetch system stats. ({res.status_code})")
    except requests.exceptions.ConnectionError:
        st.error("Backend unreachable.")

# --- Sidebar: System Health ---
with st.sidebar:
    st.header("System Health")
    if st.button("Check Health"):
        try:
            health_res = requests.get(f"{API_BASE_URL}/health")
            if health_res.status_code == 200:
                health_data = health_res.json()
                
                st.markdown(f"**Overall:** {'✅ OK' if health_data['status'] == 'ok' else '⚠️ Degraded'}")
                st.markdown(f"**Database:** {'✅ ' if health_data['database'] == 'ok' else '❌ '}{health_data['database']}")
                st.markdown(f"**Redis:** {'✅ ' if health_data['redis'] == 'ok' else '❌ '}{health_data['redis']}")
                st.markdown(f"**ZooKeeper:** {'✅ ' if health_data['zookeeper'] == 'ok' else '❌ '}{health_data['zookeeper']}")
            else:
                st.error("Health check failed.")
        except requests.exceptions.ConnectionError:
            st.error("Backend unreachable.")
