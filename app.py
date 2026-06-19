# project2.py  –  실행: streamlit run project2.py
# PROJECT 02  |  친환경 선박 탄소 배출량(CII) 등급 모니터링 웹 앱
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import matplotlib

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 스타일
# -----------------------------------------------------------------------------
st.set_page_config(page_title="친환경 선박 CII 모니터링 시스템", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #1E3A8A; margin-bottom: 20px; }
    .sub-title { font-size: 18px; color: #4B5563; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🚢 친환경 선박 탄소 배출량(CII) 등급 모니터링 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">선박의 운항 데이터를 기반으로 연간 탄소집약도지수(CII)를 계산하고 등급을 모니터링합니다.</div>', unsafe_allow_html=True)
st.sidebar.header("⚓ 선박 스펙 및 운항 데이터 입력")

# -----------------------------------------------------------------------------
# 2. 사이드바 - 데이터 입력 방식 선택 (직접 입력 vs CSV 업로드)
# -----------------------------------------------------------------------------
data_source = st.sidebar.radio("데이터 입력 방식 선택", ["직접 입력", "CSV 파일 업로드"])

# 선박 종류별 이산화탄소 배출 계수 (MGO: 3.206, HFO: 3.114 등 평균치 가정)
FUEL_FACTORS = {"MGO/MDO": 3.206, "HFO": 3.114, "LNG": 2.750}

if data_source == "직접 입력":
    ship_name = st.sidebar.text_input("선박명", "해양호 (Ocean Blue)")
    ship_type = st.sidebar.selectbox("선박 종류", ["Bulk Carrier", "Container Ship", "Tanker", "LNG Carrier"])
    gt = st.sidebar.number_input("총톤수 (GT)", min_value=1000, max_value=300000, value=50000, step=1000)
    distance = st.sidebar.number_input("연간 운항 거리 (Nautical Miles, nm)", min_value=100, value=60000, step=500)
    fuel_type = st.sidebar.selectbox("사용 연료 종류", list(FUEL_FACTORS.keys()))
    fuel_consumption = st.sidebar.number_input("연간 연료 소모량 (Tons)", min_value=1, value=4500, step=50)
    
    # 단일 데이터 프레임 생성
    co2_emissions = fuel_consumption * FUEL_FACTORS[fuel_type]
    # Attained CII = (CO2 * 10^6) / (GT * Distance) -> gCO2 / GT*nm
    attained_cii = (co2_emissions * 1e6) / (gt * distance) if distance > 0 else 0
    
    input_df = pd.DataFrame([{
        "선박명": ship_name, "선박 종류": ship_type, "총톤수(GT)": gt, 
        "운항 거리(nm)": distance, "연료 소모량(Tons)": fuel_consumption, 
        "CO2 배출량(Tons)": co2_emissions, "Attained CII": attained_cii
    }])

else:
    uploaded_file = st.sidebar.file_uploader("CSV 파일을 업로드하세요.", type=["csv"])
    if uploaded_file is not None:
        input_df = pd.read_csv(uploaded_file)
        # CSV 필수 컬럼 계산 및 검증
        if "연료 소모량(Tons)" in input_df.columns and "총톤수(GT)" in input_df.columns and "운항 거리(nm)" in input_df.columns:
            input_df["CO2 배출량(Tons)"] = input_df["연료 소모량(Tons)"] * 3.17  # 평균 계수 적용
            input_df["Attained CII"] = (input_df["CO2 배출량(Tons)"] * 1e6) / (input_df["총톤수(GT)"] * input_df["운항 거리(nm)"])
        else:
            st.error("CSV 파일에 '총톤수(GT)', '운항 거리(nm)', '연료 소모량(Tons)' 컬럼이 포함되어 있어야 합니다.")
            st.stop()
    else:
        st.info("💡 우측 화면을 확인하려면 좌측 사이드바에서 샘플 CSV를 업로드하거나 '직접 입력'을 선택해 주세요.")
        # 샘플 데이터 제공
        sample_data = pd.DataFrame({
            "선박명": ["A호", "B호", "C호"], "선박 종류": ["Container Ship", "Bulk Carrier", "Tanker"],
            "총톤수(GT)": [80000, 45000, 110000], "운항 거리(nm)": [70000, 55000, 48000], "연료 소모량(Tons)": [6200, 3100, 5800]
        })
        st.markdown("### 📋 업로드용 CSV 파일 예시 포맷")
        st.dataframe(sample_data)
        st.stop()

# -----------------------------------------------------------------------------
# 3. CII 등급 판정 로직 (선박별 간이 수식 적용)
# -----------------------------------------------------------------------------
def determine_cii_grade(cii, ship_type):
    # 선박 종류별 기준선(Required CII) 가상 매핑 (원래는 GT 기반 수식 적용)
    base_cii = {"Bulk Carrier": 6.5, "Container Ship": 9.0, "Tanker": 5.5, "LNG Carrier": 7.0}
    ref = base_cii.get(ship_type, 7.0)
    
    # 기준선 대비 실제 CII 비율로 등급 산정
    ratio = cii / ref
    if ratio <= 0.85: return "A", "#10B981"  # 초록
    elif ratio <= 0.95: return "B", "#34D399" # 연초록
    elif ratio <= 1.05: return "C", "#FBBF24" # 노랑
    elif ratio <= 1.18: return "D", "#F97316" # 주황
    else: return "E", "#EF4444"               # 빨강

# 등급 계산 가미
input_df["CII 등급"], input_df["Color"] = zip(*input_df.apply(lambda row: determine_cii_grade(row["Attained CII"], row["선박 종류"]), axis=1))

# -----------------------------------------------------------------------------
# 4. 메인 화면 시각화 및 결과 레이아웃
# -----------------------------------------------------------------------------
# 선택된 선박 (복수 데이터일 경우 첫 번째 선박 기준 대시보드 출력)
selected_ship = input_df.iloc[0]

col1, col2, col3 = st.columns([1, 1, 1.5])

with col1:
    st.metric(label="📊 Attained CII (공식 결과)", value=f"{selected_ship['Attained CII']:.2f} g/GT·nm")
    st.metric(label="🌱 총 CO2 배출량", value=f"{selected_ship['CO2 배출량(Tons)']:.1f} Tons")

with col2:
    grade = selected_ship["CII 등급"]
    color = selected_ship["Color"]
    st.markdown(f"""
        <div style="text-align: center; padding: 20px; border-radius: 10px; background-color: {color}; color: white;">
            <p style="margin:0; font-size: 18px; font-weight: bold;">현재 CII 등급</p>
            <p style="margin:0; font-size: 64px; font-weight: bold;">{grade}</p>
        </div>
    """, unsafe_allow_html=True)

with col3:
    # Plotly를 이용한 Gauge 차트 시각화
    grade_idx = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}[grade]
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = grade_idx,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "CII Grade Gauge (A=1 ~ E=5)", 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [0.5, 5.5], 'tickvals': [1, 2, 3, 4, 5], 'ticktext': ['A', 'B', 'C', 'D', 'E']},
            'bar': {'color': "#1F2937"},
            'steps': [
                {'range': [0.5, 1.5], 'color': "#10B981"},
                {'range': [1.5, 2.5], 'color': "#34D399"},
                {'range': [2.5, 3.5], 'color': "#FBBF24"},
                {'range': [3.5, 4.5], 'color': "#F97316"},
                {'range': [4.5, 5.5], 'color': "#EF4444"}
            ]
        }
    ))
    fig_gauge.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_gauge, width='stretch')

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. 트렌드 분석 및 시뮬레이션 시각화 (Matplotlib / Seaborn)
# -----------------------------------------------------------------------------
st.subheader("📈 선속(Speed) 및 운항 조건 변화에 따른 배출량 추이 시뮬레이션")

# 선속 변화(10노트 ~ 20노트)에 따른 가상 시나리오 데이터 생성
speeds = np.linspace(10, 20, 50)
base_speed = 14.0 # 기준 속도

# 속도 변화에 따른 연료 소모량 및 CII 변동 시뮬레이션 계산
simulated_fuel = selected_ship["연료 소모량(Tons)"] * ((speeds / base_speed) ** 3)
simulated_co2 = simulated_fuel * FUEL_FACTORS.get(selected_ship.get("사용 연료 종류", "MGO/MDO"), 3.17)
simulated_cii = (simulated_co2 * 1e6) / (selected_ship["총톤수(GT)"] * selected_ship["운항 거리(nm)"])

sim_df = pd.DataFrame({
    "Speed (Knots)": speeds,
    "Estimated CII": simulated_cii,
    "CO2 Emissions (Tons)": simulated_co2
})

# --- 1. 테마 설정을 가장 먼저 적용 (폰트 초기화 방지) ---
import seaborn as sns
import matplotlib.pyplot as plt
import platform
from matplotlib import font_manager, rc

sns.set_theme(style="whitegrid")  # 이 코드가 폰트를 초기화하므로 먼저 선언해야 합니다.

# --- 2. OS별 한글 폰트 설정 적용 ---
if platform.system() == 'Windows':
    font_path = "C:/Windows/Fonts/malgun.ttf" # 맑은 고딕
    font_name = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font_name)
elif platform.system() == 'Darwin': # Mac
    rc('font', family='AppleGothic')
else: 
    rc('font', family='NanumGothic')

# 마이너스 부호(-) 깨짐 방지 및 글꼴 부드럽게 설정
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 10

# --- 3. 시각화 그래프 그리기 ---
fig, ax1 = plt.subplots(figsize=(10, 4))

# CII 선 그래프
color = '#1f77b4'
ax1.set_xlabel('Vessel Speed (Knots)', fontweight='bold')
ax1.set_ylabel('Attained CII', color=color, fontweight='bold')
sns.lineplot(data=sim_df, x='Speed (Knots)', y='Estimated CII', ax=ax1, color=color, linewidth=2.5, label='CII')
ax1.tick_params(axis='y', labelcolor=color)

# 등급 경계선 예시 표시 (C등급 마지노선 가정)
ax1.axhline(y=simulated_cii.mean(), color='r', linestyle='--', label='Required CII (Target)')

# CO2 배출량 축 추가
ax2 = ax1.twinx()  
color = '#2ca02c'
ax2.set_ylabel('CO2 Emissions (Tons)', color=color, fontweight='bold')
sns.lineplot(data=sim_df, x='Speed (Knots)', y='CO2 Emissions (Tons)', ax=ax2, color=color, linewidth=2, linestyle=':', label='CO2')
ax2.tick_params(axis='y', labelcolor=color)

# 한글 타이틀 적용
plt.title(f" {selected_ship['선박명']} : 속도 증가에 따른 탄소 배출량 및 CII 지수 변화 (Cubed Law 반영)", fontsize=13, pad=15)
fig.tight_layout()

# 스트림릿에 그래프 출력
st.pyplot(fig)

# -----------------------------------------------------------------------------
# 6. 전체 데이터 테이블 출력
# -----------------------------------------------------------------------------
st.markdown("### 📋 모니터링 대상 데이터 상세")
st.dataframe(input_df.drop(columns=["Color"] if "Color" in input_df.columns else []))
