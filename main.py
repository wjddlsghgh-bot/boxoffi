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


# 2. API 키 안전하게 가져오는 함수 (Secrets 에러 방지)
def get_api_key():
    # 1) Streamlit Secrets에서 키 찾기 시도
    try:
        if "KOBIS_KEY" in st.secrets and st.secrets["KOBIS_KEY"]:
            return st.secrets["KOBIS_KEY"]
    except Exception:
        # Secrets 파일이 아예 없거나 예외 발생 시 무시하고 다음 단계 진행
        pass

    # 2) 사이드바에서 사용자가 직접 입력할 수 있는 입력창 제공
    st.sidebar.subheader("🔑 KOBIS API 키 설정")
    user_key = st.sidebar.text_input(
        "KOBIS API 키를 입력하세요:",
        type="password",
        help="발급받은 키를 입력하시면 박스오피스 데이터를 불러옵니다.",
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

        # [오류 대응 1] 인증키 오류 등의 faultInfo 응답 처리
        if "faultInfo" in data:
            message = data["faultInfo"].get("message", "인증키가 유효하지 않습니다.")
            return None, f"API 오류 응답: {message}"

        box_office_result = data.get("boxOfficeResult", {})
        daily_list = box_office_result.get("dailyBoxOfficeList", [])

        # [오류 대응 2] 영화 목록이 빈 경우
        if not daily_list:
            return None, "영화 목록 데이터가 비어 있습니다."

        return daily_list, None

    except requests.exceptions.RequestException as e:
        return None, f"네트워크 요청 중 오류가 발생했습니다: {e}"


# --- 앱 메인 로직 실행 ---

# 1. API 키 취득
api_key = get_api_key()

# 2. 데이터 불러오기
movie_data, error_message = fetch_box_office(api_key)

# 3. 오류 또는 안내 메시지 처리
if error_message:
    if error_message == "NO_API_KEY":
        st.info("💡 **KOBIS API 인증키가 필요합니다.**")
        st.markdown(
            """
        **방법 1. 배포 환경(Streamlit Cloud) 등록**
        - Streamlit Cloud의 `App Settings > Secrets` 메뉴에 아래 형식으로 등록하세요.
        ```toml
        KOBIS_KEY = "발급받은_인증키"
        ```

        **방법 2. 화면 왼쪽 사이드바에서 직접 입력**
        - 왼쪽 사이드바의 입력창에 KOBIS API 키를 입력하시면 즉시 조회됩니다.
        """
        )
    else:
        st.error("⚠️ 데이터를 불러오지 못했습니다.")
        st.warning(f"**원인:** {error_message}")

        st.markdown("---")
        st.subheader("🛠️ 확인
