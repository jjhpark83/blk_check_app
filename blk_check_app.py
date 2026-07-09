import streamlit as style
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

# ===========================================================================
# 1. 환경 설정 및 구글 시트 주소 (★본인 주소로 변경 필수★)
# ===========================================================================
# ⚠️ 주의: 구글 시트 우측 상단 [공유] -> 링크가 있는 모든 사용자 항목이 
# 반드시 "편집자"로 설정되어 있어야 Streamlit 앱에서 저장이 가능합니다.
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/12i27S6rTm_scIeUQ1k7MbSCHpr_qrhkhrB8yhxU0JQg/edit?usp=sharing"

# 🔗 [★여기에 아까 복사한 구글 웹앱 URL 주소를 붙여넣으세요★]
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRuaayPJrl-gHYRE9fJbmrbtKlucciupcjqP7taGjCOdTe79gc4dXBnrSDBVnot6ijhQ/exec"


# 페이지 와이드 모드 설정
style.set_page_config(layout="wide")
style.title("⚙️ 블록검사 공정별 특이사항 관리 시스템")

# 구글 시트 고유 ID 추출 함수
def get_sheet_id(url):
    try:
        return url.split("/d/")[1].split("/")[0]
    except Exception:
        return None

SHEET_ID = get_sheet_id(GOOGLE_SHEET_URL)

# ===========================================================================
# 2. 데이터 로드 및 저장 함수 (gspread/패키지 의존성 없이 순수 웹 API 우회)
# ===========================================================================
def load_data_from_sheets():
    fallback_df = pd.DataFrame(columns=['호선', '블록', '공정', '세부내용', '등록일', '완료일', '담당자'])
    if not SHEET_ID:
        style.error("❌ 올바른 구글 시트 URL 주소가 아닙니다.")
        return fallback_df
        
    try:
        # CSV 내보내기 엔드포인트를 활용하여 구글 드라이브 라이브러리 없이 실시간 로드
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
        
        # 주소 캐싱 메커니즘을 피하기 위해 임의의 타임스탬프 파라미터 추가 (실시간 동기화 보장)
        live_url = f"{csv_url}&t={int(datetime.now().timestamp())}"
        
        df = pd.read_csv(live_url)
        
        if df.empty:
            return fallback_df
            
        # 데이터 공백 정제 및 타입 일치
        df['호선'] = df['호선'].astype(str).str.strip().str.replace(".0", "", regex=False)
        df['블록'] = df['블록'].astype(str).str.strip()
        df['공정'] = df['공정'].fillna("").astype(str).str.strip()
        df['세부내용'] = df['세부내용'].fillna("").astype(str)
        df['담당자'] = df['담당자'].fillna("").astype(str).str.strip()
        
        # 날짜 예외 처리 및 포맷 변환
        df['등록일'] = pd.to_datetime(df['등록일'], errors='coerce').dt.date
        df['완료일'] = pd.to_datetime(df['완료일'], errors='coerce').dt.date
        return df
    except Exception as e:
        style.error(f"❌ 구글 드라이브 실시간 자료 로드 실패: {e}")
        return fallback_df

def save_data_to_sheets(payload_data):
    """
    구글 웹앱 API로 방금 입력/수정한 한 줄의 데이터를 
    실제 구글 드라이브 스프레드시트에 즉시 물리적으로 전송(Write)합니다.
    """
    try:
        if "여기에_본인의_웹앱" in GOOGLE_WEBAPP_URL or not GOOGLE_WEBAPP_URL:
            return False
            
        # 구글 Apps Script로 데이터 POST 전송
        response = requests.post(GOOGLE_WEBAPP_URL, json=payload_data, timeout=5)
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        style.sidebar.error(f"🌐 구글 전송 오류: {e}")
        return False

# 🚨 세션 스테이트를 활용하여 실시간 추가/수정 데이터 보존 데이터베이스 구축
if 'live_data' not in style.session_state:
    style.session_state.live_data = load_data_from_sheets()

df = style.session_state.live_data

# ===========================================================================
# 3. 사이드바: 🆕 특이사항 신규 등록 및 완료 처리 섹션
# ===========================================================================
style.sidebar.header("🆕 특이사항 등록 / 완료 처리")

if 'edit_index' not in style.session_state:
    style.session_state.edit_index = None

if style.session_state.edit_index is not None:
    style.sidebar.warning(f"⚠️ 현재 {style.session_state.edit_index + 1}번 행 수정 모드입니다.")
    idx = style.session_state.edit_index
    default_hosun = str(df.loc[idx, '호선']) if idx < len(df) else ""
    default_block = str(df.loc[idx, '블록']) if idx < len(df) else ""
    default_process = str(df.loc[idx, '공정']) if idx < len(df) else ""
    default_content = str(df.loc[idx, '세부내용']) if idx < len(df) else ""
    default_reg_date = df.loc[idx, '등록일'] if idx < len(df) and pd.notna(df.loc[idx, '등록일']) else datetime.now().date()
    
    # 가끔 날짜가 문자열로 들어오는 경우 예외 처리
    if isinstance(default_reg_date, str):
        try: default_reg_date = datetime.strptime(default_reg_date, '%Y-%m-%d').date()
        except: default_reg_date = datetime.now().date()
        
    default_is_comp = pd.notna(df.loc[idx, '완료일']) and str(df.loc[idx, '완료일']).strip() != "" if idx < len(df) else False
    default_comp_date = df.loc[idx, '완료일'] if default_is_comp else datetime.now().date()
    if isinstance(default_comp_date, str) and default_is_comp:
        try: default_comp_date = datetime.strptime(default_comp_date, '%Y-%m-%d').date()
        except: default_comp_date = datetime.now().date()
        
    default_worker = str(df.loc[idx, '담당자']) if idx < len(df) else ""
    submit_label = "💾 수정완료 (저장)"
else:
    default_hosun = ""
    default_block = ""
    default_process = ""
    default_content = ""
    default_reg_date = datetime.now().date()
    default_is_comp = False
    default_comp_date = datetime.now().date()
    default_worker = ""
    submit_label = "📝 신규 등록하기"

with style.sidebar.form(key='register_form', clear_on_submit=True):
    input_hosun = style.text_input("호선 (예: 8247)", value=default_hosun)
    input_block = style.text_input("블록 (예: F51P0)", value=default_block)
    input_process = style.text_input("공정 (소조, 조립, 선PE 등)", value=default_process)
    input_content = style.text_area("세부내용", value=default_content)
    input_reg_date = style.date_input("등록일", value=default_reg_date)
    
    is_completed = style.checkbox("체크 시 완료 처리 (완료일 입력)", value=default_is_comp)
    input_comp_date = style.date_input("완료일", value=default_comp_date) if is_completed else None
    
    input_worker = style.text_input("담당자", value=default_worker)
    submit_btn = style.form_submit_button(label=submit_label)

if style.session_state.edit_index is not None:
    if style.sidebar.button("❌ 수정 취소"):
        style.session_state.edit_index = None
        style.rerun()

if submit_btn:
    if input_hosun and input_block and input_content:
        # 💡 구글 시트로 보낼 한 줄 데이터 패키지 만들기
        payload = {
            "hosun": input_hosun.strip(),
            "block": input_block.strip(),
            "process": input_process.strip(),
            "content": input_content,
            "reg_date": str(input_reg_date),
            "comp_date": str(input_comp_date) if is_completed else "",
            "worker": input_worker.strip()
        }
        
        # 실제 구글 드라이브 시트에 한 줄 밀어넣기 시도!
        success = save_data_to_sheets(payload)
        
        if success:
            # 구글 시트 저장 성공 시 화면 대시보드 데이터프레임 갱신
            if style.session_state.edit_index is not None:
                df.loc[style.session_state.edit_index] = [input_hosun.strip(), input_block.strip(), input_process.strip(), input_content, input_reg_date, input_comp_date if is_completed else "", input_worker.strip()]
                style.sidebar.success("💾 구글 스프레드시트 파일 수정 완료!")
                style.session_state.edit_index = None
            else:
                new_row = pd.DataFrame([[input_hosun.strip(), input_block.strip(), input_process.strip(), input_content, input_reg_date, input_comp_date if is_completed else "", input_worker.strip()]], columns=df.columns)
                df = pd.concat([df, new_row], ignore_index=True)
                style.sidebar.success("🎉 구글 스프레드시트 파일 신규 등록 완료!")
            
            style.session_state.live_data = df
            style.rerun()
        else:
            style.sidebar.error("❌ 구글 웹앱 연결 실패! URL 주소나 배포 버전을 확인하세요.")
    else:
        style.sidebar.error("⚠️ 호선, 블록, 세부내용은 필수 입력 사항입니다.")
# ===========================================================================
# 4. 메인 화면: 📊 통계 그래프 존
# ===========================================================================
style.subheader("📊 실시간 공정 현황 통계")
if not df.empty:
    col1, col2 = style.columns(2)
    uncompleted_df = df[df['완료일'].isna() | (df['완료일'] == "")]
    
    with col1:
        if not uncompleted_df.empty:
            process_counts = uncompleted_df['공정'].value_counts().reset_index()
            process_counts.columns = ['공정', '미완료 건수']
            fig1 = px.bar(process_counts, x='공정', y='미완료 건수', title="🔥 공정별 미완료 특이사항 건수", color='공정')
            style.plotly_chart(fig1, use_container_width=True)
        else:
            style.info("현재 미완료된 특이사항이 없습니다.")
            
    with col2:
        if '호선' in df.columns and not uncompleted_df.empty:
            hosun_counts = uncompleted_df['호선'].value_counts().reset_index()
            hosun_counts.columns = ['호선', '미완료 건수']
            fig2 = px.pie(hosun_counts, values='미완료 건수', names='호선', title="🚢 호선별 미완료 특이사항 비중", hole=0.3)
            style.plotly_chart(fig2, use_container_width=True)
        else:
            style.info("현재 미완료된 특이사항이 없습니다.")
else:
    style.info("통계를 표시할 데이터가 아직 없습니다.")

style.markdown("---")

# ===========================================================================
# 5. 메인 화면: 🔍 조건별 조회 및 데이터프레임 연동 존
# ===========================================================================
style.subheader("🔍 특이사항 검색 및 전체 조회")

if 'selected_hosun' not in style.session_state:
    style.session_state.selected_hosun = "전체"
if 'selected_block' not in style.session_state:
    style.session_state.selected_block = "전체"

available_hosun = sorted(list(df['호선'].dropna().unique())) if not df.empty else []
available_block = sorted(list(df['블록'].dropna().unique())) if not df.empty else []

if style.session_state.selected_hosun != "전체" and not df.empty:
    available_block = sorted(list(df[df['호선'] == style.session_state.selected_hosun]['블록'].dropna().unique()))
if style.session_state.selected_block != "전체" and not df.empty:
    available_hosun = sorted(list(df[df['블록'] == style.session_state.selected_block]['호선'].dropna().unique()))

all_hosun_options = ["전체"] + available_hosun
all_block_options = ["전체"] + available_block

c1, c2 = style.columns(2)
with c1:
    search_hosun = style.selectbox(
        "🚢 호선 선택", 
        all_hosun_options, 
        index=all_hosun_options.index(style.session_state.selected_hosun) if style.session_state.selected_hosun in all_hosun_options else 0,
        key="hosun_box"
    )
with c2:
    search_block = style.selectbox(
        "🧱 블록 선택", 
        all_block_options, 
        index=all_block_options.index(style.session_state.selected_block) if style.session_state.selected_block in all_block_options else 0,
        key="block_box"
    )

show_completed = style.checkbox("✅ 완료된 특이사항 항목도 조회 목록에 포함하기", value=False)

if search_hosun != style.session_state.selected_hosun or search_block != style.session_state.selected_block:
    style.session_state.selected_hosun = search_hosun
    style.session_state.selected_block = search_block
    style.rerun()

view_df = df.copy()
view_df['원래번호'] = view_df.index

if not view_df.empty:
    if search_hosun == "전체" and search_block == "전체":
        if not show_completed:
            view_df = view_df[(view_df['완료일'].isna()) | (view_df['완료일'] == "")]
            style.info("💡 현재 [미완료 항목] 전체 조회 모드입니다.")
        else:
            style.success(f"🎯 현재 [전체 데이터] 조회 모드입니다. 총 {len(view_df)}건 표시")
    else:
        if search_hosun != "전체":
            view_df = view_df[view_df['호선'] == search_hosun]
        if search_block != "전체":
            view_df = view_df[view_df['블록'] == search_block]
        style.success(f"🎯 검색 결과: 총 {len(view_df)}건 발견")

style.markdown("👇 **수정 또는 완료 처리할 행을 테이블에서 마우스로 클릭하면 좌측 사이드바로 불러옵니다.**")
event = style.dataframe(
    view_df.drop(columns=['원래번호']) if not view_df.empty else view_df, 
    use_container_width=True, 
    hide_index=True,
    selection_mode="single-row",
    on_select="rerun"
)

if event and 'rows' in event.get('selection', {}) and event['selection']['rows']:
    selected_row_idx = event['selection']['rows'][0]
    actual_df_idx = view_df.iloc[selected_row_idx]['원래번호']
    style.session_state.edit_index = actual_df_idx
    style.rerun()

# ===========================================================================
# 6. 메인 화면: 📥 데이터 다운로드 존
# ===========================================================================
if not view_df.empty:
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        view_df.drop(columns=['원래번호']).to_excel(writer, index=False, sheet_name='Sheet1')
    
    style.download_button(
        label="📥 현재 조회된 목록 엑셀 다운로드",
        data=buffer.getvalue(),
        file_name=f"block_check_filtered_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )
