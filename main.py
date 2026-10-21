import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# Streamlit 페이지 기본 설정 (제목, 레이아웃)
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
    # yyyymmdd 8자리 문자열 형식으로 반환
    return yesterday_kst.strftime("%Y%m%d")


# 2. KOBIS API 데이터 호출 함수
@st.cache_data(ttl=3600)  # 1시간 동안 응답 데이터를 저장(캐싱)하여 API 호출 수를 줄입니다.
def fetch_box_office():
    # Streamlit Secrets(비밀 금고)에서 KOBIS_KEY 가져오기
    if "KOBIS_KEY" not in st.secrets:
        return None, "SECRETS_NOT_FOUND"

    api_key = st.secrets["KOBIS_KEY"]
    target_dt = get_yesterday_kst()

    # KOBIS 일별 박스오피스 공식 API 요청 주소
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_dt}

    try:
        # API 요청 보내기
        response = requests.get(url, params=params, timeout=10)

        # HTTP 요청 자체가 실패한 경우
        if response.status_code != 200:
            return None, f"HTTP 오류 발생 (상태 코드: {response.status_code})"

        data = response.json()

        # [오류 대응 1] 인증키 오류 등으로 'faultInfo' 응답이 돌아온 경우
        if "faultInfo" in data:
            message = data["faultInfo"].get("message", "알 수 없는 API 오류")
            return None, f"API 오류 응답: {message}"

        # [오류 대응 2] 정상 응답 내부의 영화 데이터 확인
        box_office_result = data.get("boxOfficeResult", {})
        daily_list = box_office_result.get("dailyBoxOfficeList", [])

        # 영화 목록이 비어있는 경우
        if not daily_list:
            return None, "영화 목록 데이터가 비어 있습니다."

        return daily_list, None

    except requests.exceptions.RequestException as e:
        return None, f"네트워크 요청 중 오류가 발생했습니다: {e}"


# 데이터 불러오기 실행
movie_data, error_message = fetch_box_office()

# 3. 오류 발생 시 안내 화면 출력
if error_message:
    st.error("⚠️ 데이터를 불러오지 못했습니다.")
    st.warning(f"**원인:** {error_message}")

    st.markdown("---")
    st.subheader("🛠️ 확인 및 조치 사항")
    if error_message == "SECRETS_NOT_FOUND":
        st.write(
            "1. Streamlit Cloud 설정(Settings > Secrets)에 `KOBIS_KEY = \"발급받은키\"` 형태로 비밀키가 등록되어 있는지 확인해 주세요."
        )
        st.write("2. 로컬 환경이라면 `.streamlit/secrets.toml` 파일이 작성되어 있는지 확인해 주세요.")
    else:
        st.write("1. 발급받은 KOBIS API 인증키가 올바른지 확인해 주세요.")
        st.write("2. 영화진흥위원회 API 서버에 일시적인 장애가 없는지 확인해 주세요.")
        st.write("3. 인터넷 연결 상태를 확인해 주세요.")

else:
    # 4. 데이터 가공 (문자열 -> 숫자 변환 및 정제)
    df = pd.DataFrame(movie_data)

    # API 결과의 문자열 데이터를 숫자형(int)으로 변환
    df["rank"] = df["rank"].astype(int)
    df["audiCnt"] = df["audiCnt"].astype(int)
    df["audiAcc"] = df["audiAcc"].astype(int)
    df["scrnCnt"] = df["scrnCnt"].astype(int)

    # 1위 영화 정보 추출
    top_movie = df.iloc[0]

    # 5. 1위 영화 지표 카드 (Metric) 3장 표시
    st.subheader(f"🥇 어제 박스오피스 1위: {top_movie['movieNm']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="일일 관객수", value=f"{top_movie['audiCnt']:,} 명"
        )
    with col2:
        st.metric(
            label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명"
        )
    with col3:
        st.metric(
            label="스크린 수", value=f"{top_movie['scrnCnt']:,} 개"
        )

    st.markdown("---")

    # 6. 관객수 상위 5편 막대그래프 시각화
    st.subheader("📊 관객수 상위 5개 영화")
    top5_df = df.head(5)[["movieNm", "audiCnt"]].copy()
    top5_df = top5_df.rename(
        columns={"movieNm": "영화명", "audiCnt": "어제 관객수"}
    )

    # Streamlit 차트 출력을 위해 영화명을 인덱스로 지정
    top5_df = top5_df.set_index("영화명")
    st.bar_chart(top5_df)

    st.markdown("---")

    # 7. 박스오피스 전체 순위 표 출력
    st.subheader("📋 전체 박스오피스 순위")

    # 표에 출력할 컬럼만 추출하고 이름 변경
    display_df = df[
        ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()
    display_df.columns = [
        "순위",
        "영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수",
    ]

    # Streamlit 데이터프레임 표시 (숫자 천 단위 쉼표 서식 적용)
    st.dataframe(
        display_df.style.format(
            {"관객수": "{:,}", "누적관객": "{:,}", "스크린수": "{:,}"}
        ),
        use_container_width=True,
        hide_index=True,
    )
