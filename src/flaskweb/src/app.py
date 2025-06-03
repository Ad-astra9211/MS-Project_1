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

@app.route('/')
def home():
    df = run_query("SELECT * FROM funds_data.funds_info LIMIT 10")
    return render_template('index.html', tables=df.to_html(classes='data'))

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        occupation = request.form['occupation']
        risk_preference = request.form['risk']
        themes = request.form.getlist('theme')

        query = '''
        SELECT i.`펀드코드`, i.`펀드명`, r.`투자위험등급`, f.`운용보수`, p.`펀드성과정보_1년`, k.`추천랭킹`
        FROM funds_data.funds_info i
        JOIN funds_data.fund_risk_grades r ON i.`펀드코드` = r.`펀드코드`
        JOIN funds_data.fund_performance p ON i.`펀드코드` = p.`펀드코드`
        JOIN funds_data.fund_rank k ON i.`펀드코드` = k.`펀드코드`
        JOIN funds_data.fund_fees f ON i.`펀드코드` = f.`펀드코드`
        JOIN funds_data.fund_tags t ON i.`펀드코드` = t.`펀드코드`
        WHERE r.`투자위험등급` <= ?
        '''

        for theme in themes:
            query += f" AND t.`{theme}` > 0.5"

        query += " ORDER BY k.`추천랭킹` ASC LIMIT 20"

        df = run_query(query, (risk_preference,))
        funds = df.to_dict(orient='records')

        return render_template('result.html', funds=funds)

    except Exception as e:
        # 에러 로그 출력 및 에러 페이지 렌더링(또는 메시지 반환)
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

    # 2. 월별 펀드 성과 합계(sales_data): 임의로 펀드성과정보_1년의 월별 합계
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
               CAST(f.`순자산`/1000000 AS INT) AS visitors,
               CAST(f.`순자산`/2000000 AS INT) AS unique_users,
               ROUND(100 - MOD(p.`펀드성과정보_1년`, 100), 2) AS bounce_rate
        FROM funds_data.funds_info i
        JOIN funds_data.fund_performance p ON i.`펀드코드` = p.`펀드코드`
        JOIN funds_data.fund_performance f ON i.`펀드코드` = f.`펀드코드`
        LIMIT 10
    """
    df_page_visits = run_query(page_visits_sql)
    page_visits = df_page_visits.to_dict(orient='records')

    # 4. 소셜 트래픽(social_traffic): 주요 테마별 합계 및 비율
    tag_cols = ['가치주', '성장주', 'ESG', '글로벌']
    tag_sum_sql = f"""
        SELECT
            SUM(`가치주`) AS value1,
            SUM(`성장주`) AS value2,
            SUM(`ESG`) AS value3,
            SUM(`글로벌`) AS value4
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



if __name__ == '__main__':
    app.run(debug=True)
