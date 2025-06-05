from flask import Flask, render_template, request
import os
from databricks import sql
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

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

# 클러스터별 기본 필터 조건
cluster_fund_filter_conditions = {
    0: {  # 오래된 VIP & 활동성 높은 고객
        "funds_data.fund_performance.펀드성과정보_1년": (">", 0.05),
        "funds_data.fund_performance.펀드수정샤프연환산_1년": (">", 1.0),
        "funds_data.fund_risk_grades.투자위험등급": ("<=", 3)
    },
    1: {  # 저활동/이탈 가능성 고객
        "funds_data.fund_tags.절대수익추구": (">", 0.5),
        "funds_data.fund_tags.퇴직연금": (">", 0.5),
        "funds_data.fund_fees.선취수수료": ("==", 0.0),
        "funds_data.fund_performance.MaximumDrawDown_1년": ("<", 0.05),
        "funds_data.fund_risk_grades.투자위험등급": ("<=", 3)
    },
    2: {  # 신규 고객 또는 빠르게 이탈한 고객
        "funds_data.fund_tags.4차산업": (">", 0.5),
        "funds_data.fund_tags.성장주": (">", 0.5),
        "funds_data.fund_fees.선취수수료": ("==", 0.0),
        "funds_data.fund_performance.펀드성과정보_1년": (">", 0.03),
        "funds_data.fund_risk_grades.투자위험등급": ("<=", 4),
    },
    3: {  # 안정적인 중급 이용 고객
        "funds_data.fund_tags.자산배분": (">", 0.5),
        "funds_data.fund_performance.펀드수정샤프연환산_1년": (">", 0.8),
        "funds_data.fund_fees.운용보수": ("<", 1.0),
        "funds_data.fund_risk_grades.투자위험등급": ("<=", 2),
    },
    4: {  # 중저가 이용/평범한 고객
        "funds_data.fund_tags.배당주": (">", 0.5),
        "funds_data.fund_tags.중소형주": ("<", 0.5),
        "funds_data.fund_performance.펀드성과정보_1년": (">", 0.02),
        "funds_data.fund_fees.판매보수": ("<", 0.8),
        "funds_data.fund_risk_grades.투자위험등급": ("<=", 3),
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
        # 1. 회원코드 입력이 있으면 cluster값을 우선 조회
        member_code = request.form.get('member_code')
        cluster_value = None
        preselected_themes = []
        preselected_risk = None
        cluster_cond = {}

        # [핵심] 적용할 필드명 리스트
        filter_fields = {
            "funds_data.fund_performance.펀드수정샤프연환산_1년": "p.`펀드수정샤프연환산_1년`",
            "funds_data.fund_performance.펀드성과정보_1년": "p.`펀드성과정보_1년`",
            "funds_data.fund_fees.선취수수료": "f.`선취수수료`",
            "funds_data.fund_performance.MaximumDrawDown_1년": "p.`MaximumDrawDown_1년`",
            "funds_data.fund_fees.운용보수": "f.`운용보수`",
            "funds_data.fund_fees.판매보수": "f.`판매보수`"
        }

        if member_code:
            # cluster값 조회
            query = "SELECT cluster FROM database_pjt.df_final_with_cluster WHERE `발급회원번호` = ?"
            df = run_query(query, params=(member_code,))
            if df.empty:
                flash('해당 회원 코드가 존재하지 않습니다.')
                return redirect(url_for('home'))
            cluster_value = int(df.iloc[0]['cluster'])

            # cluster별 기본 필터/테마/위험등급 추출
            cluster_cond = cluster_fund_filter_conditions.get(cluster_value, {})
            for key, (op, val) in cluster_cond.items():
                # 테마 키워드 추출
                for theme in theme_keywords:
                    if theme in key and op == ">" and val >= 0.5:
                        preselected_themes.append(theme)
                # 위험등급 추출
                if '투자위험등급' in key and op in ("<=", "<"):
                    preselected_risk = val
            # print('cluster_cond:', cluster_cond)
            # print('preselected_themes:', preselected_themes)
            # print('preselected_risk:', preselected_risk)

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

        # [3] 클러스터 필터 동적 쿼리 추가
        applied_filters = {}  # 화면 표시용
        if cluster_cond:
            for key, (op, val) in cluster_cond.items():
                # 필드명이 filter_fields에 있는 경우만 쿼리에 추가
                if key in filter_fields:
                    sql_field = filter_fields[key]
                    if op == "==":
                        query += f" AND {sql_field} = ?"
                    else:
                        query += f" AND {sql_field} {op} ?"
                    params.append(val)
                    # 화면 표시용 라벨
                    label_map = {
                        "funds_data.fund_performance.펀드수정샤프연환산_1년": "펀드수정샤프연환산_1년",
                        "funds_data.fund_performance.펀드성과정보_1년": "펀드성과정보_1년",
                        "funds_data.fund_fees.선취수수료": "선취수수료",
                        "funds_data.fund_performance.MaximumDrawDown_1년": "MaximumDrawDown_1년",
                        "funds_data.fund_fees.운용보수": "운용보수",
                        "funds_data.fund_fees.판매보수": "판매보수"
                    }
                    applied_filters[label_map[key]] = f"{op} {val}"

        # 키워드(펀드명) 필터
        if keyword:
            query += " AND i.`펀드명` LIKE ?"
            params.append(f'%{keyword}%')

        query += f" ORDER BY {sort_column}"

        df = run_query(query, params)
        funds = df.to_dict(orient='records')

        # result.html에 preselected_themes, preselected_risk 전달
        return render_template(
            'result.html',
            funds=funds,
            preselected_themes=themes,
            preselected_risk=risk_preference,
            theme_keywords=theme_keywords,
            applied_filters=applied_filters  # 화면 표시용 필터 전달
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
    # 1. 월별 펀드 설정(orders_data): 펀드 신규 설정 수
    orders_sql = """
        SELECT DATE_FORMAT(`설정일`, 'yyyy-MM') AS month, COUNT(*) AS num_funds
        FROM funds_data.funds_info
        GROUP BY month
        ORDER BY month
    """
    df_orders = run_query(orders_sql)
    orders_data = {
        "months": df_orders["month"].tolist(),
        "values": df_orders["num_funds"].tolist()
    }

    # 2. 
    sales_sql = """
    SELECT DATE_FORMAT(i.`설정일`, 'yyyy-MM') AS month, SUM(p.`펀드성과정보_1년`) AS total_sales
    FROM funds_data.fund_performance p
    JOIN funds_data.funds_info i ON p.`펀드코드` = i.`펀드코드`
    GROUP BY month
    ORDER BY month
    """
    df_sales = run_query(sales_sql)
    sales_data = {
        "months": df_sales["month"].tolist(),
        "values": [round(x, 2) for x in df_sales["total_sales"].tolist()]
    }

    # 3. 페이지 방문 현황(page_visits): 펀드별 임의 집계 (순자산 등 활용)
    page_visits_sql = """
        SELECT i.`펀드명` AS name,
               CAST(p.`순자산`/1000000 AS INT) AS visitors,
               CAST(p.`순자산`/2000000 AS INT) AS unique_users,
               ROUND(100 - MOD(p.`펀드성과정보_1년`, 100), 2) AS bounce_rate
        FROM funds_data.funds_info i
        JOIN funds_data.fund_performance p ON i.`펀드코드` = p.`펀드코드`
        LIMIT 10
    """
    df_page_visits = run_query(page_visits_sql)
    page_visits = df_page_visits.to_dict(orient='records')

    # 4. 소셜 트래픽(social_traffic): 주요 테마별 합계 및 비율
    tag_cols = ['가치주', '성장주', '중소형주', '글로벌', '자산배분', '4차산업', 'ESG', '배당주', 'FoFs', '퇴직연금', '고난도금융상품', '절대수익추구', '레버리지', '퀀트']
    tag_sum_sql = f"""
        SELECT
            SUM(`가치주`) AS `가치주`,
            SUM(`성장주`) AS `성장주`,
            SUM(`중소형주`) AS `중소형주`,
            SUM(`글로벌`) AS `글로벌`,
            SUM(`자산배분`) AS `자산배분`,
            SUM(`4차산업`) AS `4차산업`,
            SUM(`ESG`) AS `ESG`,
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

    return render_template(
        'dashboard.html',
        sales_data=sales_data,
        orders_data=orders_data,
        page_visits=page_visits,
        social_traffic=social_traffic
    )

@app.route('/db_dash')
def databricks_dashboard():
    # 실제 대시보드 임베드 URL로 교체하세요
    dashboard_url = "https://adb-625348768188018.18.azuredatabricks.net/dashboardsv3/01f03d3450ba1580b668837389ccfdde/published?o=625348768188018&f_a6f4c99b%7Eb0d634d7=PR73T7JQK435%2CPRBK5R8LK175%2CPRBK5R8LKK15%2CPRBK5R8LK14K"
    return render_template('db_dash.html', dashboard_url=dashboard_url)



