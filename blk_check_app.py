import streamlit as style
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests

# ===========================================================================
# 1. 환경 설정 및 구글 시트 주소 (★본인 주소로 변경 필수★)
# ===========================================================================
# ⚠️ 주의: 구글 시트의 [공유] 설정이 "링크가 있는 모든 사용자(편집자)"로 되어 있어야 
# 모바일에서 데이터 입력이 가능합니다.
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/12i27S6rTm_scIeUQ1k7MbSCHpr_qrhkhrB8yhxU0JQg/edit?usp=sharing"

# 페이지 와이드 모드 설정
style.set_page_config(layout="wide")
style.title("⚙️ 블록검사 공정별 특이사항 관리 시스템")

# ===========================================================================
# 2. 데이터 로드 및 저장 함수 (보안망 우회 및 네트워크 에러 처리 내장)
# ===========================================================================
def load_data_from_sheets():
    fallback_df = pd.DataFrame(columns=['호선', '블록', '공정', '세부내용', '등록일', '완료일', '담당자'])
    try:
        if "/edit" in GOOGLE_SHEET_URL:
            csv_url = GOOGLE_SHEET_URL.split("/edit")[0] + "/export?format=csv"
        else:
            csv_url = GOOGLE_SHEET_URL
            
        # 판다스로 구글 시트 CSV 직접 로드 (사내 보안망 우회)
        df = pd.read_csv(csv_url)
        
        if df.empty:
            return fallback_df
            
        # 데이터 정제 및 날짜 예외 처리
        df['호선'] = df['호선'].astype(str).str.strip()
        df['블록'] = df['블록'].astype(str).str.strip()
        df['등록일'] = pd.to_datetime(df['등록일'], errors='coerce').dt.date
        df['완료일'] = pd.to_datetime(df['완료일'], errors='coerce').dt.date
        return df
    except pd.errors.EmptyDataError:
        style.warning("⚠️ 구글 시트에 헤더만 존재하거나 데이터가 완전히 비어있습니다.")
        return fallback_df
    except (requests.exceptions.ConnectionError, urllib.error.URLError) if 'urllib' in globals() else requests.exceptions.ConnectionError:
        style.error("🌐 사내 방화벽 장비 또는 인터넷 연결 문제로 구글 서버에 접속할 수 없습니다.")
        return fallback_df
    except Exception as e:
        style.error(f"❌ 데이터 로드 중 예상치 못한 오류 발생: {e}")
        return fallback_df

def save_data_to_sheets(df):
    """
    배포 환경(Streamlit Cloud)에서는 구글 시트에 직접 데이터를 업데이트하며,
    패키지 설치가 막힌 사내 로컬 환경일 경우 우회 안내 메시지를 출력합니다.
    """
    try:
        # Streamlit Cloud 배포 환경인지 확인하는 로직
        from streamlit_gsheets import GSheetsConnection
        conn = style.connection("gsheets", type=GSheetsConnection)
        conn.update(data=df)
        return True
    except Exception:
        # 로컬 보안망 환경이라 라이브러리가 없을 때의 예외 처리 (수동 안내)
        style.sidebar.error("⚠️ [로컬 보안망 제한] 현재 PC 환경에서는 데이터 직접 저장이 제한됩니다.")
        style.sidebar.info("💡 모바일 배포 주소(스마트폰 화면)에서는 정상적으로 저장·수정이 가능합니다.")
        return False

# 최초 실시간 데이터 로드
df = load_data_from_sheets()

# ===========================================================================
# 3. 사이드바: 🆕 특이사항 신규 등록 및 완료 처리 섹션 (구글 시트 연동 반영)
# ===========================================================================
style.sidebar.header("🆕 특이사항 등록 / 완료 처리")

if 'edit_index' not in style.session_state:
    style.session_state.edit_index = None

if style.session_state.edit_index is not None:
    style.sidebar.warning(f"⚠️ 현재 {style.session_state.edit_index + 1}번 행 수정 모드입니다.")
    idx = style.session_state.edit_index
    default_hosun = str(df.loc[idx, '호선']) if idx < len(df) else ""
    default_block = str(df.loc[idx, '블록']) if idx < len(df) else ""
    default_process = str(df.loc[idx, '공정']) if idx < len(df) and pd.notna(df.loc[idx, '공정']) else ""
    default_content = str(df.loc[idx, '세부내용']) if idx < len(df) and pd.notna(df.loc[idx, '세부내용']) else ""
    default_reg_date = df.loc[idx, '등록일'] if idx < len(df) and pd.notna(df.loc[idx, '등록일']) else datetime.now().date()
    default_is_comp = pd.notna(df.loc[idx, '완료일']) if idx < len(df) else False
    default_comp_date = df.loc[idx, '완료일'] if default_is_comp else datetime.now().date()
    default_worker = str(df.loc[idx, '담당자']) if idx < len(df) and pd.notna(df.loc[idx, '담당자']) else ""
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
            # 기존 데이터 수정
            df.loc[style.session_state.edit_index, '호선'] = input_hosun.strip()
            df.loc[style.session_state.edit_index, '블록'] = input_block.strip()
            df.loc[style.session_state.edit_index, '공정'] = input_process.strip()
            df.loc[style.session_state.edit_index, '세부내용'] = input_content
            df.loc[style.session_state.edit_index, '등록일'] = input_reg_date
            df.loc[style.session_state.edit_index, '완료일'] = input_comp_date if is_completed else None
            df.loc[style.session_state.edit_index, '담당자'] = input_worker
            
            if save_data_to_sheets(df):
                style.sidebar.success("💾 데이터가 성공적으로 수정되었습니다!")
                style.session_state.edit_index = None
                style.rerun()
        else:
            # 신규 데이터 추가
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
            
            if save_data_to_sheets(df):
                style.sidebar.success("🎉 신규 특이사항 등록 완료!")
                style.rerun()
    else:
        style.sidebar.error("⚠️ 호선, 블록, 세부내용은 필수 입력 사항입니다.")

# ===========================================================================
# 4. 메인 화면: 📊 통계 그래프 존
# ===========================================================================
style.subheader("📊 실시간 공정 현황 통계")
if not df.empty:
    col1, col2 = style.columns(2)
    uncompleted_df = df[df['완료일'].isna()]
    
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
        elif uncompleted_df.empty:
            style.info("현재 미완료된 특이사항이 없습니다.")
        else:
            style.info("'호선' 컬럼을 찾을 수 없습니다.")
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
