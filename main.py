<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>일별 박스오피스 조회</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 30px;
      background-color: #f8f9fa;
    }
    h1 {
      color: #333;
    }
    .controls {
      margin-bottom: 20px;
    }
    label {
      font-weight: bold;
      margin-right: 10px;
    }
    input[type="date"] {
      padding: 6px 10px;
      font-size: 14px;
      border: 1px solid #ccc;
      border-radius: 4px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background-color: #fff;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    th, td {
      border: 1px solid #dee2e6;
      padding: 12px;
      text-align: center;
    }
    th {
      background-color: #343a40;
      color: #fff;
    }
    tr:nth-child(even) {
      background-color: #f2f2f2;
    }
    .rank-up {
      color: #e74c3c;
      font-weight: bold;
    }
    .rank-down {
      color: #2980b9;
      font-weight: bold;
    }
    .rank-same {
      color: #7f8c8d;
    }
    .movie-title {
      text-align: left;
    }
    #message {
      margin-top: 20px;
      font-size: 16px;
      color: #e74c3c;
      font-weight: bold;
    }
  </style>
</head>
<body>

  <h1>🎬 일별 박스오피스</h1>

  <div class="controls">
    <label for="targetDate">날짜 선택:</label>
    <input type="date" id="targetDate">
  </div>

  <table id="boxOfficeTable">
    <thead>
      <tr>
        <th>순위</th>
        <th>변동</th>
        <th>영화명</th>
        <th>개봉일</th>
        <th>당일 관객수</th>
        <th>누적 관객수</th>
      </tr>
    </thead>
    <tbody id="boxOfficeList">
      <!-- 데이터가 여기에 동적으로 추가됩니다 -->
    </tbody>
  </table>

  <div id="message"></div>

  <script>
    // 본인의 Kobis API 키를 입력하세요.
    const API_KEY = 'YOUR_API_KEY';

    // 어제 날짜 계산 (YYYY-MM-DD 형식)
    function getYesterdayString() {
      const today = new Date();
      today.setDate(today.getDate() - 1);
      const year = today.getFullYear();
      const month = String(today.getMonth() + 1).padStart(2, '0');
      const day = String(today.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }

    // 날짜 선택 input 기본값 및 max값 설정
    const dateInput = document.getElementById('targetDate');
    const yesterday = getYesterdayString();
    
    dateInput.max = yesterday; // 오늘 및 미래 날짜 선택 불가
    dateInput.value = yesterday; // 기본 선택값: 어제

    // 박스오피스 데이터 불러오기 함수
    async function fetchBoxOffice(selectedDate) {
      // YYYY-MM-DD -> YYYYMMDD 변환
      const targetDt = selectedDate.replace(/-/g, '');
      const url = `http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key=${API_KEY}&targetDt=${targetDt}`;

      const tbody = document.getElementById('boxOfficeList');
      const messageDiv = document.getElementById('message');
      
      tbody.innerHTML = '';
      messageDiv.textContent = '';

      try {
        const response = await fetch(url);
        const data = await response.json();
        const dailyBoxOfficeList = data.boxOfficeResult?.dailyBoxOfficeList;

        // 영화 목록이 없거나 비어있는 경우
        if (!dailyBoxOfficeList || dailyBoxOfficeList.length === 0) {
          messageDiv.textContent = '그날은 아직 집계 전입니다.';
          return;
        }

        // 목록 출력
        dailyBoxOfficeList.forEach(item => {
          const rankInten = parseInt(item.rankInten, 10);
          const audiAcc = parseInt(item.audiAcc, 10);

          // 1. 순위 변동 표시 로직
          let rankChangeHtml = '<span class="rank-same">-</span>';
          if (rankInten > 0) {
            rankChangeHtml = `<span class="rank-up">▲ ${rankInten}</span>`;
          } else if (rankInten < 0) {
            rankChangeHtml = `<span class="rank-down">▼ ${Math.abs(rankInten)}</span>`;
          }

          // 2. 누적관객 100만 이상 트로피 로직
          let movieName = item.movieNm;
          if (audiAcc >= 1000000) {
            movieName += ' 🏆';
          }

          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${item.rank}</td>
            <td>${rankChangeHtml}</td>
            <td class="movie-title">${movieName}</td>
            <td>${item.openDt || '-'}</td>
            <td>${Number(item.audiCnt).toLocaleString()}명</td>
            <td>${audiAcc.toLocaleString()}명</td>
          `;
          tbody.appendChild(tr);
        });

      } catch (error) {
        console.error('데이터를 불러오는 중 오류 발생:', error);
        messageDiv.textContent = '데이터를 불러오는 중 오류가 발생했습니다.';
      }
    }

    // 초기 화면 로딩 시 어제 박스오피스 조회
    fetchBoxOffice(dateInput.value);

    // 날짜 선택 변경 시 자동 재조회
    dateInput.addEventListener('change', (e) => {
      fetchBoxOffice(e.target.value);
    });
  </script>
</body>
</html>
