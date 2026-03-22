import streamlit as st

st.set_page_config(page_title="배당 계산기", layout="centered")

st.title("💰 배당 계산기")

# -------------------------------
# ✅ 초기값
# -------------------------------
if "qqqi" not in st.session_state:
    st.session_state.qqqi = 500

if "schd" not in st.session_state:
    st.session_state.schd = 5000

# 배당 (연간, 달러 기준)
QQQI_DIV = 1.6
SCHD_DIV = 2.6

# 환율
USD_KRW = 1350

# 세율
TAX_RATE = 0.15


# -------------------------------
# ✅ QQQI
# -------------------------------
st.subheader("QQQI")

col1, col2 = st.columns([2, 1])

with col1:
    st.session_state.qqqi = st.number_input(
        "QQQI 수량",
        min_value=0,
        step=100,
        value=st.session_state.qqqi,
        key="qqqi_input"
    )

with col2:
    if st.button("+100", key="qqqi_plus"):
        st.session_state.qqqi += 100
    if st.button("-100", key="qqqi_minus"):
        st.session_state.qqqi -= 100


# -------------------------------
# ✅ SCHD
# -------------------------------
st.subheader("SCHD")

col1, col2 = st.columns([2, 1])

with col1:
    st.session_state.schd = st.number_input(
        "SCHD 수량",
        min_value=0,
        step=100,
        value=st.session_state.schd,
        key="schd_input"
    )

with col2:
    if st.button("+100", key="schd_plus"):
        st.session_state.schd += 100
    if st.button("-100", key="schd_minus"):
        st.session_state.schd -= 100


# -------------------------------
# ✅ 배당 계산
# -------------------------------
st.divider()
st.subheader("📊 예상 배당")

# 세전
qqqi_annual = st.session_state.qqqi * QQQI_DIV
schd_annual = st.session_state.schd * SCHD_DIV

total_annual_usd = qqqi_annual + schd_annual
monthly_usd = total_annual_usd / 12

# 세후
after_tax_annual_usd = total_annual_usd * (1 - TAX_RATE)
after_tax_monthly_usd = after_tax_annual_usd / 12

# 원화 변환
monthly_krw_before = monthly_usd * USD_KRW
monthly_krw_after = after_tax_monthly_usd * USD_KRW


# -------------------------------
# ✅ 결과 출력
# -------------------------------
st.write("### 💵 세전")
st.write(f"월 배당 (USD): ${monthly_usd:,.2f}")
st.write(f"월 배당 (KRW): {monthly_krw_before:,.0f} 원")

st.write("### 💰 세후 (15%)")
st.write(f"월 배당 (USD): ${after_tax_monthly_usd:,.2f}")
st.write(f"월 배당 (KRW): {monthly_krw_after:,.0f} 원")


# -------------------------------
# ✅ 참고
# -------------------------------
st.caption("※ 배당금 / 환율은 임의 값 (추후 API 연동 가능)")