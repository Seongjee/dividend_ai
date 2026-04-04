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
is_mobile = st.sidebar.toggle("📱 모바일 모드", False)
st.sidebar.caption("👉 입력값은 내 기기에만 저장됩니다")

if st.sidebar.button("🔄 초기화"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("### 📱 화면 모드")

if is_mobile:
    st.caption("👉 모바일 최적화 화면")
else:
    st.caption("👉 PC 전체 화면")

st.sidebar.title("⚙️ 시뮬 설정")

use_live = st.sidebar.toggle("📡 실시간 데이터 사용", True)

# 👉 업데이트 시간 표시용
if "last_update" not in st.session_state:
    st.session_state.last_update = None


components.html(
    """
    <script>
    const inputs = window.parent.document.querySelectorAll('input');

    inputs.forEach(input => {
        const key = input.getAttribute('aria-label');

        // 불러오기
        if(localStorage.getItem(key)){
            input.value = localStorage.getItem(key);
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }

        // 저장
        input.addEventListener('change', () => {
            localStorage.setItem(key, input.value);
        });
    });
    </script>
    """,
    height=0
)

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

        st.session_state.last_update = datetime.now()

        st.sidebar.success("📡 실시간 반영됨")

    except Exception as e:
        st.sidebar.warning(f"⚠️ 일부 데이터 실패: {e}")

# =========================
# 입력 함수
# =========================
def input_int(label, key, default, step=1, disabled=False):
    if key not in st.session_state:
        st.session_state[key] = int(default)

    return st.sidebar.number_input(
        label,
        step=step,
        key=key,
        disabled=disabled,
        format="%d",
        value=int(st.session_state[key])
    )

def input_float(label, key, default, step=0.01, disabled=False):
    if key not in st.session_state:
        st.session_state[key] = float(default)

    return st.sidebar.number_input(
        label,
        step=float(step),              # 🔥 안전장치
        key=key,
        disabled=disabled,
        value=float(st.session_state[key])
    )

# =========================
# 입력창
# =========================
qqqi_qty = input_int("QQQI 수량", "qqqi_qty", 500)
schd_qty = input_int("SCHD 수량", "schd_qty", 5000)

qqqi_div = input_float("QQQI 월 배당 ($)", "qqqi_div", 0.61, 0.01, disabled=use_live)
schd_div = input_float("SCHD 분기 배당 ($)", "schd_div", 0.28, 0.01, disabled=use_live)
exchange_rate = input_float("환율", "exchange_rate", 1499.0, 1.0, disabled=use_live)
qqqi_price = input_float("QQQI 가격 ($)", "qqqi_price", 50.0, 0.01, disabled=use_live)

# =========================
# 🔥 현재값 표시 (핵심 추가)
# =========================
if use_live:
    st.sidebar.markdown("---")
    st.sidebar.markdown("📊 **현재 실시간 값**")

    #st.sidebar.write(f"QQQI 가격: ${st.session_state.qqqi_price:,.2f}")
    st.sidebar.write(f"QQQI 배당: ${st.session_state.qqqi_div:,.4f}")
    st.sidebar.write(f"SCHD 배당: ${st.session_state.schd_div:,.4f}")
    st.sidebar.write(f"환율: {st.session_state.exchange_rate:,.0f}원")
    st.sidebar.write(f"QQQI 가격: ${float(st.session_state.qqqi_price):,.2f}")

    if st.session_state.last_update:
        st.sidebar.caption(
            f"🕒 업데이트: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}"
        )

# =========================
# 나머지 설정
# =========================
tax_rate = st.sidebar.slider("세율 (%)", 0, 30, 15) / 100
growth_rate = st.sidebar.slider("SCHD 성장률 (%)", 0.0, 10.0, 5.0) / 100
qqqi_decay = st.sidebar.slider("QQQI 감소율 (%)", 0.0, 10.0, 3.0) / 100
inflation_rate = st.sidebar.slider("물가 상승률 (%)", 0.0, 5.0, 3.0) / 100

monthly_need_m = input_int("월 생활비 (백만원)", "monthly_need_m", 200)
monthly_need = monthly_need_m * 10000

years = st.sidebar.selectbox("시뮬 기간", [10, 20, 30])
months = years * 12

reinvest = st.sidebar.toggle("🔁 배당 재투자", True)
cash_years = st.sidebar.slider("💰 현금으로 버틸 기간 (년)", 0, 3, 1)

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
#st.title("💰 Dividend AI (QQQI + SCHD)")
#st.subheader("QQQI 월배당 + SCHD 분기배당 기반 현금흐름 시뮬레이션")

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
    # 💻 PC → 기존 그대로
    st.dataframe(styled, height=520)

else:
    # 📱 모바일 → 심플 + 핵심 유지
    # st.subheader("📱 모바일 요약")

    # 👉 핵심: 원화 + 달러 둘 다 유지
    mobile_df = df[
        [
            "날짜",
            "QQQI", #"QQQI($)",
            "SCHD", #"SCHD($)",
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

# ✅ 1️⃣ 날짜 타입 변환 (🔥 핵심)
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
    marker_color=colors,
    opacity=0.5,
    hovertemplate="%{y:,.0f}원"
))

# ✅ 2️⃣ Y축 백만원 단위 (🔥 핵심)
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