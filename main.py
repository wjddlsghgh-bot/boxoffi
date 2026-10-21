import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# Streamlit 페이지 기본 설정
st.set_page_config(
    page_title="어제의 박스오피스", page_icon="🎬", layout="wide"
)

st.title("🎬 어제 일별 박스오피스 순위")


# 1. 한국 시간(KST) 기준 '어제' 날짜 계산 함수
def get_yesterday_kst():
    # 배포 서버의 시계와 무관하게 한국 시간(Asia/Seoul)을 가져옵니다.
    kst_tz = pytz.timezone("Asia/Seoul")
    now_kst = datetime.datetime.now(kst_tz)
    yesterday_kst = now_kst - datetime.timedelta(days=1)
    return yesterday_kst.strftime("%Y%m%d")


# 2. API 키 안전하게 가져오기 (Secrets 예외 완벽 방지)
def get_api_key():
    api_key = None

    # Streamlit Secrets 읽기 시도 (오류 발생 시 무시)
    try:
        if hasattr(st, "secrets") and "KOBIS_KEY" in st.secrets:
            api_key = st.secrets["KOBIS_KEY"]
    except Exception:
        api_key = None

    # 사이드바 입력창 제공 (Secrets에 키가 없는 경우)
    st.sidebar.subheader("🔑 KOBIS API 키 설정")
    user_key = st.sidebar.text_input(
        "KOBIS API 키를 입력하세요:",
        value=api_key if api_key else "",
        type="password",
        help="발급받은 KOBIS API 키를 입력하면 바로 조회됩니다.",
    )

    return user_key


# 3. KOBIS API 데이터 호출 함수
@st.cache_data(ttl=3600)
def fetch_box_office(api_key):
    if not api_key:
        return None, "NO_API_KEY"

    target_dt = get_yesterday_kst()
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_dt}

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None, f"HTTP 오류 발생 (상태 코드: {response.status_code})"

        data = response.json()

        # [오류 대응 1] KOBIS API 오류 응답 (faultInfo)
        if "faultInfo" in data:
            message = data["faultInfo"].get("message", "인증키가 유효하지 않습니다.")
            return None, f"API 오류 응답: {message}"

        box_office_result = data.get("boxOfficeResult", {})
        daily_list = box_office_result.get("dailyBoxOfficeList", [])

        # [오류 대응 2] 데이터가 비어있는 경우
        if not daily_list:
            return None, "영화 목록 데이터가 비어 있습니다."

        return daily_list, None

    except requests.exceptions.RequestException as e:
        return None, f"네트워크 요청 중 오류가 발생했습니다: {e}"


# --- 메인 실행 로직 ---

# 1. API 키 가져오기
api_key = get_api_key()

# 2. 데이터 불러오기
movie_data, error_message = fetch_box_office(api_key)

# 3. 화면 출력 및 처리
if error_message:
    if error_message == "NO_API_KEY":
        st.info("💡 **KOBIS API 키를 설정해 주세요.**")
        st.markdown(
            """
        ### 📌 해결 방법 (2가지 중 하나 선택)

        **1. 화면 왼쪽 사이드바에서 키 입력하기 (가장 쉬운 방법)**
        - 왼쪽 사이드바(‘🔑 KOBIS API 키 설정’) 입력창에 발급받은 API 키를 넣으시면 바로 작동합니다.

        **2. Streamlit Cloud에 Secrets 등록하기**
        - Streamlit Cloud 앱 관리 화면에서 **App Settings > Secrets** 메뉴에 이동합니다.
        - 아래 내용을 입력하고 Save를 눌러주세요:
          ```toml
          KOBIS_KEY = "발급받은_인증키_입력"
          ```
        """
        )
    else:
        st.error("⚠️ 데이터를 불러오지 못했습니다.")
        st.warning(f"**원인:** {error_message}")

        st.markdown("---")
        st.subheader("🛠️ 확인 및 조치 사항")
        st.write("1. 입력하신 **KOBIS API 인증키**가 올바른지 확인해 주세요.")
        st.write("2. 영화진흥위원회 API 서버 상태를 확인해 주세요.")
else:
    # 4. 정상 작동 시 표 및 차트 출력
    df = pd.DataFrame(movie_data)

    df["rank"] = df["rank"].astype(int)
    df["audiCnt"] = df["audiCnt"].astype(int)
    df["audiAcc"] = df["audiAcc"].astype(int)
    df["scrnCnt"] = df["scrnCnt"].astype(int)

    top_movie = df.iloc[0]

    # 1위 영화 지표 카드 (Metric) 3장
    st.subheader(f"🥇 어제 박스오피스 1위: {top_movie['movieNm']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="일일 관객수", value=f"{top_movie['audiCnt']:,} 명")
    with col2:
        st.metric(label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명")
    with col3:
        st.metric(label="스크린 수", value=f"{top_movie['scrnCnt']:,} 개")

    st.markdown("---")

    # 관객수 상위 5편 막대그래프
    st.subheader("📊 관객수 상위 5개 영화")
    top5_df = df.head(5)[["movieNm", "audiCnt"]].copy()
    top5_df = top5_df.rename(columns={"movieNm": "영화명", "audiCnt": "어제 관객수"})
    top5_df = top5_df.set_index("영화명")
    st.bar_chart(top5_df)

    st.markdown("---")

    # 전체 박스오피스 순위 표
    st.subheader("📋 전체 박스오피스 순위")

    display_df = df[
        ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()
    display_df.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

    st.dataframe(
        display_df.style.format(
            {"관객수": "{:,}", "누적관객": "{:,}", "스크린수": "{:,}"}
        ),
        use_container_width=True,
        hide_index=True,
    )
