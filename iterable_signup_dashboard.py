import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AAA Enrollment Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — clean light style matching screenshot ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #ffffff;
    color: #1e2330;
}

[data-testid="stAppViewContainer"] { background: #ffffff; }
[data-testid="stSidebar"] {
    background: #f8f9fc;
    border-right: 1px solid #e8eaf0;
}
[data-testid="stSidebar"] * { color: #444 !important; }

.kpi-section-title {
    font-size: 22px;
    font-weight: 700;
    color: #1e2330;
    margin: 0 0 28px 0;
}
.kpi-divider {
    border: none;
    border-top: 1px solid #e8eaf0;
    margin: 36px 0;
}
.kpi-block { padding: 0 0 4px 0; }
.kpi-label {
    font-size: 13px;
    font-weight: 400;
    color: #5a6278;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 42px;
    font-weight: 300;
    color: #1e2330;
    line-height: 1;
    letter-spacing: -1px;
}

.section-title {
    font-size: 17px;
    font-weight: 600;
    color: #1e2330;
    margin: 36px 0 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #e8eaf0;
}

div[data-testid="stSelectbox"] label,
div[data-testid="stDateInput"] label,
div[data-testid="stTextInput"] label {
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #5a6278 !important;
}

.stButton > button {
    background: #1e2330;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 10px 28px;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    width: 100%;
    transition: background 0.2s;
}
.stButton > button:hover { background: #3a4255; }
.stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
EMPLOYER_NAME    = "American Automobile Association"
ENROLLMENT_VALUE = "enrolled"

# ── Sidebar ────────────────────────────────────────────────────────────────────
API_KEY = "90f3cfed80ff406498a95991e99472f4"

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    api_key = API_KEY
    st.markdown("---")
    st.markdown(
        f"<small style='color:#8a8fa8'>Filtered to:<br>"
        f"<b>Employer:</b> {EMPLOYER_NAME}<br>"
        f"<b>Status:</b> {ENROLLMENT_VALUE.title()}<br>"
        f"<b>Date Range:</b> Nov 1 2025 – Today</small>",
        unsafe_allow_html=True,
    )

# Fixed date range
start_date = datetime(2025, 11, 1).date()
end_date   = datetime.today().date()


# ── Data fetching ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_users(api_key: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    url = "https://api.iterable.com/api/export/data.json"
    headers = {"Api-Key": api_key}
    params = {
        "dataTypeName": "user",
        "startDateTime": datetime.utcfromtimestamp(start_ts / 1000).strftime("%Y-%m-%d %H:%M:%S"),
        "endDateTime":   datetime.utcfromtimestamp(end_ts   / 1000).strftime("%Y-%m-%d %H:%M:%S"),
        "omitFields": "",
    }
    response = requests.get(url, headers=headers, params=params, stream=True, timeout=120)
    if response.status_code != 200:
        raise ValueError(f"API error {response.status_code}: {response.text[:300]}")

    records = []
    for line in response.iter_lines():
        if line:
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    if not records:
        return pd.DataFrame()

    df = pd.json_normalize(records)

    keep = [
        "email", "firstName", "lastName",
        "signupDate", "signupSource",
        "enrollmentStatus", "isEnrolled",
        "employerName", "employeeOrDependent",
        "planType", "city", "mailingAddressState",
        "itblInternal.documentCreatedAt",
        "profileUpdatedAt", "gender",
    ]
    existing = [c for c in keep if c in df.columns]
    df = df[existing].copy()

    for col in ["signupDate", "itblInternal.documentCreatedAt", "profileUpdatedAt"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    return df


# ── Plotly theme ───────────────────────────────────────────────────────────────
ACCENT  = "#3b4fd8"
ACCENT2 = "#6875f5"
GREEN   = "#16a34a"
AMBER   = "#d97706"
ROSE    = "#dc2626"
PALETTE = [ACCENT, ACCENT2, GREEN, AMBER, ROSE, "#0891b2", "#9333ea"]

def plotly_layout(title="", height=340):
    return dict(
        title=dict(text=title, font=dict(family="Inter", size=15, color="#1e2330")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8f9fc",
        font=dict(family="Inter", color="#1e2330", size=12),
        xaxis=dict(gridcolor="#e8eaf0", linecolor="#e8eaf0", tickfont=dict(color="#5a6278")),
        yaxis=dict(gridcolor="#e8eaf0", linecolor="#e8eaf0", tickfont=dict(color="#5a6278")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#1e2330")),
        margin=dict(l=12, r=12, t=48, b=12),
        height=height,
    )


# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:28px;font-weight:700;color:#1e2330;margin-bottom:4px'>"
    "AAA Enrollment Dashboard</h1>"
    "<p style='color:#8a8fa8;font-size:13px;margin-top:0'>"
    "American Automobile Association · Enrolled Members · Iterable</p>",
    unsafe_allow_html=True,
)

# ── Fetch & filter ─────────────────────────────────────────────────────────────
with st.spinner("Fetching data from Iterable…"):
    try:
        start_ms = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000)
        end_ms   = int(datetime.combine(end_date,   datetime.max.time()).timestamp() * 1000)
        df_raw   = fetch_users(api_key, start_ms, end_ms)
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")
        st.stop()

if df_raw.empty:
    st.warning("No user records found for the selected date range.")
    st.stop()

df = df_raw.copy()

# All AAA members (any enrollment status) — used for velocity denominator
df_all_aaa = df_raw.copy()
if "employerName" in df_all_aaa.columns:
    df_all_aaa = df_all_aaa[df_all_aaa["employerName"].str.strip().str.lower() == EMPLOYER_NAME.lower()]
total_aaa_members = len(df_all_aaa)

# Filter: employer = American Automobile Association
if "employerName" in df.columns:
    df = df[df["employerName"].str.strip().str.lower() == EMPLOYER_NAME.lower()]

# Filter: enrollmentStatus = enrolled
if "enrollmentStatus" in df.columns:
    df = df[df["enrollmentStatus"].str.strip().str.lower() == ENROLLMENT_VALUE]
elif "isEnrolled" in df.columns:
    df = df[df["isEnrolled"] == True]

if df.empty:
    st.warning("No enrolled AAA members found for the selected date range.")
    st.stop()

# ── Compute KPIs ───────────────────────────────────────────────────────────────
total_enrolled = len(df)
employees  = 0
dependents = 0
if "employeeOrDependent" in df.columns:
    employees  = int((df["employeeOrDependent"].str.strip().str.lower() == "employee").sum())
    dependents = int((df["employeeOrDependent"].str.strip().str.lower() == "dependent").sum())

# Velocity = enrolled members / number of days in selected range
date_range_days = max((end_date - start_date).days, 1)
velocity_per_day = total_enrolled / date_range_days
enrollment_velocity = f"{velocity_per_day:.1f}"

# ── Key Metrics ────────────────────────────────────────────────────────────────
st.markdown("<div class='kpi-section-title'>Key Metrics</div>", unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>Total AAA Members</div>"
        f"<div class='kpi-value'>{total_aaa_members:,}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>Enrolled AAA Members</div>"
        f"<div class='kpi-value'>{total_enrolled:,}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>Employees Enrolled</div>"
        f"<div class='kpi-value'>{employees:,}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>Dependents Enrolled</div>"
        f"<div class='kpi-value'>{dependents:,}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with k5:
    st.markdown(
        f"<div class='kpi-block'>"
        f"<div class='kpi-label'>AAA Velocity</div>"
        f"<div class='kpi-value'>{enrollment_velocity} <span style='font-size:24px;font-weight:300;color:#5a6278'>/ day</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr class='kpi-divider'>", unsafe_allow_html=True)

# ── Enrollments over time ──────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Enrollments Over Time</div>", unsafe_allow_html=True)

# Use documentCreatedAt as the date field for monthly grouping
date_col = None
for col in ["itblInternal.documentCreatedAt", "profileUpdatedAt", "signupDate"]:
    if col in df.columns and df[col].notna().any():
        date_col = col
        break

if date_col:
    df_time = df.dropna(subset=[date_col]).copy()
    df_time["month"] = pd.to_datetime(df_time[date_col], errors="coerce", utc=True).dt.to_period("M").dt.to_timestamp()
    df_time = df_time.dropna(subset=["month"])

    monthly = df_time.groupby("month").size().reset_index(name="enrollments")

    # Fill all months from Jan 2026 to current month (including zeros)
    all_months = pd.date_range(start="2026-01-01", end=datetime.today().strftime("%Y-%m-01"), freq="MS")
    monthly = monthly.set_index("month").reindex(all_months, fill_value=0).reset_index()
    monthly.columns = ["month", "enrollments"]
    monthly["cumulative"] = monthly["enrollments"].cumsum()
    monthly["month_label"] = monthly["month"].dt.strftime("%b %Y")

    tab1, tab2 = st.tabs(["Monthly Enrollments", "Cumulative Growth"])
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["month_label"], y=monthly["enrollments"],
            marker_color=ACCENT, name="Enrollments",
            text=monthly["enrollments"], textposition="outside",
        ))
        fig.update_layout(**plotly_layout("Monthly Enrollments"))
        fig.update_xaxes(tickangle=0)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=monthly["month_label"], y=monthly["cumulative"],
            mode="lines+markers", fill="tozeroy",
            fillcolor="rgba(59,79,216,0.08)",
            line=dict(color=ACCENT, width=2),
            marker=dict(size=6, color=ACCENT),
        ))
        fig2.update_layout(**plotly_layout("Cumulative Enrollments"))
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No date field available for time-series charts.")

# ── Employee vs Dependent breakdown ───────────────────────────────────────────
if "employeeOrDependent" in df.columns and df["employeeOrDependent"].notna().any():
    st.markdown("<div class='section-title'>Employee vs Dependent Breakdown</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        eod = df["employeeOrDependent"].str.strip().str.title().value_counts().reset_index()
        eod.columns = ["type", "count"]
        fig = px.pie(eod, names="type", values="count",
                     color_discrete_sequence=[ACCENT, ACCENT2], hole=0.55)
        fig.update_traces(textfont_size=13)
        fig.update_layout(**plotly_layout("Enrollment Split", height=320))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        if "signupDate" in df.columns and df["signupDate"].notna().any():
            df_eod = df.dropna(subset=["signupDate", "employeeOrDependent"]).copy()
            df_eod["week"] = df_eod["signupDate"].dt.to_period("W").dt.start_time
            df_eod["type"] = df_eod["employeeOrDependent"].str.strip().str.title()
            eod_weekly = df_eod.groupby(["week", "type"]).size().reset_index(name="count")
            fig3 = px.line(eod_weekly, x="week", y="count", color="type",
                           color_discrete_sequence=[ACCENT, ACCENT2])
            fig3.update_traces(line_width=2)
            fig3.update_layout(**plotly_layout("Employee vs Dependent Over Time", height=320))
            st.plotly_chart(fig3, use_container_width=True)

# ── Gender breakdown ───────────────────────────────────────────────────────────
if "gender" in df.columns and df["gender"].notna().any():
    st.markdown("<div class='section-title'>Gender Breakdown</div>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)

    with g1:
        gender_counts = df["gender"].str.strip().str.title().value_counts().reset_index()
        gender_counts.columns = ["gender", "count"]
        fig = px.pie(
            gender_counts, names="gender", values="count",
            color_discrete_sequence=[ACCENT, ACCENT2, GREEN, AMBER],
            hole=0.55,
        )
        fig.update_traces(textfont_size=13)
        fig.update_layout(**plotly_layout("Gender Split", height=320))
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        fig = px.bar(
            gender_counts, x="gender", y="count",
            color="gender",
            color_discrete_sequence=[ACCENT, ACCENT2, GREEN, AMBER],
            text="count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(**plotly_layout("Gender Count", height=320))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ── Geography ──────────────────────────────────────────────────────────────────
if "mailingAddressState" in df.columns and df["mailingAddressState"].notna().any():
    st.markdown("<div class='section-title'>Enrollments by State</div>", unsafe_allow_html=True)
    state_data = df["mailingAddressState"].value_counts().head(15).reset_index()
    state_data.columns = ["state", "count"]
    fig = px.bar(state_data, x="state", y="count",
                 color="count", color_continuous_scale=[[0, "#dde1f7"], [1, ACCENT]])
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**plotly_layout("Top 15 States", height=320))
    st.plotly_chart(fig, use_container_width=True)

# ── Plan type ──────────────────────────────────────────────────────────────────
if "planType" in df.columns and df["planType"].notna().any():
    st.markdown("<div class='section-title'>Plan Type Distribution</div>", unsafe_allow_html=True)
    pt = df["planType"].value_counts().head(10).reset_index()
    pt.columns = ["plan", "count"]
    fig = px.bar(pt, x="count", y="plan", orientation="h",
                 color_discrete_sequence=[ACCENT2])
    fig.update_layout(**plotly_layout("Plan Types", height=320))
    fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, use_container_width=True)

# ── Raw data ───────────────────────────────────────────────────────────────────
with st.expander("📋 View Raw Data"):
    st.dataframe(
        df.sort_values("signupDate", ascending=False) if "signupDate" in df.columns else df,
        use_container_width=True, height=400,
    )
    csv = df.to_csv(index=False).encode()
    st.download_button("⬇ Download CSV", csv, "aaa_enrolled_members.csv", "text/csv")

st.markdown(
    "<p style='text-align:center;color:#c0c4d0;font-size:12px;margin-top:48px'>"
    "AAA Enrollment Dashboard · Iterable · built with Streamlit</p>",
    unsafe_allow_html=True,
)
