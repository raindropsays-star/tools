import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import urllib.request
import os

# 1. 한글 폰트(나눔고딕) 자동 다운로드 및 적용
@st.cache_resource
def load_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(url, font_path)
    fm.fontManager.addfont(font_path)
    return fm.FontProperties(fname=font_path).get_name()

font_name = load_korean_font()
plt.rc('font', family=font_name)
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="사회복지 사례관리 생태도 생성기", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 2rem; font-weight: bold; color: #2C3E50; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌳 사례관리 디지털 생태도(Eco-Map)</div>', unsafe_allow_html=True)

# 세션 상태 초기화
if "client_name" not in st.session_state:
    st.session_state.client_name = "당사자"

if "nodes" not in st.session_state:
    st.session_state.nodes = [
        {"name": "장기요양", "type": "공식체계", "strength": "보통", "direction": "체계 ➔ 대상자"},
        {"name": "방문진료", "type": "공식체계", "strength": "보통", "direction": "체계 ➔ 대상자"},
        {"name": "노인맞춤돌봄", "type": "공식체계", "strength": "보통", "direction": "체계 ➔ 대상자"},
        {"name": "오래된 친구", "type": "비공식체계", "strength": "강함", "direction": "쌍방향 (↔)"},
        {"name": "이웃", "type": "비공식체계", "strength": "강함", "direction": "체계 ➔ 대상자"},
        {"name": "경로당", "type": "비공식체계", "strength": "약함", "direction": "대상자 ➔ 체계"}
    ]

# 사이드바 설정
st.sidebar.header("👤 대상자 및 체계 관리")

# 대상자 이름 변경
st.session_state.client_name = st.sidebar.text_input("중앙 대상자 이름", value=st.session_state.client_name)

st.sidebar.markdown("---")
st.sidebar.subheader("➕ 체계(관계) 추가")

with st.sidebar.form("add_node_form"):
    node_name = st.text_input("체계명 (예: 경로당, 복지관 등)")
    node_type = st.selectbox("체계 구분", ["공식체계", "비공식체계"])
    strength = st.selectbox("관계 강도 (선의 형태)", ["강함 (굵은 실선)", "보통 (일반 실선)", "약함 (점선)"])
    direction = st.selectbox("관계 방향", [
        "체계 ➔ 대상자", 
        "대상자 ➔ 체계", 
        "쌍방향 (↔)", 
        "단순 연결 (방향없음)"
    ])
    submit = st.form_submit_button("체계 추가하기")

    if submit and node_name:
        str_val = "강함" if "강함" in strength else ("약함" if "약함" in strength else "보통")
        st.session_state.nodes.append({
            "name": node_name,
            "type": node_type,
            "strength": str_val,
            "direction": direction
        })
        st.rerun()

# 체계 삭제
st.sidebar.markdown("---")
st.sidebar.subheader("🗑️ 등록된 체계 목록")
for i, node in enumerate(st.session_state.nodes):
    col1, col2 = st.sidebar.columns([3, 1])
    col1.write(f"• **{node['name']}** ({node['type']})")
    if col2.button("삭제", key=f"del_{i}"):
        st.session_state.nodes.pop(i)
        st.rerun()

# 생태도 시각화 함수
def draw_pretty_ecomap(nodes, client_name):
    fig, ax = plt.subplots(figsize=(9, 8), dpi=200)
    fig.patch.set_facecolor('#F8F9FA')
    ax.set_facecolor('#F8F9FA')

    G = nx.DiGraph()
    center_id = client_name
    G.add_node(center_id)

    official = [n for n in nodes if n['type'] == "공식체계"]
    unofficial = [n for n in nodes if n['type'] == "비공식체계"]

    pos = {center_id: (0, 0)}

    # 좌측 (공식체계)
    if official:
        angles_off = np.linspace(np.pi/1.8, 3*np.pi/1.8, len(official) + 2)[1:-1]
        for idx, n in enumerate(official):
            pos[n['name']] = (1.6 * np.cos(angles_off[idx]), 1.6 * np.sin(angles_off[idx]))

    # 우측 (비공식체계)
    if unofficial:
        angles_unoff = np.linspace(-np.pi/1.8, np.pi/1.8, len(unofficial) + 2)[1:-1]
        for idx, n in enumerate(unofficial):
            pos[n['name']] = (1.6 * np.cos(angles_unoff[idx]), 1.6 * np.sin(angles_unoff[idx]))

    # 외곽 가이드 원
    bg_circle = plt.Circle((0, 0), 1.9, color='#E9ECEF', fill=False, linestyle='--', linewidth=1.5)
    ax.add_patch(bg_circle)

    # 1. 중앙 대상자 노드
    ax.scatter(0, 0, s=4500, color='#FFEAA7', edgecolors='#FDCB6E', linewidth=3, zorder=3)
    ax.text(0, 0, center_id, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=13, weight='bold'),
            ha='center', va='center', color='#2D3436', zorder=4)

    # 2. 공식체계 노드
    for n in official:
        x, y = pos[n['name']]
        bbox_props = dict(boxstyle="round,pad=0.6", fc="#E3F2FD", ec="#90CAF9", lw=2)
        ax.text(x, y, f" {n['name']} ", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=10, weight='bold'),
                ha='center', va='center', bbox=bbox_props, color='#2D3436', zorder=4)

    # 3. 비공식체계 노드
    for n in unofficial:
        x, y = pos[n['name']]
        bbox_props = dict(boxstyle="round,pad=0.6", fc="#E8F5E9", ec="#A5D6A7", lw=2)
        ax.text(x, y, f" {n['name']} ", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=10, weight='bold'),
                ha='center', va='center', bbox=bbox_props, color='#2D3436', zorder=4)

    # 4. 선 형태(강도) 및 화살표(방향) 독립 적용
    for n in nodes:
        target_x, target_y = pos[n['name']]
        
        # 4-1. 선 두께 및 패턴 (관계 강도)
        if "강" in n['strength']:
            lw = 3.5
            style = 'solid'
            color = '#000000'
        elif "약" in n['strength']:
            lw = 1.3
            style = 'dashed'
            color = '#636E72'
        else: # 보통
            lw = 2.0
            style = 'solid'
            color = '#2D3436'

        # 4-2. 화살표 방향 설정 (방향에 상관없이 위에서 정의한 style과 lw 적용)
        if "체계 ➔ 대상자" in n['direction']:
            start_pt = (target_x, target_y)
            end_pt = (0, 0)
            arr_style = "->"
        elif "대상자 ➔ 체계" in n['direction']:
            start_pt = (0, 0)
            end_pt = (target_x, target_y)
            arr_style = "->"
        elif "쌍방향" in n['direction']:
            start_pt = (target_x, target_y)
            end_pt = (0, 0)
            arr_style = "<->"
        else: # 단순 연결
            start_pt = (target_x, target_y)
            end_pt = (0, 0)
            arr_style = "-"

        arrow = dict(arrowstyle=arr_style, linestyle=style, linewidth=lw, color=color, shrinkA=35, shrinkB=35)
        ax.annotate("", xy=end_pt, xytext=start_pt, arrowprops=arrow, zorder=2)

    ax.set_xlim(-2.3, 2.3)
    ax.set_ylim(-2.2, 2.2)
    plt.axis("off")
    plt.tight_layout()
    return fig

# 메인 구성
col1, col2 = st.columns([2.5, 1])

with col1:
    fig = draw_pretty_ecomap(st.session_state.nodes, st.session_state.client_name)
    st.pyplot(fig)

with col2:
    st.markdown("### 📌 구분 범례")
    st.success("**중앙 노란 원:** 대상자")
    st.info("**좌측 블루 카드:** 공식체계 (제도/서비스)")
    st.warning("**우측 그린 카드:** 비공식체계 (자연/이웃)")
    st.markdown("---")
    st.markdown("""
    **관계 표기 지침:**
    - **굵은 실선:** 강한 관계 (강함)
    - **일반 실선:** 보통 관계 (보통)
    - **점선:** 약한/희미한 관계 (약함)
    - **화살표:** 에너지 및 지원 흐름 방향
    """)
