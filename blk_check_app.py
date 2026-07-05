import streamlit as style
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection  # 구글 시트 라이브러리 추가

# 💡 구글 시트 연결 설정 (구글 시트 URL을 지정)
# 실제 배포 시에는 아래 URL 칸에 본인의 구글 시트 주소를 넣거나 secrets 기능을 사용합니다.
GSHEET_URL = "https://docs.google.com/spreadsheets/d/이곳에_본인의_구글시트_ID_입력/edit?usp=sharing"
conn = style.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 함수 (구글 시트에서 읽기)
def load_data():
    try:
        # 구글 시트 데이터를 판다스 데이터프레임으로 로드
        df = conn.read(spreadsheet=GSHEET_URL, ttl="0d") # ttl="0d"는 캐시 없이 실시간 조회를 의미
        df['호선'] = df['호선'].astype(str).str.strip()
        df['블록'] = df['블록'].astype(str).str.strip()
        df['등록일'] = pd.to_datetime(df['등록일']).dt.date
        df['완료일'] = pd.to_datetime(df['완료일']).dt.date
        return df
    except Exception as e:
        return pd.DataFrame(columns=['호선', '블록', '공정', '세부내용', '등록일', '완료일', '담당자'])

# 데이터 저장 함수 (구글 시트에 쓰기)
def save_data(df):
    # 날짜 형식을 문자열로 변환하여 저장 안정성 확보
    df_to_save = df.copy()
    df_to_save['등록일'] = df_to_save['등록일'].astype(str)
    df_to_save['완료일'] = df_to_save['완료일'].apply(lambda x: str(x) if pd.notna(x) else "")
    conn.update(spreadsheet=GSHEET_URL, data=df_to_save)

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

# 레이아웃 조정: 선택박스 2개 배치 후 하단에 완료 항목 체크박스 배치
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

# 💡 [핵심 추가] 전체 조회 상태일 때 완료 항목도 볼지 선택하는 체크박스
show_completed = style.checkbox("✅ 완료된 특이사항 항목도 조회 목록에 포함하기", value=False)

if search_hosun != style.session_state.selected_hosun or search_block != style.session_state.selected_block:
    style.session_state.selected_hosun = search_hosun
    style.session_state.selected_block = search_block
    style.rerun()

# 테이블 조회를 위해 데이터 복사 및 원본 인덱스 보존
view_df = df.copy()
view_df['원래번호'] = view_df.index

if search_hosun == "전체" and search_block == "전체":
    # 💡 체크박스 체크 여부에 따라 조건 분기
    if not show_completed:
        view_df = view_df[view_df['완료일'].isna()]
        style.info("💡 현재 [미완료 항목] 전체 조회 모드입니다. 완료된 항목을 보려면 위의 체크박스를 체크하세요.")
    else:
        style.success(f"🎯 현재 [전체 데이터] 조회 모드입니다. 총 {len(view_df)}건의 등록 내역이 표시됩니다.")
        
    view_df = view_df.sort_values(by='등록일', ascending=False)
else:
    # 특정 호선/블록 검색 시에는 조건대로 정렬 (완료 항목 기본 포함)
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
