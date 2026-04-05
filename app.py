import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf

st.set_page_config(layout="wide")

# =========================
# 기본값
# =========================
DEFAULTS = {
    "compact_view": True,          # 간단 보기 (모바일용)
    "use_live": True,
    "qqqi_qty": 500,
    "schd_qty": 5000,
    "monthly_need_m": 200,         # 백만원 단위
    "years": 10,
    "cash_years": 1,
    "reinvest": True,
    "tax_rate_pct": 15,
    "inflation_rate_pct": 3.0,
    "growth_rate_pct": 5.0,
    "qqqi_decay_pct": 3.0,
    "qqqi_div": 0.61,
    "schd_div": 0.28,
    "qqqi_price": 50.0,
    "exchange_rate": 1499.0,
    "last_update": "",
}

# =========================
# query params -> 최초 1회만 반영
# =========================
def parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).lower() in ["true", "1", "yes", "y", "on"]

def load_initial_state():
    for key, default in DEFAULTS.items():
        if key in st.session_state:
            continue

        raw = st.query_params.get(key, None)

        if raw is None:
            st.session_state[key] = default
            continue

        try:
            if isinstance(default, bool):
                st.session_state[key] = parse_bool(raw, default)
            elif isinstance(default, int):
                st.session_state[key] = int(raw)
            elif isinstance(default, float):
                st.session_state[key] = float(raw)
            else:
                st.session_state[key] = raw
        except Exception:
            st.session_state[key] = default

load_initial_state()

if "_live_loaded" not in st.session_state:
    st.session_state._live_loaded = False

if "_prev_use_live" not in st.session_state:
    st.session_state._prev_use_live = st.session_state.use_live

# =========================
# 스타일
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 0.8rem;
    padding-bottom: 1.4rem;
}

div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
    padding: 8px 12px;
}

div[data-testid="stDataFrame"] div[role="table"] {
    font-size: 0.92rem;
}

/* number_input 버튼 터치 효과 완화 */
div[data-testid="stNumberInput"] button {
    -webkit-tap-highlight-color: transparent;
}

div[data-testid="stNumberInput"] button:focus,
div[data-testid="stNumberInput"] button:active,
div[data-testid="stNumberInput"] button:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 실시간 데이터
# =========================
@st.cache_data(ttl=3600)
def get_live_data():
    qqqi = yf.Ticker("QQQI")
    schd = yf.Ticker("SCHD")
    usdkrw = yf.Ticker("KRW=X")

    qqqi_price_series = qqqi.history(period="5d")["Close"].dropna()
    fx_series = usdkrw.history(period="5d")["Close"].dropna()

    qqqi_div_series = qqqi.dividends
    schd_div_series = schd.dividends

    qqqi_price = qqqi_price_series.iloc[-1] if not qqqi_price_series.empty else None
    exchange_rate = fx_series.iloc[-1] if not fx_series.empty else None
    qqqi_div = qqqi_div_series.tail(3).mean() if not qqqi_div_series.empty else None
    schd_div = schd_div_series.iloc[-1] if not schd_div_series.empty else None

    return qqqi_price, exchange_rate, qqqi_div, schd_div

def refresh_live_data(show_message=False):
    try:
        price, fx, q_div_live, s_div_live = get_live_data()

        if price is not None:
            st.session_state.qqqi_price = float(price)
        if fx is not None:
            st.session_state.exchange_rate = float(fx)
        if q_div_live is not None:
            st.session_state.qqqi_div = float(q_div_live)
        if s_div_live is not None:
            st.session_state.schd_div = float(s_div_live)

        st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if show_message:
            st.toast("실시간 데이터를 새로 반영했어")
        return None
    except Exception as e:
        return str(e)

live_error = None

# 최초 1회만 자동 로드
if st.session_state.use_live and not st.session_state._live_loaded:
    live_error = refresh_live_data(show_message=False)
    st.session_state._live_loaded = True

# =========================
# query params 저장
# =========================
def sync_query_params():
    keys = [
        "compact_view", "use_live",
        "qqqi_qty", "schd_qty", "monthly_need_m", "years",
        "cash_years", "reinvest",
        "tax_rate_pct", "inflation_rate_pct", "growth_rate_pct", "qqqi_decay_pct",
        "qqqi_div", "schd_div", "qqqi_price", "exchange_rate"
    ]
    for key in keys:
        st.query_params[key] = st.session_state[key]

# =========================
# 헤더
# =========================
st.title("💰 Dividend AI")

top1, top2 = st.columns([3, 1])
with top1:
    st.caption("QQQI + SCHD 배당 시뮬레이터")
with top2:
    st.toggle("간단 보기", key="compact_view")

# =========================
# 본문 상단 빠른 설정 (간단 보기용)
# =========================
if st.session_state.compact_view:
    with st.expander("⚡ 빠른 설정", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("QQQI 수량", min_value=0, step=100, key="qqqi_qty", format="%d")
        with c2:
            st.number_input("SCHD 수량", min_value=0, step=100, key="schd_qty", format="%d")

# =========================
# 사이드바
# =========================
st.sidebar.title("⚙️ 설정")

if not st.session_state.compact_view:
    with st.sidebar.expander("⚡ 빠른 설정", expanded=True):
        st.number_input("QQQI 수량", min_value=0, step=100, key="qqqi_qty", format="%d")
        st.number_input("SCHD 수량", min_value=0, step=100, key="schd_qty", format="%d")
        st.number_input("월 생활비 (백만원)", min_value=0, step=10, key="monthly_need_m", format="%d")
        st.selectbox("시뮬 기간", [10, 20, 30], key="years")
else:
    with st.sidebar.expander("⚡ 기본 설정", expanded=False):
        st.number_input("월 생활비 (백만원)", min_value=0, step=10, key="monthly_need_m", format="%d")
        st.selectbox("시뮬 기간", [10, 20, 30], key="years")

with st.sidebar.expander("💰 현재 값", expanded=not st.session_state.compact_view):
    st.toggle("실시간 데이터 사용", key="use_live")

    # use_live 상태 변화 감지
    if st.session_state.use_live != st.session_state._prev_use_live:
        if st.session_state.use_live:
            live_error = refresh_live_data(show_message=False)
            st.session_state._live_loaded = True
        else:
            st.session_state._live_loaded = False
        st.session_state._prev_use_live = st.session_state.use_live

    c1, c2 = st.columns(2)
    with c1:
        if st.button("새로고침", use_container_width=True, disabled=not st.session_state.use_live):
            live_error = refresh_live_data(show_message=True)
            st.session_state._live_loaded = True
    with c2:
        st.caption("실시간" if st.session_state.use_live else "수동입력")

    st.number_input(
        f"QQQI 월 배당 (${st.session_state.qqqi_div:,.4f})",
        min_value=0.0,
        step=0.0001,
        key="qqqi_div",
        disabled=st.session_state.use_live,
        format="%.4f"
    )
    st.number_input(
        f"SCHD 분기 배당 (${st.session_state.schd_div:,.4f})",
        min_value=0.0,
        step=0.0001,
        key="schd_div",
        disabled=st.session_state.use_live,
        format="%.4f"
    )
    st.number_input(
        f"QQQI 가격 (${st.session_state.qqqi_price:,.4f})",
        min_value=0.0,
        step=0.0001,
        key="qqqi_price",
        disabled=st.session_state.use_live,
        format="%.4f"
    )
    st.number_input(
        f"환율 ({st.session_state.exchange_rate:,.2f}원)",
        min_value=0.0,
        step=0.01,
        key="exchange_rate",
        disabled=st.session_state.use_live,
        format="%.2f"
    )

    if st.session_state.last_update and st.session_state.use_live:
        st.caption(f"🕒 업데이트: {st.session_state.last_update}")

    if live_error:
        st.warning(f"⚠️ 일부 데이터 실패: {live_error}")

with st.sidebar.expander("📊 시뮬 옵션", expanded=False):
    st.slider("현금으로 버틸 기간 (년)", 0, 3, key="cash_years")
    st.toggle("배당 재투자(QQQI)", key="reinvest")
    st.caption("ON 시 배당금으로 QQQI 재매수 가정")
    st.slider("세율 (%)", 0, 30, key="tax_rate_pct")
    st.slider("물가 상승률 (%)", 0.0, 5.0, key="inflation_rate_pct", step=0.1)
    st.slider("SCHD 성장률 (%)", 0.0, 10.0, key="growth_rate_pct", step=0.1)
    st.slider("QQQI 감소율 (%)", 0.0, 10.0, key="qqqi_decay_pct", step=0.1)

if st.sidebar.button("🔄 초기화", use_container_width=True):
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

sync_query_params()

# =========================
# 현재 값 정리
# =========================
qqqi_qty = int(st.session_state.qqqi_qty)
schd_qty = int(st.session_state.schd_qty)
monthly_need = int(st.session_state.monthly_need_m) * 10000
years = int(st.session_state.years)
months = years * 12
cash_years = int(st.session_state.cash_years)
reinvest = bool(st.session_state.reinvest)

tax_rate = st.session_state.tax_rate_pct / 100
inflation_rate = st.session_state.inflation_rate_pct / 100
growth_rate = st.session_state.growth_rate_pct / 100
qqqi_decay = st.session_state.qqqi_decay_pct / 100

qqqi_div = float(st.session_state.qqqi_div)
schd_div = float(st.session_state.schd_div)
qqqi_price = float(st.session_state.qqqi_price)
exchange_rate = float(st.session_state.exchange_rate)

# =========================
# 시뮬레이션
# =========================
data = []
q = qqqi_qty
s = schd_qty
start_date = datetime.today()

for m in range(months):
    date = start_date + relativedelta(months=m)
    date_str = date.strftime("%Y-%m")

    year_index = m // 12
    year_label = f"{year_index + 1}년차"

    q_div_now = qqqi_div * ((1 - qqqi_decay) ** year_index)
    s_div_now = schd_div * ((1 + growth_rate) ** year_index)

    q_income = q * q_div_now * (1 - tax_rate)
    s_income = s * s_div_now * (1 - tax_rate) if (m + 1) % 3 == 0 else 0

    total_usd = q_income + s_income
    total_krw = total_usd * exchange_rate

    if m < cash_years * 12:
        need = 0
    else:
        need = monthly_need * ((1 + inflation_rate) ** year_index)

    gap = total_krw - need

    data.append([
        year_label, date_str, q, q_income, s, s_income,
        total_usd, total_krw, need, gap
    ])

    if reinvest and qqqi_price > 0:
        q += int(q_income / qqqi_price)
        if (m + 1) % 3 == 0:
            q += int(s_income / qqqi_price)

df = pd.DataFrame(data, columns=[
    "연차", "날짜", "QQQI", "QQQI 배당($)", "SCHD", "SCHD 배당($)",
    "합계($)", "원화", "월 생활비", "월차이"
])

df["분기 배당"] = df["원화"].rolling(3).sum().round().astype("Int64")
df["분기 생활비"] = df["월 생활비"].rolling(3).sum().round().astype("Int64")
df["분기 차이"] = (df["분기 배당"] - df["분기 생활비"]).astype("Int64")

df.loc[(df.index + 1) % 3 != 0, ["분기 배당", "분기 생활비", "분기 차이"]] = None

# =========================
# 요약
# =========================
quarter_now = int(df["원화"].iloc[-3:].sum())
quarter_need = int(df["월 생활비"].iloc[-3:].sum())
quarter_gap = int(quarter_now - quarter_need)
gap_sign = f"{quarter_gap:+,}원"

if st.session_state.compact_view:
    st.info(
        f"마지막 분기 · 배당 {quarter_now:,.0f}원 / 생활비 {quarter_need:,.0f}원 / 차이 {gap_sign}"
    )
else:
    k1, k2, k3 = st.columns(3)
    k1.metric("마지막 분기 배당", f"{quarter_now:,.0f}원")
    k2.metric("마지막 분기 생활비", f"{quarter_need:,.0f}원")
    k3.metric("마지막 분기 차이", gap_sign)

if quarter_gap > 0:
    st.success("✅ 배당 생활 가능")
else:
    st.warning("⚠️ 생활비 부족")

# =========================
# 표
# =========================
def plus_minus_format(x):
    if pd.isnull(x):
        return ""
    return f"{int(x):+,}"

def highlight(row):
    if pd.notnull(row["분기 배당"]):
        if row["분기 차이"] > 0:
            return ["background-color: rgba(34,197,94,0.10)"] * len(row)
        else:
            return ["background-color: rgba(239,68,68,0.10)"] * len(row)
    return ["color:#999"] * len(row)

if st.session_state.compact_view:
    df_display = df[
        ["연차", "날짜", "QQQI", "분기 배당", "분기 차이"]
    ].copy()

    styled = df_display.style.format({
        "QQQI": "{:,.0f}",
        "분기 배당": "{:,.0f}",
        "분기 차이": plus_minus_format,
    }).apply(highlight, axis=1)

    st.dataframe(
        styled,
        height=340,
        use_container_width=True,
        hide_index=True
    )
else:
    df_display = df[
        [
            "연차", "날짜",
            "QQQI", "QQQI 배당($)",
            "SCHD", "SCHD 배당($)",
            "월 생활비",
            "분기 배당", "분기 생활비", "분기 차이"
        ]
    ].copy()

    styled = df_display.style.format({
        "QQQI 배당($)": "{:,.2f}",
        "SCHD 배당($)": "{:,.2f}",
        "월 생활비": "{:,.0f}",
        "분기 배당": "{:,.0f}",
        "분기 생활비": "{:,.0f}",
        "분기 차이": plus_minus_format,
    }).apply(highlight, axis=1)

    st.dataframe(
        styled,
        height=500,
        use_container_width=True,
        hide_index=True
    )

# =========================
# 그래프
# =========================
st.markdown("#### 📈 배당 흐름")

df_q = df.dropna(subset=["분기 배당"]).copy()
df_q["날짜"] = pd.to_datetime(df_q["날짜"], format="%Y-%m")
df_q["차이표시"] = df_q["분기 차이"].apply(
    lambda x: f"{int(x):+,}원" if pd.notnull(x) else ""
)

graph_height = 220 if st.session_state.compact_view else 320

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_q["날짜"],
    y=df_q["분기 배당"],
    fill="tozeroy",
    line=dict(width=2),
    hovertemplate="배당 %{y:,.0f}원<extra></extra>",
    showlegend=False,
    name="배당"
))

fig.add_trace(go.Scatter(
    x=df_q["날짜"],
    y=df_q["분기 생활비"],
    line=dict(dash="dash", width=2),
    hovertemplate="생활비 %{y:,.0f}원<extra></extra>",
    showlegend=False,
    name="생활비"
))

# 차이 표시용 투명 trace
fig.add_trace(go.Scatter(
    x=df_q["날짜"],
    y=df_q["분기 배당"],
    mode="lines",
    line=dict(width=0),
    customdata=df_q["차이표시"],
    hovertemplate="<b>차이 %{customdata}</b><extra></extra>",
    showlegend=False,
    name="차이"
))

fig.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    title=None,
    hovermode="x unified",
    height=graph_height,
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False
)

fig.update_yaxes(
    showgrid=True,
    gridcolor="rgba(0,0,0,0.06)",
    zeroline=False,
    showticklabels=not st.session_state.compact_view,
    title=None,
    ticks=""
)

fig.update_xaxes(
    tickformat="%Y",
    hoverformat="%Y-%m",
    dtick="M12",
    showgrid=False,
    title=None,
    ticks="",
    showticklabels=True
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# 핵심 결과
# =========================
st.markdown("#### 📌 핵심 결과")

# 1. 월 300만원
quarter_df = df.dropna(subset=["분기 배당"])
target = 3000000 * 3
reach = quarter_df[quarter_df["분기 배당"] >= target]

if not reach.empty:
    first_date = reach.iloc[0]["날짜"]
    start = datetime.today()
    target_date = datetime.strptime(first_date, "%Y-%m")
    diff_months = (target_date.year - start.year) * 12 + (target_date.month - start.month)
    diff_years = diff_months / 12
    reach_text = f"{first_date} ({diff_years:.1f}년)"
else:
    reach_text = "미도달"

# 2. 졸업 수량
found = False
graduate_qty = None

for qty in range(int(qqqi_qty), int(max(qqqi_qty * 3, qqqi_qty + 50)), 50):
    q = qty
    temp = []

    for m in range(months):
        year_index = m // 12

        q_div_now = qqqi_div * ((1 - qqqi_decay) ** year_index)
        s_div_now = schd_div * ((1 + growth_rate) ** year_index)

        q_income = q * q_div_now * (1 - tax_rate)
        s_income = schd_qty * s_div_now * (1 - tax_rate) if (m + 1) % 3 == 0 else 0

        total = (q_income + s_income) * exchange_rate

        if m < cash_years * 12:
            need = 0
        else:
            need = monthly_need * ((1 + inflation_rate) ** year_index)

        temp.append(total - need)

    temp_df = pd.DataFrame(temp, columns=["gap"])
    temp_df["quarter"] = temp_df["gap"].rolling(3).sum()
    qdf = temp_df.dropna()

    if not qdf.empty and (qdf["quarter"] >= 0).all():
        graduate_qty = qty
        found = True
        break

graduate_text = f"{graduate_qty:,}주" if found else "미충족"

# 3. 안정 시점
start_idx = cash_years * 12
quarter_df2 = df.iloc[start_idx:].dropna(subset=["분기 차이"])

stable_start = None
for i in range(len(quarter_df2)):
    sub = quarter_df2.iloc[i:]
    if (sub["분기 차이"] >= 0).all():
        stable_start = quarter_df2.iloc[i]["날짜"]
        break

stable_text = f"{stable_start}" if stable_start else "없음"

summary_df = pd.DataFrame({
    "항목": ["월 300만원", "QQQI 졸업", "안정 시점"],
    "결과": [reach_text, graduate_text, stable_text]
})

st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True
)