from flask import Flask, request, render_template, redirect, url_for, flash
import os
from databricks import sql
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

def run_query(query, params=None):
    with sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
    ) as connection:
        with connection.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=columns)
    return df

# 위험도 숫자 → 텍스트 변환 함수
def risk_label(risk):
    risk_map = {
        1: "1 (매우 공격적)",
        2: "2",
        3: "3",
        4: "4",
        5: "5",
        6: "6 (매우 안정적)"
    }
    return risk_map.get(int(risk), str(risk)) if risk else None

# 클러스터별 기본 필터 조건
customer_consumption_cluster_fund_conditions = {
    # Cluster 0: 핵심 활성 고객 (VIP, 활동성 높은 고객)
    (0, 0): {
        # [근거] VIP+소극적. 저위험, 안정형, MDD로 손실 제한.
        # "fund_tags.배당주": (">", 0.5),
        # "fund_tags.절대수익추구": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.05),
        "fund_performance.펀드수정샤프연환산_1년": (">", 1.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),  # 필수
        # "fund_performance.MaximumDrawDown_1년": ("<", -5),  # 안정성 강조
    },
    (0, 1): {
        # [근거] VIP+활동성. 성장/글로벌, MDD로 중위험 허용.
        # "fund_tags.글로벌": (">", 0.5),
        # "fund_tags.성장주": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.05),
        "fund_performance.펀드수정샤프연환산_1년": (">", 1.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -5),
    },
    (0, 2): {
        # [근거] 실속형 소비+VIP. 중소형주, 무수수료, 위험등급 필수.
        "fund_tags.중소형주": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.03),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 4),
        "fund_performance.MaximumDrawDown_1년": ("<", -7),  # 공격적 투자자용
    },
    (0, 3): {
        # [근거] 가족/장기고객+VIP. 자산배분/ESG, 보수적 MDD.
        # "fund_tags.자산배분": (">", 0.5),
        "fund_performance.펀드수정샤프연환산_1년": (">", 0.8),
        "fund_risk_grades.투자위험등급": ("<=", 2),
        "fund_performance.MaximumDrawDown_1년": ("<", -4),
    },
    (0, 4): {
        # [근거] 젊은/트렌드 소비+VIP. 성장주/중소형주, 위험등급 필수, MDD 완화.
        # "fund_tags.중소형주": (">", 0.5),
        "fund_tags.성장주": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.02),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -6),
    },

    # Cluster 1: 휴면/저관여 고객
    (1, 0): {
        "fund_tags.배당주": (">", 0.5),
        "fund_tags.절대수익추구": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.03),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_performance.MaximumDrawDown_1년": ("<", -3),
        "fund_risk_grades.투자위험등급": ("<=", 3),
    },
    (1, 1): {
        "fund_tags.배당주": (">", 0.5),
        "fund_tags.절대수익추구": (">", 0.5),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -3),
        "fund_fees.선취수수료": ("==", 0.0),
    },
    (1, 2): {
        "fund_tags.중소형주": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.03),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 4),
        "fund_performance.MaximumDrawDown_1년": ("<", -7),
    },
    (1, 3): {
        "fund_tags.자산배분": (">", 0.5),
        "fund_tags.ESG(사회책임투자형)": (">", 0.5),
        "fund_tags.배당주": (">", 0.5),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 2),
        "fund_performance.MaximumDrawDown_1년": ("<", -4),
    },
    (1, 4): {
        "fund_tags.중소형주": (">", 0.5),
        "fund_tags.성장주": (">", 0.5),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -6),
    },

    # Cluster 2: 금융 서비스 중심 고객
    (2, 0): {
        "fund_tags.배당주": (">", 0.5),
        "fund_tags.절대수익추구": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.03),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -5),
    },
    (2, 1): {
        "fund_tags.절대수익추구": (">", 0.5),
        "fund_tags.글로벌": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.03),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -5),
    },
    (2, 2): {
        "fund_tags.중소형주": (">", 0.5),
        "fund_tags.절대수익추구": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.03),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 4),
        "fund_performance.MaximumDrawDown_1년": ("<", -7),
    },
    (2, 3): {
        "fund_tags.자산배분": (">", 0.5),
        "fund_tags.ESG(사회책임투자형)": (">", 0.5),
        "fund_performance.펀드수정샤프연환산_1년": (">", 0.8),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 2),
        "fund_performance.MaximumDrawDown_1년": ("<", -4),
    },
    (2, 4): {
        "fund_tags.글로벌": (">", 0.5),
        "fund_tags.성장주": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.02),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -6),
    },

    # Cluster 3: 일반/평균 고객
    (3, 0): {
        "fund_tags.배당주": (">", 0.5),
        "fund_tags.자산배분": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.02),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -5),
    },
    (3, 1): {
        "fund_tags.자산배분": (">", 0.5),
        "fund_tags.글로벌": (">", 0.5),
        "fund_tags.성장주": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.02),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -5),
    },
    (3, 2): {
        "fund_tags.중소형주": (">", 0.5),
        "fund_tags.자산배분": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.02),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 4),
        "fund_performance.MaximumDrawDown_1년": ("<", -8),
    },
    (3, 3): {
        "fund_tags.자산배분": (">", 0.5),
        "fund_tags.ESG(사회책임투자형)": (">", 0.5),
        "fund_tags.배당주": (">", 0.5),
        "fund_performance.펀드성과정보_3년": (">", 0.02),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 2),
        "fund_performance.MaximumDrawDown_1년": ("<", -4),
    },
    (3, 4): {
        "fund_tags.중소형주": (">", 0.5),
        "fund_tags.성장주": (">", 0.5),
        "fund_performance.펀드성과정보_1년": (">", 0.02),
        "fund_fees.선취수수료": ("==", 0.0),
        "fund_risk_grades.투자위험등급": ("<=", 3),
        "fund_performance.MaximumDrawDown_1년": ("<", -6),
    },
}




# 테마 키워드
theme_keywords = ['가치주', '성장주', '중소형주', '글로벌', '자산배분', '4차산업', 'ESG',
                  '배당주', 'FoFs', '퇴직연금', '고난도금융상품', '절대수익추구', '레버리지', '퀀트']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        # 1. 회원코드 입력이 있으면 클러스터 값 조회
        member_code = request.form.get('member_code')
        customer_cluster_value = None  # 고객 클러스터
        consumption_cluster_value = None  # 소비 클러스터
        preselected_themes = []
        preselected_risk = None
        cluster_cond = {}
        applied_filters = {}

        # [핵심] 적용할 필드명 리스트 (SQL 매핑)
        filter_fields = {
            "fund_tags.배당주": "t.`배당주`",
            "fund_tags.절대수익추구": "t.`절대수익추구`",
            "fund_tags.글로벌": "t.`글로벌`",
            "fund_tags.성장주": "t.`성장주`",
            "fund_tags.중소형주": "t.`중소형주`",
            "fund_tags.자산배분": "t.`자산배분`",
            "fund_tags.ESG(사회책임투자형)": "t.`ESG(사회책임투자형)`",

            "fund_performance.펀드성과정보_1년": "p.`펀드성과정보_1년`",
            "fund_performance.펀드성과정보_3년": "p.`펀드성과정보_3년`",
            "fund_performance.펀드수정샤프연환산_1년": "p.`펀드수정샤프연환산_1년`",
            "fund_performance.MaximumDrawDown_1년": "p.`MaximumDrawDown_1년`",

            "fund_risk_grades.투자위험등급": "r.`투자위험등급`",
            "fund_fees.선취수수료": "f.`선취수수료`"
        }


        # 1-1. 회원코드로 고객/소비 클러스터 조회
        if member_code:
            # 소비 클러스터 조회
            q1 = "SELECT cluster FROM database_pjt.df_final_with_cluster WHERE `발급회원번호` = ?"
            df1 = run_query(q1, params=(member_code,))
            if not df1.empty:
                consumption_cluster_value = int(df1.iloc[0]['cluster'])

            # 고객 클러스터 조회
            q2 = "SELECT prediction FROM database_pjt.customer_clusters_final WHERE `발급회원번호` = ?"
            df2 = run_query(q2, params=(member_code,))
            if not df2.empty:
                customer_cluster_value = int(df2.iloc[0]['prediction'])

            # 둘 다 없으면 메시지 후 홈으로 리다이렉트
            if consumption_cluster_value is None and customer_cluster_value is None:
                flash('존재하지않는 회원번호입니다.')
                return redirect(url_for('home'))

            # 하나라도 없으면 0으로 대체
            if consumption_cluster_value is None:
                consumption_cluster_value = 0
            if customer_cluster_value is None:
                customer_cluster_value = 0

            # 클러스터 조합별 조건 추출
            cluster_key = (customer_cluster_value, consumption_cluster_value)
            cluster_cond = customer_consumption_cluster_fund_conditions.get(cluster_key, {})
            for key, (op, val) in cluster_cond.items():
                for theme in theme_keywords:
                    if theme in key and op == ">" and val >= 0.5:
                        preselected_themes.append(theme)
                if '투자위험등급' in key and op in ("<=", "<"):
                    preselected_risk = val

        # 2. 폼에서 직접 입력된 값이 있으면 우선 적용
        occupation = request.form.get('occupation')
        risk_preference = request.form.get('risk')
        themes = request.form.getlist('theme')
        keyword = request.form.get('search_query', '')
        sort_option = request.form.get('sort_option', '추천랭킹')

        # 위험선호도: 클러스터에서 가져온 값이 있으면 우선 적용
        if preselected_risk is not None:
            risk_preference = preselected_risk
        elif risk_preference is not None:
            risk_preference = int(risk_preference)

        # 테마: 클러스터에서 가져온 값이 있으면 우선 적용
        if preselected_themes:
            themes = preselected_themes

        # 정렬 옵션
        sort_columns = {
            '추천랭킹': 'k.`추천랭킹`',
            '위험등급': 'r.`투자위험등급`'
        }
        sort_column = sort_columns.get(sort_option, 'k.`추천랭킹`')

        # 3. 쿼리 생성 (기본: 위험등급 이하, 테마, 키워드, 정렬)
        query = '''
        SELECT i.`펀드코드`, i.`펀드명`, r.`투자위험등급`, f.`운용보수`, p.`펀드성과정보_1년`, k.`추천랭킹`, i.`운용사명`,
               t.`가치주`, t.`성장주`, t.`중소형주`, t.`글로벌`, t.`자산배분`, t.`4차산업`, t.`ESG`, t.`배당주`, t.`FoFs`, t.`퇴직연금`,
               t.`고난도금융상품`, t.`절대수익추구`, t.`레버리지`, t.`퀀트`, k.`최종점수`, k.`추천랭킹`, p.`펀드수정샤프연환산_1년`, f.`선취수수료`, p.`MaximumDrawDown_1년`, f.`판매보수`
        FROM funds_data.funds_info i
        JOIN funds_data.fund_risk_grades r ON i.`펀드코드` = r.`펀드코드`
        JOIN funds_data.fund_performance p ON i.`펀드코드` = p.`펀드코드`
        JOIN funds_data.fund_rank k ON i.`펀드코드` = k.`펀드코드`
        JOIN funds_data.fund_fees f ON i.`펀드코드` = f.`펀드코드`
        JOIN funds_data.fund_tags t ON i.`펀드코드` = t.`펀드코드`
        WHERE 1=1
        '''
        params = []

        # 4. 클러스터 필터 동적 쿼리 추가
        if cluster_cond:
            for key, (op, val) in cluster_cond.items():
                # 테마(태그)는 쿼리 필터로 넣지 않고, preselected_themes에만 추가
                if key.startswith("fund_tags."):
                    for theme in theme_keywords:
                        if theme in key and op == ">" and val >= 0.5:
                            preselected_themes.append(theme)
                    continue  # 쿼리에는 추가하지 않음

                # 성과, 위험, 수수료 등만 쿼리 필터로 추가
                if key in filter_fields:
                    if key == "fund_risk_grades.투자위험등급":
                        applied_filters[label_map.get(key, key)] = f"{op} {val}"
                        continue  # 쿼리에는 추가하지 않음
                    sql_field = filter_fields[key]
                    if op == "==":
                        query += f" AND {sql_field} = ?"
                    else:
                        query += f" AND {sql_field} {op} ?"
                    params.append(val)
                        # 화면 표시용 라벨
                    label_map = {
                        "fund_tags.배당주": "배당주",
                        "fund_tags.절대수익추구": "절대수익추구",
                        "fund_tags.중소형주": "중소형주",
                        "fund_tags.글로벌": "글로벌",
                        "fund_tags.성장주": "성장주",
                        "fund_tags.ESG(사회책임투자형)": "ESG",
                        "fund_performance.펀드성과정보_1년": "펀드성과정보_1년",
                        "fund_performance.펀드성과정보_3년": "펀드성과정보_3년",
                        "fund_performance.펀드수정샤프연환산_1년": "펀드수정샤프연환산_1년",
                        "fund_performance.MaximumDrawDown_1년": "MaximumDrawDown_1년",
                        "fund_risk_grades.투자위험등급": "투자위험등급",
                        "fund_fees.선취수수료": "선취수수료"
                    }

                    applied_filters[label_map.get(key, key)] = f"{op} {val}"

        # 키워드(펀드명) 필터
        if keyword:
            query += " AND i.`펀드명` LIKE ?"
            params.append(f'%{keyword}%')

        query += f" ORDER BY {sort_column}"
        df = run_query(query, params)
        funds = df.to_dict(orient='records')

        risk_text = risk_label(risk_preference) if risk_preference else None

        return render_template(
            'result.html',
            funds=funds,
            preselected_themes=themes,
            preselected_risk=risk_preference,
            risk_text=risk_text,
            theme_keywords=theme_keywords,
            applied_filters=applied_filters,
            customer_cluster_value=customer_cluster_value,
            consumption_cluster_value=consumption_cluster_value
        )

    except Exception as e:
        app.logger.error(f"Error in recommend(): {e}")
        return "추천 결과 처리 중 오류가 발생했습니다.", 500


@app.route('/fund/<code>')
def fund_detail(code):
    fund = run_query('SELECT * FROM funds_data.funds_info WHERE `펀드코드` = ?', (code,))
    types = run_query('SELECT * FROM funds_data.fund_types WHERE `펀드코드` = ?', (code,))
    perf = run_query('SELECT * FROM funds_data.fund_performance WHERE `펀드코드` = ?', (code,))
    risk = run_query('SELECT * FROM funds_data.fund_risk_grades WHERE `펀드코드` = ?', (code,))
    tags = run_query('SELECT * FROM funds_data.fund_tags WHERE `펀드코드` = ?', (code,))

    return render_template('fund_detail.html',
                           fund=fund.iloc[0].to_dict() if not fund.empty else {},
                           types=types.iloc[0].to_dict() if not types.empty else {},
                           perf=perf.iloc[0].to_dict() if not perf.empty else {},
                           risk=risk.iloc[0].to_dict() if not risk.empty else {},
                           tags=tags.iloc[0].to_dict() if not tags.empty else {})


@app.route('/dashboard')
def dashboard():
    # ────────────────────────────────────────────────────────────────────────────
    # 0. 필터 파라미터 가져오기 (GET 요청으로 들어옴)
    # ────────────────────────────────────────────────────────────────────────────
    search_query = request.args.get('search_query', '')
    fund_type_majors = request.args.getlist('fund_type_major')
    max_risk_grade = request.args.get('max_risk_grade', '')
    min_perf = request.args.get('min_perf', '')
    max_fee = request.args.get('max_fee', '')
    selected_tags = request.args.getlist('tags') # 'tags=가치주&tags=성장주'

    # 현재 필터 값을 템플릿에 전달하여 폼에 기본값으로 설정
    current_filters = {
        'search_query': search_query,
        'fund_type_major': fund_type_majors,
        'max_risk_grade': max_risk_grade,
        'min_perf': min_perf,
        'max_fee': max_fee,
        'selected_tags': selected_tags
    }

    # ────────────────────────────────────────────────────────────────────────────
    # 0.1. 필터링된 펀드 목록 조회 (새로운 메인 테이블용)
    # ────────────────────────────────────────────────────────────────────────────
    # Databricks SQL에서는 GROUP_CONCAT 대신 ARRAY_JOIN(FILTER(ARRAY(...), x -> x IS NOT NULL), ', ')를 사용합니다.
    # MISSING_AGGREGATION 오류 해결을 위해 ARRAY 내의 태그 컬럼들을 ANY_VALUE()로 감싸줍니다.
    filtered_funds_sql = """
        SELECT
            fi.`펀드코드`,
            fi.`펀드명`,
            fi.`운용사명`,
            fp.`펀드성과정보_1년`,
            frg.`투자위험등급`,
            ff.`운용보수`,
            ARRAY_JOIN(
                FILTER(
                    ARRAY(
                        CASE WHEN ANY_VALUE(ft.`가치주`) > 0 THEN '가치주' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`성장주`) > 0 THEN '성장주' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`중소형주`) > 0 THEN '중소형주' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`글로벌`) > 0 THEN '글로벌' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`자산배분`) > 0 THEN '자산배분' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`4차산업`) > 0 THEN '4차산업' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`ESG`) > 0 THEN 'ESG' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`배당주`) > 0 THEN '배당주' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`FoFs`) > 0 THEN 'FoFs' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`퇴직연금`) > 0 THEN '퇴직연금' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`고난도금융상품`) > 0 THEN '고난도금융상품' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`절대수익추구`) > 0 THEN '절대수익추구' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`레버리지`) > 0 THEN '레버리지' ELSE NULL END,
                        CASE WHEN ANY_VALUE(ft.`퀀트`) > 0 THEN '퀀트' ELSE NULL END
                    ),
                    x -> x IS NOT NULL
                ), ', '
            ) AS `주요태그`
        FROM funds_data.funds_info fi
        LEFT JOIN funds_data.fund_types ftp ON fi.`펀드코드` = ftp.`펀드코드`
        LEFT JOIN funds_data.fund_performance fp ON fi.`펀드코드` = fp.`펀드코드`
        LEFT JOIN funds_data.fund_risk_grades frg ON fi.`펀드코드` = frg.`펀드코드`
        LEFT JOIN funds_data.fund_fees ff ON fi.`펀드코드` = ff.`펀드코드`
        LEFT JOIN funds_data.fund_tags ft ON fi.`펀드코드` = ft.`펀드코드`
        WHERE 1=1
    """
    filtered_funds_params = []

    if search_query:
        filtered_funds_sql += " AND fi.`펀드명` LIKE ?"
        filtered_funds_params.append(f'%{search_query}%')
    if fund_type_majors:
        placeholders = ','.join(['?'] * len(fund_type_majors))
        filtered_funds_sql += f" AND ftp.`대유형` IN ({placeholders})"
        filtered_funds_params.extend(fund_type_majors)
    if max_risk_grade:
        filtered_funds_sql += " AND frg.`투자위험등급` <= ?"
        filtered_funds_params.append(float(max_risk_grade))
    if min_perf:
        filtered_funds_sql += " AND fp.`펀드성과정보_1년` >= ?"
        filtered_funds_params.append(float(min_perf))
    if max_fee:
        filtered_funds_sql += " AND ff.`운용보수` <= ?"
        filtered_funds_params.append(float(max_fee))
    
    tag_cols = [ # tag_cols는 여기서 다시 한번 정의됩니다 (아래의 social_traffic 및 theme_metrics에서 참조)
        '가치주', '성장주', '중소형주', '글로벌', '자산배분', '4차산업',
        'ESG', '배당주', 'FoFs', '퇴직연금', '고난도금융상품',
        '절대수익추구', '레버리지', '퀀트'
    ]
    for tag in selected_tags:
        # tag_cols와 비교하여 유효성 검사
        if tag in tag_cols:
            filtered_funds_sql += f" AND ft.`{tag}` > 0" # 필터 조건도 ANY_VALUE로 감싸줍니다.

    # ARRAY_JOIN(FILTER(ARRAY(...)))는 이미 최종 문자열이므로 GROUP BY에 포함되지 않습니다.
    # GROUP BY 절은 집계되지 않는 SELECT 컬럼만 포함해야 합니다.
    filtered_funds_sql += " GROUP BY fi.`펀드코드`, fi.`펀드명`, fi.`운용사명`, fp.`펀드성과정보_1년`, frg.`투자위험등급`, ff.`운용보수`"
    
    filtered_funds = run_query(filtered_funds_sql, filtered_funds_params).to_dict(orient='records')


    # ────────────────────────────────────────────────────────────────────────────
    # 0.2. 드롭다운 필터링을 위한 고유 값 조회
    # ────────────────────────────────────────────────────────────────────────────
    all_major_types_sql = "SELECT DISTINCT `대유형` FROM funds_data.fund_types ORDER BY `대유형`"
    all_major_types = [row['대유형'] for _, row in run_query(all_major_types_sql).iterrows()]

    # ────────────────────────────────────────────────────────────────────────────
    # 0. (카드) 총 펀드 수
    # ────────────────────────────────────────────────────────────────────────────
    total_funds_sql = """
        SELECT COUNT(*) AS total_count
        FROM funds_data.funds_info
    """
    df_total_funds = run_query(total_funds_sql)
    total_funds = int(df_total_funds.loc[0, 'total_count'])

    # ────────────────────────────────────────────────────────────────────────────
    # 00. (카드) 평균 1년 성과
    # ────────────────────────────────────────────────────────────────────────────
    avg_perf_sql = """
        SELECT AVG(`펀드성과정보_1년`) AS avg_perf
        FROM funds_data.fund_performance
    """
    df_avg_perf = run_query(avg_perf_sql)
    average_perf = round(float(df_avg_perf.loc[0, 'avg_perf'] or 0), 2)

    # ────────────────────────────────────────────────────────────────────────────
    # 1. 월별 펀드 설정(orders_data)
    # ────────────────────────────────────────────────────────────────────────────
    orders_sql = """
        SELECT DATE_FORMAT(`설정일`, 'yyyy-MM') AS month,
               COUNT(*) AS num_funds
        FROM funds_data.funds_info
        GROUP BY month
        ORDER BY month
    """
    df_orders = run_query(orders_sql)
    orders_data = {
        "months": df_orders["month"].tolist(),
        "values": df_orders["num_funds"].tolist()
    }

    # ────────────────────────────────────────────────────────────────────────────
    # 2. 평균보수 (운용보수+판매보수 합의 평균)
    # ────────────────────────────────────────────────────────────────────────────
    avg_fee_sql = """
        SELECT ROUND(AVG(ff.`운용보수` + ff.`판매보수`), 2) AS avg_fee
        FROM funds_data.fund_fees ff
    """
    df_avg_fee = run_query(avg_fee_sql)
    average_fee = float(df_avg_fee.loc[0, 'avg_fee'] or 0)


    # ────────────────────────────────────────────────────────────────────────────
    # 4. 주요 테마별 펀드 비중(social_traffic)
    # ────────────────────────────────────────────────────────────────────────────
    # tag_cols는 위에 정의된 것을 사용
    tag_sum_sql = f"""
        SELECT
            SUM(`가치주`) AS `가치주`,
            SUM(`성장주`) AS `성장주`,
            SUM(`중소형주`) AS `중소형주`,
            SUM(`글로벌`) AS `글로벌`,
            SUM(`자산배분`) AS `자산배분`,
            SUM(`4차산업`) AS `4차산업`,
            SUM(`ESG`) AS `ESG(사회책임투자형)`,
            SUM(`배당주`) AS `배당주`,
            SUM(`FoFs`) AS `FoFs`,
            SUM(`퇴직연금`) AS `퇴직연금`,
            SUM(`고난도금융상품`) AS `고난도금융상품`,
            SUM(`절대수익추구`) AS `절대수익추구`,
            SUM(`레버리지`) AS `레버리지`,
            SUM(`퀀트`) AS `퀀트`
        FROM funds_data.fund_tags
    """
    df_tags = run_query(tag_sum_sql)
    total_sum = sum(df_tags.iloc[0].values)
    social_traffic = []
    for i, tag in enumerate(tag_cols):
        visitors = int(df_tags.iloc[0][i])
        percent = round(100 * visitors / total_sum, 2) if total_sum else 0
        social_traffic.append({
            "channel": tag,
            "visitors": visitors,
            "percent": percent
        })

    # ────────────────────────────────────────────────────────────────────────────
    # 5. 투자위험등급 분포(risk_data)
    # ────────────────────────────────────────────────────────────────────────────
    risk_dist_sql = """
        SELECT ROUND(`투자위험등급`) AS risk_grade,
               COUNT(*) AS count
        FROM funds_data.fund_risk_grades
        GROUP BY risk_grade
        ORDER BY risk_grade
    """
    df_risk = run_query(risk_dist_sql)
    risk_data = {
        "labels": [int(x) for x in df_risk["risk_grade"].tolist()],
        "values": df_risk["count"].tolist()
    }
    # ────────────────────────────────────────────────────────────────────────────
    # 6.1 테마별 평균 성과 & 평균 위험(theme_metrics)
    # ────────────────────────────────────────────────────────────────────────────
    theme_metrics = {}
    for tag in tag_cols:
        theme_sql = f"""
            SELECT
                AVG(fp.`펀드성과정보_1년`)   AS avg_perf,
                AVG(fr.`투자위험등급`)     AS avg_risk
            FROM funds_data.fund_tags t
            JOIN funds_data.fund_performance fp ON t.`펀드코드` = fp.`펀드코드`
            JOIN funds_data.fund_risk_grades fr ON t.`펀드코드` = fr.`펀드코드`
            WHERE t.`{tag}` > 0
        """
        df_theme = run_query(theme_sql)
        theme_metrics[tag] = {
            "avg_perf": round(float(df_theme.loc[0, 'avg_perf'] or 0), 2),
            "avg_risk": round(float(df_theme.loc[0, 'avg_risk'] or 0), 2)
        }
    # ────────────────────────────────────────────────────────────────────────────
    # 6.2 추천 랭킹 상위 10개 펀드(top10_funds)
    # ────────────────────────────────────────────────────────────────────────────
    top10_sql = """
        SELECT i.`펀드명` AS name,
               k.`추천랭킹` AS rank,
               ROUND(k.`최종점수`, 2) AS score
        FROM funds_data.funds_info i
        JOIN funds_data.fund_rank k ON i.`펀드코드` = k.`펀드코드`
        ORDER BY k.`추천랭킹` ASC
        LIMIT 10
    """
    df_top10 = run_query(top10_sql)
    top10_funds = df_top10.to_dict(orient='records')

    # ────────────────────────────────────────────────────────────────────────────
    # 7. 펀드 대분류 분포(fund_type_dist: Pie Chart)
    # ────────────────────────────────────────────────────────────────────────────
    type_dist_sql = """
        SELECT `대유형` AS category,
               COUNT(*)           AS cnt
        FROM funds_data.fund_types
        GROUP BY `대유형`
    """
    df_type_dist = run_query(type_dist_sql)
    fund_type_dist = {
        "labels": df_type_dist["category"].tolist(),
        "values": df_type_dist["cnt"].tolist()
    }

    # ────────────────────────────────────────────────────────────────────────────
    # 8. 대분류별 평균 1년 성과 & 평균 최대 손실폭 (라인 차트, 필터 반영)
    # ────────────────────────────────────────────────────────────────────────────
    perf_mdd_sql = f"""
        SELECT
            ftp.`대유형` AS category,
            ROUND(AVG(fp.`펀드성과정보_1년`), 2)   AS avg_perf,
            ROUND(AVG(fp.`MaximumDrawDown_1년`), 2) AS avg_mdd
        FROM funds_data.funds_info fi
        JOIN funds_data.fund_performance fp ON fi.`펀드코드` = fp.`펀드코드`
        JOIN funds_data.fund_types ftp       ON fi.`펀드코드` = ftp.`펀드코드`
        JOIN funds_data.fund_fees ff         ON fi.`펀드코드` = ff.`펀드코드`
        JOIN funds_data.fund_risk_grades frg ON fi.`펀드코드` = frg.`펀드코드`
        LEFT JOIN funds_data.fund_tags ft     ON fi.`펀드코드` = ft.`펀드코드`
        WHERE 1=1
          {"AND fi.`펀드명` LIKE ?" if search_query else ""}
          {f"AND ftp.`대유형` IN ({','.join(['?']*len(fund_type_majors))})" if fund_type_majors else ""}
          {"AND frg.`투자위험등급` <= ?" if max_risk_grade else ""}
          {"AND fp.`펀드성과정보_1년` >= ?" if min_perf else ""}
          {"AND ff.`운용보수` <= ?" if max_fee else ""}
          -- 태그 필터 반복 적용 (ANY_VALUE)
          {" ".join([f"AND ft.`{tag}` > 0" for tag in selected_tags])}
        GROUP BY ftp.`대유형`
        ORDER BY ftp.`대유형`
    """
    df_perf_mdd = run_query(perf_mdd_sql, filtered_funds_params)
    perf_mdd_categories = df_perf_mdd["category"].tolist()
    perf_mdd_perf       = df_perf_mdd["avg_perf"].tolist()
    perf_mdd_mdd        = df_perf_mdd["avg_mdd"].tolist()

    # ────────────────────────────────────────────────────────────────────────────
    # 9. 대분류별 펀드 자금흐름 합 (NetCashFlow_1년) - 라인 차트, 필터 반영
    # ────────────────────────────────────────────────────────────────────────────
    cashflow_sql = f"""
        SELECT
            ftp.`대유형` AS category,
            ROUND(SUM(fp.`NetCashFlow펀드자금흐름_1년`), 2) AS total_cashflow
        FROM funds_data.funds_info fi
        JOIN funds_data.fund_performance fp ON fi.`펀드코드` = fp.`펀드코드`
        JOIN funds_data.fund_types ftp       ON fi.`펀드코드` = ftp.`펀드코드`
        JOIN funds_data.fund_fees ff         ON fi.`펀드코드` = ff.`펀드코드`
        JOIN funds_data.fund_risk_grades frg ON fi.`펀드코드` = frg.`펀드코드`
        LEFT JOIN funds_data.fund_tags ft     ON fi.`펀드코드` = ft.`펀드코드`
        WHERE 1=1
          {"AND fi.`펀드명` LIKE ?" if search_query else ""}
          {f"AND ftp.`대유형` IN ({','.join(['?']*len(fund_type_majors))})" if fund_type_majors else ""}
          {"AND frg.`투자위험등급` <= ?" if max_risk_grade else ""}
          {"AND fp.`펀드성과정보_1년` >= ?" if min_perf else ""}
          {"AND ff.`운용보수` <= ?" if max_fee else ""}
          {" ".join([f"AND ft.`{tag}` > 0" for tag in selected_tags])}
        GROUP BY ftp.`대유형`
        ORDER BY ftp.`대유형`
    """
    df_cashflow = run_query(cashflow_sql, filtered_funds_params)
    cashflow_categories = df_cashflow["category"].tolist()
    cashflow_values     = df_cashflow["total_cashflow"].tolist()

    # ────────────────────────────────────────────────────────────────────────────
    # 10. 테마별 상위 5개 펀드(theme_top5: Table)
    #     * 미리 모든 테마에 대해 Top 5를 구해서 넘겨줌
    # ────────────────────────────────────────────────────────────────────────────
    theme_top5 = {}
    for tag in tag_cols:
        top5_sql = f"""
            SELECT i.`펀드명` AS name,
                   fp.`펀드성과정보_1년` AS perf
            FROM funds_data.fund_tags t
            JOIN funds_data.fund_performance fp ON t.`펀드코드` = fp.`펀드코드`
            JOIN funds_data.funds_info i ON t.`펀드코드` = i.`펀드코드`
            WHERE t.`{tag}` > 0
            ORDER BY fp.`펀드성과정보_1년` DESC
            LIMIT 5
        """
        df_top5 = run_query(top5_sql)
        # [{'name': '펀드A', 'perf': 12.34}, …]
        theme_top5[tag] = df_top5.to_dict(orient='records')

    # ────────────────────────────────────────────────────────────────────────────
    # 모든 데이터를 템플릿으로 전달
    # ────────────────────────────────────────────────────────────────────────────
    return render_template(
        'dashboard.html',

        # 카드
        total_funds=total_funds,
        average_perf=average_perf,
        average_fee=average_fee,
        orders_data=orders_data,

        # 필터링된 펀드 목록
        filtered_funds=filtered_funds,
        current_filters=current_filters,
        all_major_types=all_major_types,

        # 차트용 데이터
        fund_type_dist=fund_type_dist,
        perf_mdd_categories=perf_mdd_categories,
        perf_mdd_perf=perf_mdd_perf,
        perf_mdd_mdd=perf_mdd_mdd,
        cashflow_categories=cashflow_categories,
        cashflow_values=cashflow_values,

        # 기존 테마 차트 & 테이블
        social_traffic=social_traffic,
        risk_data=risk_data,
        top10_funds=top10_funds,
        tag_cols=tag_cols,
        theme_metrics=theme_metrics,
        theme_top5=theme_top5
    )

@app.route('/db_dash')
def databricks_dashboard():
    # 실제 대시보드 임베드 URL로 교체하세요
    dashboard_url = "https://adb-625348768188018.18.azuredatabricks.net/dashboardsv3/01f03d3450ba1580b668837389ccfdde/published?o=625348768188018&f_a6f4c99b%7Eb0d634d7=PR73T7JQK435%2CPRBK5R8LK175%2CPRBK5R8LKK15%2CPRBK5R8LK14K"
    return render_template('db_dash.html', dashboard_url=dashboard_url)



