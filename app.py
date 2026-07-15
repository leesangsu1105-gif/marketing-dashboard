import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import ssl
import urllib.request
import io
import time

# [SSL 강력 디버깅 패치] 모든 네트워크 요청 시 인증서 검증을 강제 해제합니다.
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)))

# 1. 전역 시스템 환경 및 테마 최적화
st.set_page_config(page_title="마케팅 효율 인텔리전스 시스템", layout="wide")

st.markdown("""<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
h1 { font-weight: 800; color: #FFFFFF; letter-spacing: -0.05em; }
h3 { font-weight: 700; color: #E2E8F0; margin-top: 1.5rem; }

/* 5열 맞춤 그리드 컨테이너 */
.kpi-board {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1rem;
    margin-top: 1rem;
    margin-bottom: 2rem;
}

/* 롱 카드 (1, 2, 5열 전용: 높이 220px 통합) */
.kpi-card-tall {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 1.2rem;
    height: 220px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

/* 분할 하프 카드 (3, 4열 전용) */
.kpi-card-half {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 0.5rem 1.2rem;
    height: calc(50% - 0.35rem); /* 완벽하게 220px 롱 카드의 절반에 맞춰 단차 소멸 */
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

/* YoY 미비교 시 상하 수평 중앙 정렬을 위한 Modifier 클래스 */
.kpi-card-tall.no-yoy {
    justify-content: center !important;
    gap: 0.8rem;
}
.kpi-card-half.no-yoy {
    justify-content: center !important;
    gap: 0.2rem;
}

.kpi-label { font-size: 0.82rem; color: #94A3B8; font-weight: 600; }
.kpi-val { font-size: 1.55rem; font-weight: 800; color: #FFFFFF; line-height: 1.2; }
.kpi-val-half { font-size: 1.45rem; font-weight: 800; color: #FFFFFF; line-height: 1.1; }

/* 증감률 폰트 사이즈 업 및 밀림 방지 */
.kpi-delta { 
    font-size: 0.95rem; 
    font-weight: 700; 
    margin-top: 0.15rem; 
    display: inline-flex; 
    align-items: center; 
}
/* 한국 증시 표준 스키마 적용: + 상승은 빨간색(Warm Red), - 하락은 파란색(Cool Blue) */
.kpi-delta.plus { color: #F87171; }   /* 정열적인 상승 빨간색 */
.kpi-delta.minus { color: #60A5FA; }  /* 이성적인 하락 파란색 */
.kpi-delta-white { font-size: 0.95rem; font-weight: 700; color: #FFFFFF; opacity: 0.9; }

/* 그라데이션 프리미엄 카드 배경 선언 */
.purple { background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%) !important; border: none !important; }
.emerald { background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important; border: none !important; }

/* 그라데이션 카드 전용 초고대비 가독성 타이틀 텍스트 설정 */
.purple .kpi-label, .emerald .kpi-label {
    color: #F8FAFC !important; /* 묻히지 않는 최상위 화이트 */
    font-weight: 800 !important; /* 강하고 묵직한 볼드체 */
    text-shadow: 0px 1px 3px rgba(15, 23, 42, 0.35) !important; /* 가독성을 위한 암부 그림자 투사 */
    opacity: 1.0 !important;
}
</style>""", unsafe_allow_html=True)

st.title("📊 플랫폼 서비스 광고 효율 대시보드")
st.markdown("<p style='color:#94A3B8; font-size:1.1rem;'>월별로 각 서비스의 광고 성과를 요약합니다. (구글 스프레드시트 실시간 동기화 중)</p>", unsafe_allow_html=True)
st.markdown("---")

tabs = st.tabs(["전체 통합", "뿌리오", "반값문자", "알뜰문자", "문자매니아"])

# 3. 데이터 인프라 스키마 정의 (신규 추가된 매체별 CPA 반영)
schema_mapping = {
    '연도': 'str', '월': 'str', '서비스명': 'str',
    '전체매출': 'float', '전체광고비': 'float',
    '네이버광고비': 'float', '구글광고비': 'float', '광고가입자': 'float',
    '네이버가입자': 'float', '구글가입자': 'float', '전체가입자': 'float',
    '광고가입자CPA': 'float', '신규유료고객수': 'float', '유료고객CPA': 'float',
    '유료고객전환율': 'float', '신규당월매출': 'float', '광고비ROAS': 'float',
    '매출': 'float', '신규누적매출': 'float',
    '네이버CPA': 'float', '구글CPA': 'float'
}
numeric_cols = [col for col, dtype in schema_mapping.items() if dtype == 'float']

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSWL4QJl1FZtEc2Jh7ymw9fcC17z-Huu5o0bQMVvEge3l9IZL4T90dWiEGDxwL0QeAPayEBElVmCBjt/pub?gid=2077779532&single=true&output=csv"

@st.cache_data(ttl=5)
def load_google_sheet_data(url):
    # 구글 서버 자체의 웹게시 캐시(5분 지연)를 원천 차단하기 위해 주소 끝에 타임스탬프 난수를 강제 병합합니다.
    cache_buster = f"&_cb={int(time.time())}"
    req = urllib.request.Request(url + cache_buster, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx) as response:
        data = response.read()
    return pd.read_csv(io.BytesIO(data))

try:
    raw_data = load_google_sheet_data(SHEET_CSV_URL)
    raw_data.columns = [str(c).strip() for c in raw_data.columns]
    
    for col, dtype in schema_mapping.items():
        if col not in raw_data.columns:
            raw_data[col] = 0.0 if dtype == 'float' else ''
            
    # [핵심] ROAS 열을 제외한 다른 수치만 일차적으로 정형화합니다.
    for col in numeric_cols:
        if col != '광고비ROAS':
            raw_data[col] = pd.to_numeric(raw_data[col], errors='coerce').fillna(0.0)

    # [지능형 ROAS 필터 변환 함수]
    def smart_parse_roas(val):
        if pd.isna(val) or val == '':
            return 0.0
        if isinstance(val, str):
            val = val.replace('%', '').replace(',', '').strip()
        try:
            num = float(val)
            if 0 < num <= 10.0:
                return num * 100
            return num
        except:
            return 0.0

    raw_data['광고비ROAS'] = raw_data['광고비ROAS'].apply(smart_parse_roas)
        
    raw_data['연도'] = raw_data['연도'].astype(str).str.replace(r'\.0$', '', regex=True)
    raw_data['월'] = raw_data['월'].astype(str).str.strip()
    raw_data['서비스명'] = raw_data['서비스명'].astype(str).str.strip()
    
    # 만약 구글 시트에서 직접 전달된 CPA 값이 없다면 수식으로 안전 복구해둡니다.
    raw_data['네이버CPA'] = (raw_data['네이버광고비'] / raw_data['네이버가입자']).fillna(0).replace([float('inf'), float('-inf')], 0)
    raw_data['구글CPA'] = (raw_data['구글광고비'] / raw_data['구글가입자']).fillna(0).replace([float('inf'), float('-inf')], 0)
    
    raw_data['월_num'] = raw_data['월'].str.extract(r'(\d+)').astype(float).fillna(0)
    raw_data = raw_data.sort_values(by=['연도', '월_num']).drop(columns=['월_num'])
    
    # 2025년 & 2026년 전년 동기 대비 비교(YoY) 워딩 적용
    year_mode = st.sidebar.selectbox("📅 분석 대상 연도 보기 설정", ["2025년 & 2026년 전년 동기 대비 비교(YoY)", "2025년 성과만 보기", "2026년 성과만 보기"])
    if st.sidebar.button("🔄 실시간 동기화 강제 새로고침"):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.success("✅ 구글 실시간 데이터 파이프라인 가동 중")

    def calculate_metrics(df, target_year, month_filter=None):
        df_year = df[df['연도'] == str(target_year)]
        if df_year.empty:
            return None
        
        # [지능형 활성 월 자동 필터링 파이프라인]
        if month_filter is not None and len(month_filter) > 0:
            df_year = df_year[df_year['월'].isin(month_filter)]
        else:
            # 실적이 존재하는 활성 행 추적
            active_rows = df_year[
                (df_year['전체광고비'] > 0) | 
                (df_year['신규누적매출'] > 0) | 
                (df_year['신규당월매출'] > 0) |
                (df_year['광고가입자'] > 0)
            ]
            if not active_rows.empty:
                active_months = active_rows['월'].unique()
                df_year = df_year[df_year['월'].isin(active_months)]
                
        if df_year.empty:
            return None
            
        spend = df_year['전체광고비'].sum()
        signups = df_year['광고가입자'].sum()
        paid_cust = df_year['신규유료고객수'].sum()
        
        cpa_ad = (spend / signups) if signups > 0 else 0
        cpa_paid = (spend / paid_cust) if paid_cust > 0 else 0
        
        # 실제 데이터가 존재하는 활성 월들에 대해서만 정확한 평균 ROAS 집계
        roas = df_year['광고비ROAS'].mean() if not df_year.empty else 0.0
        
        # [★지능형 누적 매출 정합성 계산 엔진★]
        df_year_calc = df_year.copy()
        df_year_calc['월_num_temp'] = df_year_calc['월'].str.extract(r'(\d+)').astype(float).fillna(0)
        df_year_sorted = df_year_calc.sort_values(by='월_num_temp')
        
        revenue = df_year_sorted.iloc[-1]['신규누적매출'] if not df_year_sorted.empty else 0.0
        
        return {
            'spend': spend,
            'revenue': revenue,
            'signups': signups,
            'paid_cust': paid_cust,
            'cpa_ad': cpa_ad,
            'cpa_paid': cpa_paid,
            'roas': roas
        }

    def get_delta_html(current_val, prev_val, is_lower_better=False, is_pct_p=False):
        if prev_val is None or prev_val == 0:
            return '<div class="kpi-delta-white">YoY: -</div>'
        diff = current_val - prev_val
        pct = (diff / prev_val) * 100
        
        sign = '+' if diff >= 0 else ''
        arrow = '↑' if diff >= 0 else '↓'
        unit = '%p' if is_pct_p else '%'
        
        if diff == 0:
            cls = 'kpi-delta-white'
        elif diff > 0:
            cls = 'plus'   # 무조건 수학적 증가(+)는 빨간색
        else:
            cls = 'minus'  # 무조건 수학적 감소(-)는 파란색
            
        return f'<div class="kpi-delta {cls}">YoY: {arrow} {sign}{pct:.1f}{unit}</div>'

    def get_delta_html_gradient(current_val, prev_val):
        if prev_val is None or prev_val == 0:
            return '<div class="kpi-delta-white">YoY: -</div>'
        diff = current_val - prev_val
        pct = (diff / prev_val) * 100
        sign = '+' if diff >= 0 else ''
        arrow = '↑' if diff >= 0 else '↓'
        return f'<div class="kpi-delta-white">YoY: {arrow} {sign}{pct:.1f}%</div>'

    def generate_bi_charts(data_subset, label_title, show_yoy=False):
        st.markdown(f"### 🗓️ {label_title}")
        
        # 5단 맞춤형 그리드 카드용 동적 클래스 세팅
        tall_class = "kpi-card-tall" if show_yoy else "kpi-card-tall no-yoy"
        half_class = "kpi-card-half" if show_yoy else "kpi-card-half no-yoy"
        
        if show_yoy:
            df_26 = data_subset[data_subset['연도'] == '2026']
            active_months_26 = df_26[
                (df_26['전체광고비'] > 0) | 
                (df_26['전체가입자'] > 0) | 
                (df_26['신규당월매출'] > 0)
            ]['월'].unique()
            
            if len(active_months_26) == 0:
                active_months_26 = df_26['월'].unique()
            
            m25 = calculate_metrics(data_subset, 2025, month_filter=active_months_26)
            m26 = calculate_metrics(data_subset, 2026, month_filter=active_months_26)
            
            if not m26:
                st.info("비교할 2026년 데이터가 없습니다.")
                return
                
            m25_spend = m25['spend'] if m25 else 0
            m25_revenue = m25['revenue'] if m25 else 0
            m25_signups = m25['signups'] if m25 else 0
            m25_paid_cust = m25['paid_cust'] if m25 else 0
            m25_cpa_ad = m25['cpa_ad'] if m25 else 0
            m25_cpa_paid = m25['cpa_paid'] if m25 else 0
            m25_roas = m25['roas'] if m25 else 0
            
            current_spend = m26['spend']
            current_revenue = m26['revenue']
            current_signups = m26['signups']
            current_paid_cust = m26['paid_cust']
            current_cpa_ad = m26['cpa_ad']
            current_cpa_paid = m26['cpa_paid']
            current_roas = m26['roas']
            
            delta_spend = get_delta_html_gradient(current_spend, m25_spend)
            delta_revenue = get_delta_html_gradient(current_revenue, m25_revenue)
            delta_signups = get_delta_html(current_signups, m25_signups, is_lower_better=False)
            delta_paid = get_delta_html(current_paid_cust, m25_paid_cust, is_lower_better=False)
            delta_cpa_ad = get_delta_html(current_cpa_ad, m25_cpa_ad, is_lower_better=True)
            delta_cpa_paid = get_delta_html(current_cpa_paid, m25_cpa_paid, is_lower_better=True)
            delta_roas = get_delta_html(current_roas, m25_roas, is_lower_better=False, is_pct_p=True)
            
            title_prefix = "2026"
        else:
            year_val = "2025" if "2025년" in year_mode else "2026"
            m = calculate_metrics(data_subset, int(year_val))
            if not m:
                st.info(f"{year_val}년 성과 데이터가 존재하지 않습니다.")
                return
                
            current_spend = m['spend']
            current_revenue = m['revenue']
            current_signups = m['signups']
            current_paid_cust = m['paid_cust']
            current_cpa_ad = m['cpa_ad']
            current_cpa_paid = m['cpa_paid']
            current_roas = m['roas']
            
            delta_spend = ''
            delta_revenue = ''
            delta_signups = ''
            delta_paid = ''
            delta_cpa_ad = ''
            delta_cpa_paid = ''
            delta_roas = ''
            
            title_prefix = year_val

        html_code = f"""<div class="kpi-board">
<div class="{tall_class} purple">
<div>
<div class="kpi-label">{title_prefix} 총 광고비 집행액</div>
<div class="kpi-val" style="margin-top:0.5rem;">{current_spend:,.0f}원</div>
</div>
{delta_spend}
</div>
<div class="{tall_class} emerald">
<div>
<div class="kpi-label">{title_prefix} 신규 누적 매출액</div>
<div class="kpi-val" style="margin-top:0.5rem;">{current_revenue:,.0f}원</div>
</div>
{delta_revenue}
</div>
<div style="height:220px; display:flex; flex-direction:column; justify-content:space-between;">
<div class="{half_class}">
<div>
<div class="kpi-label">총 광고 가입자 수</div>
<div class="kpi-val-half">{current_signups:,.0f}명</div>
</div>
{delta_signups}
</div>
<div class="{half_class}">
<div>
<div class="kpi-label">신규 유료 고객 수</div>
<div class="kpi-val-half">{current_paid_cust:,.0f}명</div>
</div>
{delta_paid}
</div>
</div>
<div style="height:220px; display:flex; flex-direction:column; justify-content:space-between;">
<div class="{half_class}">
<div>
<div class="kpi-label">광고 가입자 CPA</div>
<div class="kpi-val-half">{current_cpa_ad:,.0f}원</div>
</div>
{delta_cpa_ad}
</div>
<div class="{half_class}">
<div>
<div class="kpi-label">신규 유료고객 CPA</div>
<div class="kpi-val-half">{current_cpa_paid:,.0f}원</div>
</div>
{delta_cpa_paid}
</div>
</div>
<div class="{tall_class}">
<div>
<div class="kpi-label">평균 마케팅 ROAS</div>
<div class="kpi-val" style="color: #818CF8; margin-top:0.5rem;">{current_roas:.1f}%</div>
</div>
{delta_roas}
</div>
</div>"""

        st.markdown(html_code, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if show_yoy:
                # 2025 vs 2026 광고비 비교 라인
                st.markdown("<p style='font-weight:600; margin-top:1rem; color:#E2E8F0;'>🔹 전년 동기 대비 광고비 비교 (단위: 억원)</p>", unsafe_allow_html=True)
                df_y_25 = data_subset[data_subset['연도'] == '2025']
                df_y_26 = data_subset[data_subset['연도'] == '2026']
                
                fig_spend = go.Figure()
                fig_spend.add_trace(go.Scatter(x=df_y_25['월'], y=df_y_25['전체광고비']/100000000, name='2025년 광고비',
                                               line=dict(color='#94A3B8', width=2, dash='dot', shape='spline')))
                fig_spend.add_trace(go.Scatter(x=df_y_26['월'], y=df_y_26['전체광고비']/100000000, name='2026년 광고비',
                                               line=dict(color='#818CF8', width=3.5, shape='spline')))
                fig_spend.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10),
                                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#E2E8F0')),
                                        xaxis=dict(showgrid=False, tickfont=dict(color='#94A3B8')),
                                        yaxis=dict(tickformat='.1f', ticksuffix='억', gridcolor='#334155', tickfont=dict(color='#94A3B8')),
                                        hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                st.plotly_chart(fig_spend, use_container_width=True)
                
                # 전년 동기 대비 월별 가입자 및 유료전환 비교
                st.markdown("<p style='font-weight:600; margin-top:1.5rem; color:#E2E8F0;'>🔹 전년 동기 대비 월별 가입자 및 유료전환 비교 (단위: 명)</p>", unsafe_allow_html=True)
                fig_paid = go.Figure()
                fig_paid.add_trace(go.Bar(x=df_y_26['월'], y=df_y_26['전체가입자'], name='26년 전체가입자', marker_color='#475569', opacity=0.35))
                fig_paid.add_trace(go.Bar(x=df_y_26['월'], y=df_y_26['광고가입자'], name='26년 광고가입자', marker_color='#0EA5E9', opacity=0.8))
                fig_paid.add_trace(go.Bar(x=df_y_26['월'], y=df_y_26['신규유료고객수'], name='26년 유료고객', marker_color='#D946EF', opacity=0.9))
                fig_paid.add_trace(go.Scatter(x=df_y_25['월'], y=df_y_25['전체가입자'], name='25년 전체가입자',
                                               line=dict(color='#94A3B8', width=2, dash='dot', shape='spline')))
                fig_paid.add_trace(go.Scatter(x=df_y_25['월'], y=df_y_25['광고가입자'], name='25년 광고가입자',
                                               line=dict(color='#38BDF8', width=2, dash='dot', shape='spline')))
                fig_paid.add_trace(go.Scatter(x=df_y_25['월'], y=df_y_25['신규유료고객수'], name='25년 유료고객',
                                               line=dict(color='#F472B6', width=2, dash='dot', shape='spline')))
                
                fig_paid.update_layout(height=220, barmode='overlay', margin=dict(t=10, b=10, l=10, r=10),
                                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#E2E8F0')),
                                       xaxis=dict(showgrid=False, tickfont=dict(color='#94A3B8')),
                                       yaxis=dict(tickformat=',.0f', ticksuffix='명', gridcolor='#334155', tickfont=dict(color='#94A3B8')),
                                       hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                st.plotly_chart(fig_paid, use_container_width=True)
            else:
                # 단해년도 차트 렌더링
                df_single = data_subset[data_subset['연도'] == year_val]
                st.markdown("<p style='font-weight:600; margin-top:1rem; color:#E2E8F0;'>🔹 매체별 광고비 집행 비중 (단위: %)</p>", unsafe_allow_html=True)
                s_naver = df_single['네이버광고비'].sum()
                s_google = df_single['구글광고비'].sum()
                
                if (s_naver + s_google) > 0:
                    fig_p = px.pie(names=['네이버 광고비', '구글 광고비'], values=[s_naver, s_google], hole=0.5,
                                   color_discrete_sequence=['#03C75A', '#4285F4'])
                    fig_p.update_layout(margin=dict(t=15, b=15, l=10, r=10), height=220, showlegend=True,
                                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                       legend=dict(font=dict(color='#E2E8F0')),
                                       hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                    st.plotly_chart(fig_p, use_container_width=True)
                else:
                    st.info("광고비 집행 내역이 없습니다.")
                    
                st.markdown("<p style='font-weight:600; margin-top:1.5rem; color:#E2E8F0;'>🔹 월별 가입자 및 유료 전환 수 (단위: 명)</p>", unsafe_allow_html=True)
                fig_join = go.Figure()
                fig_join.add_trace(go.Bar(x=df_single['월'], y=df_single['전체가입자'], name='전체가입자', marker_color='#475569', opacity=0.5))
                fig_join.add_trace(go.Bar(x=df_single['월'], y=df_single['광고가입자'], name='광고가입자', marker_color='#0EA5E9'))
                fig_join.add_trace(go.Bar(x=df_single['월'], y=df_single['신규유료고객수'], name='신규유료고객수', marker_color='#D946EF'))
                fig_join.update_layout(barmode='overlay', height=220, margin=dict(t=10, b=10, l=10, r=10),
                                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#E2E8F0')),
                                       xaxis=dict(showgrid=False, tickfont=dict(color='#94A3B8')),
                                       yaxis=dict(tickformat=',.0f', ticksuffix='명', gridcolor='#334155', tickfont=dict(color='#94A3B8')),
                                       hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                st.plotly_chart(fig_join, use_container_width=True)
                
        with col2:
            if show_yoy:
                # 2025 vs 2026 누적 매출액 비교 라인
                st.markdown("<p style='font-weight:600; margin-top:1rem; color:#E2E8F0;'>🔹 전년 동기 대비 신규 누적 매출 비교 (단위: 억원)</p>", unsafe_allow_html=True)
                fig_rev = go.Figure()
                fig_rev.add_trace(go.Scatter(x=df_y_25['월'], y=df_y_25['신규누적매출']/100000000, name='2025년 누적 매출',
                                             line=dict(color='#94A3B8', width=2, dash='dot', shape='spline')))
                fig_rev.add_trace(go.Scatter(x=df_y_26['월'], y=df_y_26['신규누적매출']/100000000, name='2026년 누적 매출',
                                             line=dict(color='#38BDF8', width=3.5, shape='spline')))
                fig_rev.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10),
                                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#E2E8F0')),
                                      xaxis=dict(showgrid=False, tickfont=dict(color='#94A3B8')),
                                      yaxis=dict(tickformat='.1f', ticksuffix='억', gridcolor='#334155', tickfont=dict(color='#94A3B8')),
                                      hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                st.plotly_chart(fig_rev, use_container_width=True)
                
                # 2025 vs 2026 ROAS 효율 비교 트렌드
                st.markdown("<p style='font-weight:600; margin-top:1.5rem; color:#E2E8F0;'>🔹 전년 동기 대비 광고 효율(ROAS) 비교 (단위: %)</p>", unsafe_allow_html=True)
                fig_roas = go.Figure()
                fig_roas.add_trace(go.Scatter(x=df_y_25['월'], y=df_y_25['광고비ROAS'], name='2025년 ROAS',
                                              line=dict(color='#94A3B8', width=2, dash='dot', shape='spline')))
                fig_roas.add_trace(go.Scatter(x=df_y_26['월'], y=df_y_26['광고비ROAS'], name='2026년 ROAS',
                                              line=dict(color='#10B981', width=3.5, shape='spline')))
                fig_roas.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10),
                                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#E2E8F0')),
                                       xaxis=dict(showgrid=False, tickfont=dict(color='#94A3B8')),
                                       yaxis=dict(tickformat=',.0f', ticksuffix='%', gridcolor='#334155', tickfont=dict(color='#94A3B8')),
                                       hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                st.plotly_chart(fig_roas, use_container_width=True)
            else:
                # 단해년도 차트 렌더링 (매출액 및 매체별 상세 CPA 통합)
                st.markdown("<p style='font-weight:600; margin-top:1rem; color:#E2E8F0;'>🔹 월별 매출 규모 및 성과 추이 (단위: 억원)</p>", unsafe_allow_html=True)
                fig_financial = go.Figure()
                fig_financial.add_trace(go.Scatter(x=df_single['월'], y=df_single['신규당월매출'] / 100000000, name='신규당월매출', 
                                                   fill='tozeroy', fillcolor='rgba(56, 189, 248, 0.15)', line=dict(color='#38BDF8', width=3, shape='spline')))
                fig_financial.add_trace(go.Scatter(x=df_single['월'], y=df_single['신규누적매출'] / 100000000, name='신규누적매출', yaxis='y2', line=dict(color='#818CF8', width=3, shape='spline')))
                fig_financial.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10),
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#E2E8F0')),
                                            xaxis=dict(showgrid=False, tickfont=dict(color='#94A3B8')),
                                            yaxis=dict(tickformat='.1f', ticksuffix='억', gridcolor='#334155', tickfont=dict(color='#94A3B8')),
                                            yaxis2=dict(tickformat='.1f', ticksuffix='억', overlaying='y', side='right', showgrid=False, tickfont=dict(color='#94A3B8')),
                                            hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                st.plotly_chart(fig_financial, use_container_width=True)
                
                # [업그레이드] 월별 CPA 추이에 광고가입자CPA / 유료고객CPA 이외에 네이버CPA와 구글CPA 점선을 함께 오버랩시킵니다!
                st.markdown("<p style='font-weight:600; margin-top:1.5rem; color:#E2E8F0;'>🔹 월별 가입자 CPA(획득 비용) 추이 (단위: 원)</p>", unsafe_allow_html=True)
                fig_efficiency = go.Figure()
                # 1) 전체 성과 (실선)
                fig_efficiency.add_trace(go.Scatter(x=df_single['월'], y=df_single['광고가입자CPA'], name='전체 광고가입자CPA', line=dict(color='#F59E0B', width=2.5, shape='spline')))
                fig_efficiency.add_trace(go.Scatter(x=df_single['월'], y=df_single['유료고객CPA'], name='전체 유료고객CPA', line=dict(color='#EF4444', width=2.5, shape='spline')))
                # 2) 매체별 상세 성과 (점선 - 가독성을 저해하지 않으면서 피드백 제공)
                fig_efficiency.add_trace(go.Scatter(x=df_single['월'], y=df_single['네이버CPA'], name='네이버 CPA', line=dict(color='#03C75A', width=2, dash='dot', shape='spline')))
                fig_efficiency.add_trace(go.Scatter(x=df_single['월'], y=df_single['구글CPA'], name='구글 CPA', line=dict(color='#4285F4', width=2, dash='dot', shape='spline')))
                
                fig_efficiency.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10),
                                             paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#E2E8F0')),
                                             xaxis=dict(showgrid=False, tickfont=dict(color='#94A3B8')),
                                             yaxis=dict(tickformat=',.0f', ticksuffix='원', gridcolor='#334155', tickfont=dict(color='#94A3B8')),
                                             hoverlabel=dict(bgcolor='#1E293B', font_size=12, font_color='#FFFFFF'))
                st.plotly_chart(fig_efficiency, use_container_width=True)
                
        st.markdown("<br><hr style='border-top:1px solid #334155; opacity:0.3;'><br>", unsafe_allow_html=True)

    # ==========================================
    # --- [INTERFACE RENDERING PIPELINE] ---
    # ==========================================
    show_yoy_mode = ("비교" in year_mode)
    
    with tabs[0]:
        agg_cols = ['전체매출', '전체광고비', '네이버광고비', '구글광고비', '광고가입자', 
                    '네이버가입자', '구글가입자', '전체가입자', '신규유료고객수', '신규당월매출', '매출', '신규누적매출',
                    '네이버CPA', '구글CPA']
        
        df_all_2025 = raw_data[raw_data['연도'] == '2025'].groupby('월')[agg_cols].sum().reset_index()
        df_all_2026 = raw_data[raw_data['연도'] == '2026'].groupby('월')[agg_cols].sum().reset_index()
        
        # 전체 통합의 ROAS는 가중 평균 적용
        df_all_2025_roas = raw_data[raw_data['연도'] == '2025'].groupby('월')['광고비ROAS'].mean().reset_index()
        df_all_2026_roas = raw_data[raw_data['연도'] == '2026'].groupby('월')['광고비ROAS'].mean().reset_index()
        
        for df_target, df_roas in [(df_all_2025, df_all_2025_roas), (df_all_2026, df_all_2026_roas)]:
            if not df_target.empty:
                df_target['광고가입자CPA'] = (df_target['전체광고비'] / df_target['광고가입자']).fillna(0)
                df_target['유료고객CPA'] = (df_target['전체광고비'] / df_target['신규유료고객수']).fillna(0)
                df_target['유료고객전환율'] = (df_target['신규유료고객수'] / df_target['광고가입자'] * 100).fillna(0)
                
                # [가중 연산 패치] 전체 통합 탭의 매체별 CPA는 각 매체별 총 합산 광고비와 가입자 수를 기준으로 정밀히 새로 구합니다.
                df_target['네이버CPA'] = (df_target['네이버광고비'] / df_target['네이버가입자']).fillna(0).replace([float('inf'), float('-inf')], 0)
                df_target['구글CPA'] = (df_target['구글광고비'] / df_target['구글가입자']).fillna(0).replace([float('inf'), float('-inf')], 0)
                
                # 병합 매칭 후 ROAS 주입
                df_target['광고비ROAS'] = df_roas['광고비ROAS']
                
                df_target['월_idx'] = df_target['월'].str.extract(r'(\d+)').astype(float).fillna(0)
                df_target.sort_values('월_idx', inplace=True)
                
        # 병합 데이터 구축
        df_all_merged = pd.concat([df_all_2025.assign(연도='2025'), df_all_2026.assign(연度='2026')], ignore_index=True)
        df_all_merged['연도'] = df_all_merged['연도'].fillna(df_all_merged['연度']).astype(str)
        df_all_merged.drop(columns=['연度'], errors='ignore', inplace=True)
        
        if show_yoy_mode:
            generate_bi_charts(df_all_merged, "전체 서비스 통합 전년 동기 대비 비교 분석 (YoY)", show_yoy=True)
        else:
            generate_bi_charts(df_all_merged, f"전체 서비스 통합 보고 [{year_mode}]", show_yoy=False)

    def render_service_view(tab_obj, s_name):
        with tab_obj:
            df_s_2025 = raw_data[(raw_data['서비스명'] == s_name) & (raw_data['연도'] == '2025')].copy()
            df_s_2026 = raw_data[(raw_data['서비스명'] == s_name) & (raw_data['연도'] == '2026')].copy()
            
            for df_target in [df_s_2025, df_s_2026]:
                if not df_target.empty:
                    # 개별 브랜드 뷰에서도 수치 정밀화
                    df_target['네이버CPA'] = (df_target['네이버광고비'] / df_target['네이버가입자']).fillna(0).replace([float('inf'), float('-inf')], 0)
                    df_target['구글CPA'] = (df_target['구글광고비'] / df_target['구글가입자']).fillna(0).replace([float('inf'), float('-inf')], 0)
                    
                    df_target['월_idx'] = df_target['월'].str.extract(r'(\d+)').astype(float).fillna(0)
                    df_target.sort_values('월_idx', inplace=True)
                    
            df_s_merged = pd.concat([df_s_2025, df_s_2026], ignore_index=True)
            
            if show_yoy_mode:
                generate_bi_charts(df_s_merged, f"{s_name} 서비스 전년 동기 대비 비교 분석 (YoY)", show_yoy=True)
            else:
                generate_bi_charts(df_s_merged, f"{s_name} Service 보고 [{year_mode}]", show_yoy=False)

    render_service_view(tabs[1], "뿌리오")
    render_service_view(tabs[2], "반값문자")
    render_service_view(tabs[3], "알뜰문자")
    render_service_view(tabs[4], "문자매니아")

except Exception as e:
    st.error(f"⚠️ BI 시각화 가동 엔진 내부 예외 제어 실패: {str(e)}")
