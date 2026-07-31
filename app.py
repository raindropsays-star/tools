import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

# 한글 폰트 설정 (Windows 기본 폰트)
plt.rc('font', family='Malgun Gothic')
plt.rc('axes', unicode_minus=False)

st.set_page_config(page_title="사회복지 사례관리 생태도 생성기", layout="wide")
st.title("🌳 사회복지 사례관리 생태도(Eco-Map) 자동 생성기")

# 세션 상태 초기화
if "nodes" not in st.session_state:
    st.session_state.nodes = [
        {"name": "장기요양", "type": "공식체계", "strength": "중", "direction": "일방향(<-)"},
        {"name": "방문진료", "type": "공식체계", "strength": "중", "direction": "일방향(<-)"},
        {"name": "노인맞춤돌봄", "type": "공식체계", "strength": "중", "direction": "일방향(<-)"},
        {"name": "오래된 친구", "type": "비공식체계", "strength": "강", "direction": "쌍방향(<->)"},
        {"name": "이웃", "type": "비공식체계", "strength": "강", "direction": "일방향(<-)"},
        {"name": "경로당", "type": "비공식체계", "strength": "약", "direction": "점선(약함)"}
    ]

# 사이드바: 입력 폼
st.sidebar.header("📋 체계(관계) 추가 및 관리")

with st.sidebar.form("add_node_form"):
    node_name = st.text_input("체계명 (예: 경로당, 장기요양 등)")
    node_type = st.selectbox("체계 구분", ["공식체계", "비공식체계"])
    strength = st.selectbox("관계 강도", ["강", "중", "약"])
    direction = st.selectbox("관계 방향", ["쌍방향(<->)", "일방향(<-)", "점선(약함)"])
    submit = st.form_submit_button("체계 추가하기")

    if submit and node_name:
        st.session_state.nodes.append({
            "name": node_name,
            "type": node_type,
            "strength": strength,
            "direction": direction
        })
        st.sidebar.success(f"'{node_name}' 추가 완료!")

# 체계 목록 삭제 기능
st.sidebar.subheader("🗑️ 등록된 체계 목록")
for i, node in enumerate(st.session_state.nodes):
    col1, col2 = st.sidebar.columns([3, 1])
    col1.write(f"**{node['name']}** ({node['type']})")
    if col2.button("삭제", key=f"del_{i}"):
        st.session_state.nodes.pop(i)
        st.rerun()

# 생태도 그리기 함수
def draw_ecomap(nodes):
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 그래프 객체 생성
    G = nx.DiGraph()
    G.add_node("당사자")
    
    official_nodes = [n for n in nodes if n['type'] == "공식체계"]
    unofficial_nodes = [n for n in nodes if n['type'] == "비공식체계"]
    
    pos = {"당사자": (0, 0)}
    
    # 공식체계 (좌측 배치)
    if official_nodes:
        angles_off = np.linspace(np.pi/2, 3*np.pi/2, len(official_nodes) + 2)[1:-1]
        for idx, n in enumerate(official_nodes):
            pos[n['name']] = (1.5 * np.cos(angles_off[idx]), 1.5 * np.sin(angles_off[idx]))
            
    # 비공식체계 (우측 배치)
    if unofficial_nodes:
        angles_unoff = np.linspace(-np.pi/2, np.pi/2, len(unofficial_nodes) + 2)[1:-1]
        for idx, n in enumerate(unofficial_nodes):
            pos[n['name']] = (1.5 * np.cos(angles_unoff[idx]), 1.5 * np.sin(angles_unoff[idx]))

    # 원형 배경선
    circle = plt.Circle((0, 0), 1.8, color='lightgray', fill=False, linestyle='--', linewidth=1.5)
    ax.add_patch(circle)
    
    # 노드 그리기
    nx.draw_networkx_nodes(G, pos, nodelist=["당사자"], node_color="gold", node_size=3000, ax=ax)
    
    if official_nodes:
        nx.draw_networkx_nodes(G, pos, nodelist=[n['name'] for n in official_nodes], 
                              node_color="lightblue", node_shape="s", node_size=2500, ax=ax)
    if unofficial_nodes:
        nx.draw_networkx_nodes(G, pos, nodelist=[n['name'] for n in unofficial_nodes], 
                              node_color="lightgreen", node_shape="s", node_size=2500, ax=ax)
        
    nx.draw_networkx_labels(G, pos, font_family='Malgun Gothic', font_size=10, font_weight="bold", ax=ax)
    
    # 관계선(화살표) 그리기
    for n in nodes:
        style = 'solid'
        weight = 1.5
        if n['strength'] == '강': weight = 3.0
        elif n['strength'] == '약': style = 'dashed'; weight = 1.0
        
        if n['direction'] == '쌍방향(<->)':
            ax.annotate("", xy=pos["당사자"], xytext=pos[n['name']],
                        arrowprops=dict(arrowstyle="<->", linestyle=style, linewidth=weight, color="black", shrinkA=25, shrinkB=25))
        elif n['direction'] == '일방향(<-)':
            ax.annotate("", xy=pos["당사자"], xytext=pos[n['name']],
                        arrowprops=dict(arrowstyle="->", linestyle=style, linewidth=weight, color="black", shrinkA=25, shrinkB=25))
        else: # 점선/약함
            ax.annotate("", xy=pos["당사자"], xytext=pos[n['name']],
                        arrowprops=dict(arrowstyle="-", linestyle="dashed", linewidth=1.0, color="gray", shrinkA=25, shrinkB=25))

    plt.title("생태도 (Eco-Map)", fontsize=16, fontweight='bold')
    plt.axis("off")
    return fig

# 메인 화면
col1, col2 = st.columns([2, 1])
with col1:
    fig = draw_ecomap(st.session_state.nodes)
    st.pyplot(fig)

with col2:
    st.subheader("💡 범례 (개입 지침)")
    st.info("""
    - **중앙 노란 원:** 당사자
    - **좌측 파란 사각형:** 공식체계 (제도/기관)
    - **우측 초록 사각형:** 비공식체계 (자연/이웃)
    - **선 굵기:** 강함(굵은선), 보통(보통선), 약함(점선)
    - **화살표:** 관계의 방향
    """)
