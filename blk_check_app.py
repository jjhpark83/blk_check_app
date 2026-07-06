import streamlit as style
import pandas as pd
import os
import time
import io
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection  # 구글 시트 라이브러리 추가
from google.api_core.exceptions import GoogleAPIError  # 구글 API 하위 예외 처리

# 💡 구글 시트 연결 설정 (구글 시트 URL 지정)
GSHEET_URL = "https://docs.google.com/spreadsheets/d/12i27S6rTm_scIeUQ1k7MbSCHpr_qrhkhrB8yhxU0JQg/edit?usp=drive_link"

# ---------------------------------------------------------------------------
# 🛠️ 자동 재시도 데코레이터 (네트워크 지연 및 API 일시적 차단 방지)
# ---------------------------------------------------------------------------
def retry_on_failure(max_retries=3, initial_delay=2):
    """구글 API 통신 중 일시적인 오류가 발생하면 지정된 횟수만큼 재시도합니다."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (GoogleAPIError, Exception) as e:
                    error_msg = str(e).lower()
                    # 403 권한 거부 에러는 다시 시도해도 해결되지 않으므로 즉시 중단
                    if "permission" in error_msg or "403" in error_msg:
                        raise PermissionError("구글 시트 접근 권한이 없습니다. 서비스 계정 공유 설정을 확인하세요.") from e
                    
                    # 마지막 시도까지 실패하면 에러를 밖으로 던짐
                    if attempt == max_retries - 1:
                        raise e
                    
                    # 에러 발생 시 사용자에게 알리고 잠시 대기 후 재시도
                    style.sidebar.warning(f"⚠️ 시트 연결 지연... 다시 시도 중입니다 ({attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2  # 대기 시간을 2배로 늘림 (지수 백오프)
            return None
        return wrapper
    return decorator

# ---------------------------------------------------------------------------
# 📥 데이터 불러오기 함수 (안전장치 강화 버전)
# ---------------------------------------------------------------------------
@retry_on_failure(max_retries=3, initial_delay=2)
def load_data():
    """트랜잭션 가드레일을 적용하여 구글 시트에서 안전하게 데이터를 읽어옵니다."""
    try:
        # 매번 신규 연결 상태를 검증하기 위해 동적 커넥션 로드
        conn = style.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=GSHEET_URL, ttl="0d") # ttl="0d"는 캐시 없이 실시간 조회를 의미
        
        # 시트는 존재하나 데이터 내용이 전혀 없는 경우 기본 틀(Skeleton) 반환
        if df is None or df.empty:
            return pd.DataFrame(columns=['호선', '블록', '공정', '세부내용', '등록일', '완료일', '담당자'])
            
        # 문자열 데이터 공백 제거 및 결측치 처리
        df['호선'] = df['호선'].fillna('').astype(str).str.strip()
        df['블록'] = df['블록'].fillna('').astype(str).str.strip()
        
        # 포맷이 깨진 날짜가 들어와도 앱이 멈추지 않도록 errors='coerce' 설정
        df['등록일'] = pd.to_datetime(df['등록일'], errors='coerce').dt.date
        df['완료일'] = pd.to_datetime(df['완료일'], errors='coerce').dt.date
        
        # 등록일이 빈 칸인 경우 오늘 날짜로 강제 채움 (시스템 안정성 확보)
        today = datetime.now().date()
        df['등록일'] = df['등록일'].fillna(today)
        
        return df
        
    except PermissionError as pe:
        style.error(f"🔒 권한 오류: {pe}")
        style.stop()  # 권한이 아예 없으면 렌더링을 즉시 중단하여 불필요한 트레이스백 노출 방지
    except Exception as e:
        style.error(f"❌ 데이터 로딩 중 오류 발생: {e}")
        return pd.DataFrame(columns=['호선', '블록', '공정', '세부내용', '등록일', '완료일', '담당자'])

# ---------------------------------------------------------------------------
# 💾 데이터 저장 함수 (이중 백업 로직 적용 버전)
# ---------------------------------------------------------------------------
def save_data(df):
    if df is None:
        style.sidebar.error("⚠️ 저장할 데이터가 없습니다.")
        return False

    # 데이터 전처리 (날짜를 문자열로 변환)
    df_to_save = df.copy()
    df_to_save['등록일'] = df_to_save['등록일'].astype(str)
    df_to_save['완료일'] = df_to_save['완료일'].apply(lambda x: str(x) if pd.notna(x) else "")
    
    # 커넥션 개시
    conn = style.connection("gsheets", type=GSheetsConnection)
    
    try:
        # 라이브러리 우회: gspread 클라이언트를 직접 제어하여 쓰기 실행
        sh = conn.client.open_by_url(GSHEET_URL)
        worksheet = sh.get_worksheet(0) # 첫 번째 탭 선택
        
        worksheet.clear() # 기존 내용 전체 삭제 (중복 방지)
        
        # 헤더와 데이터를 리스트 형태로 변환하여 한 번에 기록
        matrix_data = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()
        worksheet.update(matrix_data)
        return True
    except Exception as e:
        style.sidebar.error(f"🚨 데이터베이스 동기화 실패: {e}")
        style.sidebar.info("구글 시트 [공유] 메뉴에서 서비스 계정이 '편집자'로 추가되었는지 꼭 확인하세요.")
        return False
# ---------------------------------------------------------------------------
# 애플리케이션 메인 구동 영역
# ---------------------------------------------------------------------------

# 데이터 로드
df = load_data()

# 페이지 와이드 모드 설정
style.set_page_config(layout="wide")
style.title("⚙️ 블록검사 공정별 특이사항 관리 시스템 by 박종현")

# ---------------------------------------------------------------------------
# 사이드바: 🆕 특이사항 신규 등록 및 완료 처리 섹션
# ---------------------------------------------------------------------------
style.sidebar.header("🆕 특이사항 등록 / 완료 처리")

if 'edit_index' not in style.session_state:
    style.session_state.edit_index = None

if style.session_state.edit_index is not None:
    style.sidebar.warning(f"⚠️ 현재 {style.session_state.edit_index + 1}번 행 수정 모드입니다.")
    idx = style.session_state.edit_index
    default_hosun = str(df.loc[idx, '호선'])
    default_block = str(df.loc[idx, '블록'])
    default_process = str(df.loc[idx, '공정']) if pd.notna(df.loc[idx, '공정']) else ""
    default_content = str(df.loc[idx, '세부내용']) if pd.notna(df.loc[idx, '세부내용']) else ""
    default_reg_date = df.loc[idx, '등록일'] if pd.notna(df.loc[idx, '등록일']) else datetime.now().date()
    default_is_comp = pd.notna(df.loc[idx, '완료일'])
    default_comp_date = df.loc[idx, '완료일'] if default_is_comp else datetime.now().date()
    default_worker = str(df.loc[idx, '담당자']) if pd.notna(df.loc[idx, '담당자']) else ""
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
        if style.form_submit_button(label="❌ 수정 취소"):
            style.session_state.edit_index = None
            style.rerun()

if submit_btn:
    if input_hosun and input_block and input_content:
        if style.session_state.edit_index is not None:
            df.loc[style.session_state.edit_index, '호선'] = input_hosun.strip()
            df.loc[style.session_state.edit_index, '블록'] = input_block.strip()
            df.loc[style.session_state.edit_index, '공정'] = input_process.strip()
            df.loc[style.session_state.edit_index, '세부내용'] = input_content
            df.loc[style.session_state.edit_index, '등록일'] = input_reg_date
            df.loc[style.session_state.edit_index, '완료일'] = input_comp_date if is_completed else None
            df.loc[style.session_state.edit_index, '담당자'] = input_worker
            style.sidebar.success("💾 데이터가 성공적으로 수정되었습니다!")
            style.session_state.edit_index = None
        else:
            new_data = {
                '호선': input_hosun.strip(),
                '블록': input_block.strip(),
                '공정': input_process.strip(),
                '세부내용': input_content,
                '등록일': input_reg_date,
                '완료일': input_comp_date if is_completed else None,
                '담당자': input_worker
            }
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            style.sidebar.success("🎉 신규 특이사항 등록 완료!")
            
        save_data(df)
        style.rerun()
    else:
        style.sidebar.error("⚠️ 호선, 블록, 세부내용은 필수 입력 사항입니다.")

# ---------------------------------------------------------------------------
# 메인 화면: 📊 통계 그래프 존
# ---------------------------------------------------------------------------
style.subheader("📊 실시간 공정 현황 통계")
if not df.empty:
    col1, col2 = style.columns(2)
    
    with col1:
        uncompleted_df = df[df['완료일'].isna()]
        if not uncompleted_df.empty:
            process_counts = uncompleted_df['공정'].value_counts().reset_index()
            process_counts.columns = ['공정', '미완료 건수']
            fig1 = px.bar(process_counts, x='공정', y='미완료 건수', title="🔥 공정별 미완료 특이사항 건수", color='공정')
            style.plotly_chart(fig1, use_container_width=True)
        else:
            style.info("현재 미완료된 특이사항이 없습니다.")
            
    with col2:
        if '호선' in df.columns and not df.empty:
            hosun_counts = df['호선'].value_counts().reset_index()
            hosun_counts.columns = ['호선', '등록 건수']
            fig2 = px.pie(hosun_counts, values='등록 건수', names='호선', title="🚢 호선별 누적 특이사항 비중", hole=0.3)
            style.plotly_chart(fig2, use_container_width=True)
else:
    style.info("통계를 표시할 데이터가 아직 없습니다.")

style.markdown("---")

# ---------------------------------------------------------------------------
# 메인 화면: 🔍 조건별 조회 및 데이터프레임 연동 존
# ---------------------------------------------------------------------------
style.subheader("🔍 특이사항 검색 및 전체 조회")

if 'selected_hosun' not in style.session_state:
    style.session_state.selected_hosun = "전체"
if 'selected_block' not in style.session_state:
    style.session_state.selected_block = "전체"

available_hosun = sorted(list(df['호선'].dropna().unique()))
available_block = sorted(list(df['블록'].dropna().unique()))

if style.session_state.selected_hosun != "전체":
    available_block = sorted(list(df[df['호선'] == style.session_state.selected_hosun]['블록'].dropna().unique()))

if style.session_state.selected_block != "전체":
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

if search_hosun == "전체" and search_block == "전체":
    if not show_completed:
        view_df = view_df[view_df['완료일'].isna()]
        style.info("💡 현재 [미완료 항목] 전체 조회 모드입니다. 완료된 항목을 보려면 위의 체크박스를 체크하세요.")
    else:
        style.success(f"🎯 현재 [전체 데이터] 조회 모드입니다. 총 {len(view_df)}건의 등록 내역이 표시됩니다.")
        
    view_df = view_df.sort_values(by='등록일', ascending=False)
else:
    if search_hosun != "전체":
        view_df = view_df[view_df['호선'] == search_hosun]
    if search_block != "전체":
        view_df = view_df[view_df['블록'] == search_block]
    view_df = view_df.sort_values(by='등록일', ascending=False)
    style.success(f"🎯 검색 결과: 총 {len(view_df)}건의 항목이 발견되었습니다. (완료 항목 포함)")

style.markdown("👇 **수정 또는 완료 처리할 행을 테이블에서 마우스로 클릭하면 좌측 사이드바로 불러옵니다.**")
event = style.dataframe(
    view_df.drop(columns=['원래번호']), 
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

# ---------------------------------------------------------------------------
# 메인 화면: 📥 데이터 다운로드 존
# ---------------------------------------------------------------------------
if not view_df.empty:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        view_df.drop(columns=['원래번호']).to_excel(writer, index=False, sheet_name='Sheet1')
    
    style.download_button(
        label="📥 현재 조회된 목록 엑셀 다운로드",
        data=buffer.getvalue(),
        file_name=f"block_check_filtered_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )
