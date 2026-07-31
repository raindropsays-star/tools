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
    .main-title { font-size: 1.6rem; font-weight: bold; color: #2C3E50; margin-bottom: 0.5rem; }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌳 사례관리 디지털 생태도(Eco-Map)</div>', unsafe_allow_html=True)

# 세션 상태 초기화
if "client_name" not in st.session_state:
    st.session_state.client_name = "당사자"

if "nodes" not in st.session_state:
    st.session_state.nodes = [
        {"name": "장기요양", "role": "요양보호사 파견", "type": "공식체계", "strength": "강함", "direction": "체계 ➔ 대상자"},
        {"name": "방문진료", "role": "월1회 방문진료", "type": "공식체계", "strength": "강함", "direction": "대상자 ➔ 체계"},
        {"name": "보건소", "role": "맞춤형 방문건강", "type": "공식체계", "strength": "보통", "direction": "체계 ➔ 대상자"},
        {"name": "노인맞춤돌봄", "role": "안부확인", "type": "공식체계", "strength": "보통", "direction": "체계 ➔ 대상자"},
        {"name": "오래된 친구", "role": "정서적 지지", "type": "비공식체계", "strength": "강함", "direction": "쌍방향 (↔)"},
        {"name": "경로당", "role": "여가 이용", "type": "비공식체계", "strength": "약함", "direction": "대상자 ➔ 체계"}
    ]

# 사이드바 설정
st.sidebar.header("👤 대상자 및 체계 관리")

# 대상자 이름 변경
st.session_state.client_name = st.sidebar.text_input("중앙 대상자 이름", value=st.session_state.client_name)

st.sidebar.markdown("---")
st.sidebar.subheader("➕ 체계(관계) 추가")

with st.sidebar.form("add_node_form"):
    node_name = st.text_input("체계명 (예: 경로당, 보건소 등)")
    node_role = st.text_input("체계 역할 / 부가 설명 (예: 병원 동행 등)")
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
            "role": node_role if node_role else "",
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
    role_str = f" ({node['role']})" if node.get('role') else ""
    col1.write(f"• **{node['name']}**{role_str}")
    if col2.button("삭제", key=f"del_{i}"):
        st.session_state.nodes.pop(i)
        st.rerun()

# 위치 계산 함수 (타이이트한 원 구도를 위해 배치 반지름 보정)
def calculate_positions(node_list, is_official):
    positions = {}
    count = len(node_list)
    if count == 0:
        return positions

    if is_official:
        start_angle, end_angle = np.pi * 0.62, np.pi * 1.38
    else:
        start_angle, end_angle = -np.pi * 0.38, np.pi * 0.38

    if count <= 4:
        radii = [0.82] * count
        angles = np.linspace(start_angle, end_angle, count + 2)[1:-1] if count > 1 else [(start_angle + end_angle)/2]
    else:
        half = (count + 1) // 2
        radii = [0.72] * half + [0.95] * (count - half)
        angles_inner = np.linspace(start_angle, end_angle, half + 2)[1:-1]
        angles_outer = np.linspace(start_angle, end_angle, (count - half) + 2)[1:-1]
        angles = list(angles_inner) + list(angles_outer)

    for idx, n in enumerate(node_list):
        r = radii[idx]
        a = angles[idx]
        x = r * np.cos(a)
        y = r * np.sin(a)
        positions[n['name']] = (x, y)

    return positions

# 생태도 시각화 함수 (외부 원을 타이트하게 축소)
def draw_pretty_ecomap(nodes, client_name):
    fig, ax = plt.subplots(figsize=(6.5, 6.5), dpi=200)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    G = nx.DiGraph()
    center_id = client_name
    G.add_node(center_id)

    official = [n for n in nodes if n['type'] == "공식체계"]
    unofficial = [n for n in nodes if n['type'] == "비공식체계"]

    pos = {center_id: (0, 0)}
    pos.update(calculate_positions(official, is_official=True))
    pos.update(calculate_positions(unofficial, is_official=False))

    # 1. 외곽 원 (반지름을 1.25 -> 1.08로 타이트하게 축소)
    circle_r = 1.08
    bg_circle = plt.Circle((0, 0), circle_r, color='#B2BEC3', fill=False, linestyle='-', linewidth=1.2)
    ax.add_patch(bg_circle)

    # 2. 중앙 세로 수직 점선
    ax.plot([0, 0], [-circle_r, circle_r], color='#B2BEC3', linestyle='--', linewidth=1.5, zorder=1)

    # 3. 상단 타이틀 (원 테두리에 바짝 밀착)
    bbox_official = dict(boxstyle="round,pad=0.4", fc="#E3F2FD", ec="#1E88E5", lw=1.8)
    bbox_unofficial = dict(boxstyle="round,pad=0.4", fc="#E8F5E9", ec="#43A047", lw=1.8)

    ax.text(-0.48, circle_r, "공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=12.5, weight='bold'),
            ha='center', va='center', color='#0D47A1', zorder=2, bbox=bbox_official)
    ax.text(0.48, circle_r, "비공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=12.5, weight='bold'),
            ha='center', va='center', color='#1B5E20', zorder=2, bbox=bbox_unofficial)

    # 4. 중앙 대상자 노드
    ax.scatter(0, 0, s=2800, color='#FFEAA7', edgecolors='#FDCB6E', linewidth=2.2, zorder=2)
    ax.text(0, 0, center_id, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=12, weight='bold'),
            ha='center', va='center', color='#2D3436', zorder=3)

    # 5. 체계 노드 그리기
    def draw_node_box(n_list, bg_color, border_color):
        for n in n_list:
            x, y = pos[n['name']]
            
            if n.get('role'):
                full_text = f"{n['name']}\n({n['role']})"
            else:
                full_text = f"{n['name']}"

            bbox_props = dict(boxstyle="round,pad=0.5", fc=bg_color, ec=border_color, lw=1.5)
            
            ax.text(x, y, full_text, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=9, weight='bold'),
                    ha='center', va='center', color='#2D3436', zorder=3, bbox=bbox_props, linespacing=1.2)

    draw_node_box(official, "#E3F2FD", "#90CAF9")
    draw_node_box(unofficial, "#E8F5E9", "#A5D6A7")

    # 6. 화살표 연결 (타이트해진 구도에 맞춰 간격 세밀 조절)
    for n in nodes:
        target_x, target_y = pos[n['name']]
        
        if "강" in n['strength']:
            lw = 2.6
            style = 'solid'
            color = '#000000'
        elif "약" in n['strength']:
            lw = 1.1
            style = 'dashed'
            color = '#636E72'
        else:
            lw = 1.6
            style = 'solid'
            color = '#2D3436'

        if "체계 ➔ 대상자" in n['direction']:
            start_pt = (target_x, target_y)
            end_pt = (0, 0)
            arr_style = "->"
            sA, sB = 38, 35
        elif "대상자 ➔ 체계" in n['direction']:
            start_pt = (0, 0)
            end_pt = (target_x, target_y)
            arr_style = "->"
            sA, sB = 35, 38
        elif "쌍방향" in n['direction']:
            start_pt = (target_x, target_y)
            end_pt = (0, 0)
            arr_style = "<->"
            sA, sB = 38, 35
        else:
            start_pt = (target_x, target_y)
            end_pt = (0, 0)
            arr_style = "-"
            sA, sB = 38, 35

        arrow = dict(arrowstyle=arr_style, linestyle=style, linewidth=lw, color=color, shrinkA=sA, shrinkB=sB)
        ax.annotate("", xy=end_pt, xytext=start_pt, arrowprops=arrow, zorder=4)

    # 하단 범례 표시
    legend_text = "↔ 쌍방향·강함     ➔ 일방향·보통     ---> 점선·약함"
    ax.text(0, -1.25, legend_text, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=8.5, weight='bold'),
            ha='center', va='center', color='#2D3436')

    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    plt.axis("off")
    plt.tight_layout()
    return fig

# 메인 구성
col1, col2 = st.columns([2.5, 1])

with col1:
    fig = draw_pretty_ecomap(st.session_state.nodes, st.session_state.client_name)
    st.pyplot(fig)

with col2:
    st.markdown("### 📌 생태도 작성 안내")
    st.info("**공식체계:** 제도 안의 서비스/기관")
    st.success("**비공식체계:** 제도 밖의 개인/자원")
    st.markdown("---")
    st.markdown("""
    **개선 사항:**
    - 외부 가이드 원의 크기를 타이트하게 축소하여 공백을 최소화했습니다.
    """)
