import datetime
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="어제의 박스오피스", page_icon="🎬", layout="wide")

API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

# 1. 날짜 설정: 한국 시간(UTC+9) 기준 어제까지로 고정
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
yesterday = today_kst - datetime.timedelta(days=1)

st.title("🎬 일별 박스오피스")
st.caption("달력에서 날짜를 선택하세요. 가장 늦게 선택할 수 있는 날짜는 한국 시간 기준 어제입니다.")

selected_date = st.date_input(
    "조회 날짜",
    value=yesterday,
    min_value=datetime.date(2004, 1, 1),
    max_value=yesterday,  # 오늘 이후 날짜는 선택 불가
    format="YYYY/MM/DD"
)
target_dt = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

# 2. 인증키 처리
try:
    API_KEY = st.secrets["KOBIS_KEY"]
except Exception:
    st.error("🔐 KOBIS 인증키를 찾을 수 없습니다.")
    st.markdown("Streamlit Cloud의 **Settings → Secrets**에 `KOBIS_KEY`가 등록되어 있는지 확인하세요.")
    st.code('KOBIS_KEY = "발급받은_인증키"', language="toml")
    st.stop()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boxoffice(date_text, api_key):
    response = requests.get(
        API_URL,
        params={"key": api_key, "targetDt": date_text},
        timeout=20
    )
    response.raise_for_status()
    return response.json()


try:
    with st.spinner("KOBIS에서 데이터를 불러오는 중입니다..."):
        data = fetch_boxoffice(target_dt, str(API_KEY).strip())
except requests.exceptions.RequestException as error:
    st.error("🌐 KOBIS 서버에 연결하지 못했습니다.")
    st.write(f"오류 내용: {error}")
    st.stop()
except Exception as error:
    st.error("예상하지 못한 문제가 발생했습니다.")
    st.write(f"오류 내용: {error}")
    st.stop()

# 3. KOBIS 응답 예외 처리
if "faultInfo" in data:
    fault = data.get("faultInfo", {})
    st.error(f"🚨 KOBIS API 오류: {fault.get('message', '오류 발생')}")
    st.stop()

boxoffice_result = data.get("boxOfficeResult", {})
movies = boxoffice_result.get("dailyBoxOfficeList", [])

# 영화 목록이 비어있는 경우 (집계 전 처리)
if not movies:
    st.warning("📭 그날은 아직 집계 전입니다.")
    st.info("KOBIS에서 해당 날짜의 박스오피스 집계를 완료했는지 확인해 주세요.")
    st.stop()

df = pd.DataFrame(movies)

# 숫자 데이터 변환
for column in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]:
    df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)

df["movieNm"] = df["movieNm"].fillna("영화명 없음").astype(str)
df["openDt"] = df["openDt"].fillna("-").replace("", "-").astype(str)

# 4. 누적 관객수 100만 명 이상 트로피 🏆 표시 (>= 1,000,000 이상)
df["표시 영화명"] = df.apply(
    lambda row: f"{row['movieNm']} 🏆" if row["audiAcc"] >= 1_000_000 else row["movieNm"],
    axis=1
)

# 5. 전일 대비 순위 변동 (양수: 빨간 위 화살표 ▲, 음수: 파란 아래 화살표 ▼)
def format_rank_change(value):
    if value > 0:
        return f"▲ {value}"
    if value < 0:
        return f"▼ {abs(value)}"
    return "-"

df["순위 변동"] = df["rankInten"].map(format_rank_change)
df = df.sort_values("rank").reset_index(drop=True)

# 1위 영화 지표
first = df.iloc[0]
st.subheader(f"🥇 {display_date} 1위 — {first['표시 영화명']}")
c1, c2, c3 = st.columns(3)
c1.metric("관객수", f"{first['audiCnt']:,}명")
c2.metric("누적 관객수", f"{first['audiAcc']:,}명")
c3.metric("스크린수", f"{first['scrnCnt']:,}개")

# 순위 표 출력
st.subheader("📋 박스오피스 순위")
table = df[["rank", "순위 변동", "표시 영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
table.columns = ["순위", "전일 대비", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

for column in ["관객수", "누적관객", "스크린수"]:
    table[column] = table[column].map(lambda value: f"{value:,}")

def color_rank_change(value):
    if isinstance(value, str) and value.startswith("▲"):
        return "color: #e53935; font-weight: bold;"
    if isinstance(value, str) and value.startswith("▼"):
        return "color: #1976d2; font-weight: bold;"
    return "color: #777777;"

st.dataframe(
    table.style.map(color_rank_change, subset=["전일 대비"]),
    hide_index=True,
    use_container_width=True
)

# 상위 5편 막대그래프
st.subheader("📊 관객수 상위 5편")
top5 = df.nlargest(5, "audiCnt").sort_values("audiCnt", ascending=True)
chart = px.bar(
    top5,
    x="audiCnt",
    y="표시 영화명",
    orientation="h",
    labels={"audiCnt": "관객수(명)", "표시 영화명": "영화명"},
    text="audiCnt"
)
chart.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
chart.update_layout(
    yaxis_title="",
    xaxis_title="관객수(명)",
    margin=dict(l=10, r=40, t=20, b=10)
)
st.plotly_chart(chart, use_container_width=True)

st.caption("데이터 출처: 영화관입장권통합전산망(KOBIS) 일별 박스오피스 API")
