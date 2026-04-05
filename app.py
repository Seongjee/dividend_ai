import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import os
import yfinance as yf
import streamlit.components.v1 as components

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(layout="wide")

# =========================
# 상태 초기화
# =========================
if "initialized" not in st.session_state:
    st.session_state.initialized = True

# =========================
# 📡 실시간 데이터
# =========================
@st.cache_data(ttl=3600)
def get_live_data():
    qqqi = yf.Ticker("QQQI")
    schd = yf.Ticker("SCHD")
    usdkrw = yf.Ticker("KRW=X")

    price_data = qqqi.history(period="5d")["Close"].dropna()
    price = price_data.iloc[-1] if not price_data.empty else None

    fx_data = usdkrw.history(period="5d")["Close"].dropna()
    fx = fx_data.iloc[-1] if not fx_data.empty else None

    q_series = qqqi.dividends
    q_div = q_series.tail(3).mean() if not q_series.empty else None

    s_series = schd.dividends
    s_div = s_series.iloc[-1] if not s_series.empty else None

    return price, fx, q_div, s_div

# =========================
# 사이드바
# =========================
st.sidebar.title("⚙️ 설정")

is_mobile = st.sidebar.toggle("모바일 모드", True)
expanded_default = not is_mobile

if st.sidebar.button("🔄 초기화"):
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

use_live = st.sidebar.toggle("실시간 데이터 사용", True)

# 👉 업데이트 시간 표시용
if "last_update" not in st.session_state:
    st.session_state.last_update = None

# =========================
# 🔥 실시간 먼저 적용 (위젯 생성 전)
# =========================
if use_live:
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

        if "qqqi_price" not in st.session_state:
            st.session_state.qqqi_price = float(price)

        if "exchange_rate" not in st.session_state:
            st.session_state.exchange_rate = float(fx)

        if "qqqi_div" not in st.session_state:
            st.session_state.qqqi_div = float(q_div_live)

        if "schd_div" not in st.session_state:
            st.session_state.schd_div = float(s_div_live)


        st.session_state.last_update = datetime.now()

        st.sidebar.success("📡 실시간 반영됨")

    except Exception as e:
        st.sidebar.warning(f"⚠️ 일부 데이터 실패: {e}")

# =========================
# 입력 함수
# =========================
def load_from_query(key, default, cast_type=int):
    if key in st.query_params:
        try:
            return cast_type(st.query_params[key])
        except:
            return default
    return default

def input_int(label, key, default, step=1, disabled=False):
    if key not in st.session_state:
        st.session_state[key] = load_from_query(key, default, int)

    return st.number_input(   # 🔥 sidebar 제거
        label,
        step=step,
        key=key,
        disabled=disabled,
        format="%d"
    )

def input_float(label, key, default, step=0.01, disabled=False):
    if key not in st.session_state:
        st.session_state[key] = load_from_query(key, default, float)

    return st.number_input(
        label,
        step=float(step),
        key=key,
        disabled=disabled
    )

# =========================
# 📦 사이드바 입력 (Expander 구조)
# =========================
# 기본 설정
with st.sidebar.expander("📦 기본 설정", expanded=True):

    qqqi_qty = input_int("QQQI 수량", "qqqi_qty", 500)
    schd_qty = input_int("SCHD 수량", "schd_qty", 5000)

    monthly_need_m = input_int("월 생활비 (백만원)", "monthly_need_m", 200)
    monthly_need = monthly_need_m * 10000

    cash_years = st.slider("💰 현금으로 버틸 기간 (년)", 0, 3, 1)
    reinvest = st.toggle("배당 재투자", True)

# 상세 옵션
with st.sidebar.expander("📊 상세 옵션", expanded=expanded_default):

    years = st.selectbox("시뮬 기간", [10, 20, 30])
    months = years * 12

    tax_rate = st.slider("세율 (%)", 0, 30, 15) / 100
    inflation_rate = st.slider("물가 상승률 (%)", 0.0, 5.0, 3.0) / 100

    growth_rate = st.slider("SCHD 성장률 (%)", 0.0, 10.0, 5.0) / 100
    qqqi_decay = st.slider("QQQI 감소율 (%)", 0.0, 10.0, 3.0) / 100

# 현재 가격
with st.sidebar.expander("💰 현재 가격", expanded=expanded_default):
    qqqi_div = input_float(f"QQQI 월 배당 (${st.session_state.qqqi_div:,.4f})", "qqqi_div", 0.61, 0.0001, disabled=use_live)
    schd_div = input_float(f"SCHD 분기 배당 (${st.session_state.schd_div:,.4f})", "schd_div", 0.28, 0.0001, disabled=use_live)
    qqqi_price = input_float(f"QQQI 가격 (${st.session_state.qqqi_price:,.2f})", "qqqi_price", 50.0, 0.0001, disabled=use_live)
    exchange_rate = input_float(f"환율 ({st.session_state.exchange_rate:,.2f}원)", "exchange_rate", 1499.0, 1.0, disabled=use_live)

    # 현재값 표시
    if use_live:
        if st.session_state.last_update:
            st.caption(
                f"🕒 업데이트: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}"
            )

# =========================
# 🔥 입력값 URL 저장
# =========================
for key in [
    "qqqi_qty",
    "schd_qty",
    "monthly_need_m",
    "qqqi_div",
    "schd_div",
    "exchange_rate",
    "qqqi_price"
]:
    if key in st.session_state:
        st.query_params[key] = st.session_state[key]
        
# =========================
# 시뮬레이션 (기존 그대로)
# =========================
data = []
q = qqqi_qty
s = schd_qty
start_date = datetime.today()

for m in range(months):

    date = start_date + relativedelta(months=m)
    date_str = date.strftime("%Y-%m")

    year_index = m // 12
    year_label = f"{year_index+1}년차"

    q_div = st.session_state.qqqi_div * ((1 - qqqi_decay) ** year_index)
    s_div = st.session_state.schd_div * ((1 + growth_rate) ** year_index)

    q_income = q * q_div * (1 - tax_rate)
    s_income = s * s_div * (1 - tax_rate) if (m + 1) % 3 == 0 else 0

    total = q_income + s_income
    krw = total * st.session_state.exchange_rate

    if m < cash_years * 12:
        need = 0
    else:
        need = monthly_need * ((1 + inflation_rate) ** year_index)

    gap = krw - need

    data.append([
        year_label, date_str, q, q_income, s, s_income,
        total, krw, need, gap
    ])

    if reinvest:
        q += int(q_income / st.session_state.qqqi_price)
        if (m + 1) % 3 == 0:
            q += int(s_income / st.session_state.qqqi_price)

df = pd.DataFrame(data, columns=[
    "연차","날짜","QQQI","QQQI($)","SCHD","SCHD($)",
    "합계($)","원화","월 생활비","월차이"
])

# =========================
# 이하 기존 그대로 (생략 없음)
# =========================
df["분기 배당"] = df["원화"].rolling(3).sum().round().astype("Int64")
df["분기 생활비"] = df["월 생활비"].rolling(3).sum().round().astype("Int64")
df["분기 차이"] = (df["분기 배당"] - df["분기 생활비"]).astype("Int64")
df["상태"] = df["분기 차이"].apply(lambda x: "✅" if x > 0 else "❌")

df.loc[(df.index + 1) % 3 != 0,
       ["분기 배당","분기 생활비","분기 차이"]] = None

st.subheader("💰 Dividend AI (QQQI + SCHD)")

# 🔥 분기 KPI 추가
quarter_now = df["원화"].iloc[-3:].sum()
quarter_need = df["월 생활비"].iloc[-3:].sum()
quarter_gap = quarter_now - quarter_need

# =========================
# 🔥 KPI 카드 UI
# =========================

def kpi_card(title, value, color):
    st.markdown(f"""
    <div style="
        background-color:{color};
        padding:16px;
        border-radius:12px;
        text-align:center;
        color:white;
        font-weight:600;
    ">
        <div style="font-size:14px; opacity:0.9;">{title}</div>
        <div style="font-size:22px; margin-top:6px;">{value}</div>
    </div>
    """, unsafe_allow_html=True)


# 👉 색상 로직
if quarter_gap > 0:
    gap_color = "#2ecc71"   # 초록
else:
    gap_color = "#e74c3c"   # 빨강


# 👉 PC / 모바일 분기
if not is_mobile:
    col1, col2, col3 = st.columns(3)

    with col1:
        kpi_card(f"{years}년 후 분기 배당", f"{quarter_now:,.0f}원", "#3498db")

    with col2:
        kpi_card(f"{years}년 후 분기 생활비", f"{quarter_need:,.0f}원", "#f39c12")

    with col3:
        kpi_card(f"{years}년 후 분기 차이", f"{quarter_gap:,.0f}원", gap_color)

else:
    kpi_card(f"{years}년 후 분기 배당", f"{quarter_now:,.0f}원", "#3498db")
    st.markdown("")

    kpi_card(f"{years}년 후 분기 생활비", f"{quarter_need:,.0f}원", "#f39c12")
    st.markdown("")

    kpi_card(f"{years}년 후 분기 차이", f"{quarter_gap:,.0f}원", gap_color)


# 🔥 상태 표시
if quarter_gap > 0:
    st.success("🔥 배당으로 생활 가능")
else:
    st.warning("⚠️ 아직 부족")

#
df_display = df[
    [
        "연차","날짜",
        "QQQI","QQQI($)",
        "SCHD","SCHD($)",
        "월 생활비",
        "분기 배당","분기 생활비","분기 차이"
    ]
].copy()

def highlight(row):
    if pd.notnull(row["분기 배당"]):
        if row["분기 차이"] > 0:
            return ["background-color: rgba(0,180,0,0.15)"] * len(row)
        else:
            return ["background-color: rgba(255,0,0,0.15)"] * len(row)
    return ["color:#999"] * len(row)


styled = df_display.style.format({
    "QQQI($)": "{:,.2f}",
    "SCHD($)": "{:,.2f}",
    "월 생활비": "{:,.0f}",
    "분기 배당": "{:,.0f}",
    "분기 생활비": "{:,.0f}",
    "분기 차이": "{:,.0f}"
}).apply(highlight, axis=1)

if not is_mobile:
    # 💻 PC
    st.dataframe(styled, height=520)

else:
    # 📱 모바일

    # 원화 + 달러 둘 다 유지
    mobile_df = df[
        [
            "날짜",
            "QQQI", #"QQQI($)",
            #"SCHD", #"SCHD($)",
            "월 생활비",
            "분기 배당", "분기 차이"
        ]
    ].copy()

    st.dataframe(
        mobile_df.style.format({
            #"QQQI($)": "{:,.2f}",
            #"SCHD($)": "{:,.2f}",
            "월 생활비": "{:,.0f}",
            "분기 배당": "{:,.0f}",
            "분기 차이": "{:,.0f}"
        }),
        height=400
    )

# =========================
# 그래프 시작
# =========================
import plotly.graph_objects as go
import pandas as pd

df_q = df.dropna(subset=["분기 배당"]).copy()

# ✅ 1️⃣ 날짜 타입 변환
df_q['날짜'] = pd.to_datetime(df_q['날짜'], format="%Y-%m")

# ✅ 색상
colors = df_q["분기 차이"].apply(lambda x: "green" if x >= 0 else "red")

fig = go.Figure()

# ✅ 분기 배당
fig.add_trace(go.Scatter(
    x=df_q['날짜'],
    y=df_q['분기 배당'],
    name='분기 배당',
    fill='tozeroy',
    hovertemplate="%{y:,.0f}원"
))

# ✅ 분기 생활비
fig.add_trace(go.Scatter(
    x=df_q['날짜'],
    y=df_q['분기 생활비'],
    name='분기 생활비',
    line=dict(dash='dash'),
    hovertemplate="%{y:,.0f}원"
))

# ✅ 분기 차이
fig.add_trace(go.Bar(
    x=df_q['날짜'],
    y=df_q['분기 차이'],
    name='분기 차이',
    marker_color = ['#2ecc71' if x >= 0 else '#e74c3c' for x in df_q["분기 차이"]],
    opacity=0.5,
    hovertemplate="%{y:,.0f}원"
))

# ✅ 2️⃣ Y축 백만원 단위
fig.update_layout(
    plot_bgcolor='white',
    paper_bgcolor='white',
    title="📊 분기 배당 vs 생활비",
    yaxis_title="금액 (원)",
    hovermode="x unified",
    xaxis=dict(
        hoverformat="%Y-%m"
    )
)

fig.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

fig.update_yaxes(
    tickformat=",",
    title_text="금액 (원)"
)

fig.add_hline(y=0, line_dash="dash")

st.plotly_chart(fig, use_container_width=True)

# =========================
# 그래프 여기까지
# =========================


# =========================
# 월 300 달성 시점
# =========================
quarter_df = df.dropna(subset=["분기 배당"])
target = 3000000 * 3
reach = quarter_df[quarter_df["분기 배당"] >= target]

st.subheader("📍 월 300만원 달성 시점")

if not reach.empty:
    first_date = reach.iloc[0]["날짜"]

    start = datetime.today()
    target_date = datetime.strptime(first_date, "%Y-%m")

    diff_months = (target_date.year - start.year) * 12 + (target_date.month - start.month)
    diff_years = diff_months / 12

    st.success(f"👉 {first_date} (약 {diff_years:.1f}년 후)")
else:
    st.warning("❌ 달성 못함")

# =========================
# QQQI 졸업 수량
# =========================
st.subheader("🎯 QQQI 졸업 수량")

found = False

for qty in range(int(qqqi_qty), int(qqqi_qty * 3), 50):

    q = qty
    temp = []

    for m in range(months):

        year_index = m // 12

        q_div = qqqi_div * ((1 - qqqi_decay) ** year_index)
        s_div = schd_div * ((1 + growth_rate) ** year_index)

        q_income = q * q_div * (1 - tax_rate)
        s_income = schd_qty * s_div * (1 - tax_rate) if (m + 1) % 3 == 0 else 0

        total = (q_income + s_income) * exchange_rate

        if m < cash_years * 12:
            need = 0
        else:
            need = monthly_need * ((1 + inflation_rate) ** year_index)

        temp.append(total - need)

    temp_df = pd.DataFrame(temp, columns=["gap"])
    temp_df["quarter"] = temp_df["gap"].rolling(3).sum()

    qdf = temp_df.dropna()

    if (qdf["quarter"] >= 0).all():
        st.success(f"👉 약 {qty:,}주부터 추가 매수 불필요")
        found = True
        break

if not found:
    st.warning("❗ 졸업 불가능")

###
start_idx = cash_years * 12

quarter_df = df.iloc[start_idx:].dropna(subset=["분기 차이"])

stable_start = None

for i in range(len(quarter_df)):
    sub = quarter_df.iloc[i:]
    if (sub["분기 차이"] >= 0).all():
        stable_start = quarter_df.iloc[i]["날짜"]
        break

st.subheader("📍 안정 시점")

if stable_start:
    st.success(f"👉 {stable_start}부터 안정 (배당 ≥ 생활비 유지)")
else:
    st.warning("❌ 안정 구간 없음")