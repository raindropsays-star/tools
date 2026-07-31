import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches
import numpy as np
import urllib.request
import os
import io

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

st.set_page_config(page_title="사례관리 스마트 생태도/가계도 생성기", layout="wide")

# 상단 여백 최소화 패딩 적용
st.markdown("""
<style>
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화 (생태도)
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

# 세션 상태 초기화 (가계도)
if "gen_client" not in st.session_state:
    st.session_state.gen_client = {"name": "홍길동", "gender": "남성", "age": "72", "is_alive": True}

if "family_members" not in st.session_state:
    st.session_state.family_members = [
        {"relation": "부(아버지)", "name": "아버지", "gender": "남성", "age": "사망", "is_alive": False, "rel_type": "보통"},
        {"relation": "모(어머니)", "name": "어머니", "gender": "여성", "age": "사망", "is_alive": False, "rel_type": "보통"},
        {"relation": "배우자", "name": "배우자", "gender": "여성", "age": "68", "is_alive": True, "rel_type": "밀접/친밀"},
        {"relation": "자녀", "name": "장남", "gender": "남성", "age": "45", "is_alive": True, "rel_type": "보통"},
        {"relation": "자녀", "name": "장녀", "gender": "여성", "age": "42", "is_alive": True, "rel_type": "소원/불화"}
    ]

# -------------------------------------------------------------
# 사이드바 최상단: 도구 선택 메뉴
# -------------------------------------------------------------
st.sidebar.header("📌 작성 도구 선택")
selected_tool = st.sidebar.radio("원하시는 도구를 선택하세요", ["🌳 사례관리 생태도", "👨‍👩‍👧‍👦 스마트 가계도"])
st.sidebar.markdown("---")

# =============================================================
# [MODE 1] 생태도 모드
# =============================================================
if selected_tool == "🌳 사례관리 생태도":
    st.sidebar.header("🌳 [생태도] 정보 입력")
    st.session_state.client_name = st.sidebar.text_input("중앙 대상자 이름", value=st.session_state.client_name, key="eco_client")
    
    with st.sidebar.form("add_node_form"):
        st.subheader("➕ 체계 추가")
        node_name = st.text_input("체계명 (예: 경로당 등)")
        node_role = st.text_input("체계 역할 / 부가 설명")
        node_type = st.selectbox("체계 구분", ["공식체계", "비공식체계"])
        strength = st.selectbox("관계 강도", ["강함 (굵은 실선)", "보통 (일반 실선)", "약함 (점선)"])
        direction = st.selectbox("관계 방향", ["체계 ➔ 대상자", "대상자 ➔ 체계", "쌍방향 (↔)", "단순 연결"])
        if st.form_submit_button("체계 추가하기") and node_name:
            str_val = "강함" if "강함" in strength else ("약함" if "약함" in strength else "보통")
            st.session_state.nodes.append({"name": node_name, "role": node_role, "type": node_type, "strength": str_val, "direction": direction})
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ 등록된 체계 목록")
    for i, node in enumerate(st.session_state.nodes):
        c1, c2 = st.sidebar.columns([3, 1])
        c1.write(f"• **{node['name']}** ({node.get('role', '')})")
        if c2.button("삭제", key=f"del_eco_{i}"):
            st.session_state.nodes.pop(i)
            st.rerun()

    def calculate_positions_ecomap(node_list, is_official):
        positions = {}
        count = len(node_list)
        if count == 0: return positions

        if is_official: start_angle, end_angle = np.pi * 0.65, np.pi * 1.35
        else: start_angle, end_angle = -np.pi * 0.35, np.pi * 0.35

        if count <= 4:
            radii = [0.75] * count
            angles = np.linspace(start_angle, end_angle, count + 2)[1:-1] if count > 1 else [(start_angle + end_angle)/2]
        else:
            half = (count + 1) // 2
            radii = [0.68] * half + [0.85] * (count - half)
            angles_inner = np.linspace(start_angle, end_angle, half + 2)[1:-1]
            angles_outer = np.linspace(start_angle, end_angle, (count - half) + 2)[1:-1]
            angles = list(angles_inner) + list(angles_outer)

        for idx, n in enumerate(node_list):
            positions[n['name']] = (radii[idx] * np.cos(angles[idx]), radii[idx] * np.sin(angles[idx]))
        return positions

    def draw_pretty_ecomap(nodes, client_name):
        fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=200)
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')

        center_id = client_name
        official = [n for n in nodes if n['type'] == "공식체계"]
        unofficial = [n for n in nodes if n['type'] == "비공식체계"]

        pos = {center_id: (0, 0)}
        pos.update(calculate_positions_ecomap(official, is_official=True))
        pos.update(calculate_positions_ecomap(unofficial, is_official=False))

        circle_r = 1.05
        ax.add_patch(plt.Circle((0, 0), circle_r, color='#B2BEC3', fill=False, linestyle='-', linewidth=1.2))
        ax.plot([0, 0], [-circle_r, circle_r], color='#B2BEC3', linestyle='--', linewidth=1.5, zorder=1)

        bbox_official = dict(boxstyle="round,pad=0.35", fc="#E3F2FD", ec="#1E88E5", lw=1.6)
        bbox_unofficial = dict(boxstyle="round,pad=0.35", fc="#E8F5E9", ec="#43A047", lw=1.6)

        ax.text(-0.52, circle_r, "공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=10.5, weight='bold'), ha='center', va='center', color='#0D47A1', zorder=2, bbox=bbox_official)
        ax.text(0.52, circle_r, "비공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=10.5, weight='bold'), ha='center', va='center', color='#1B5E20', zorder=2, bbox=bbox_unofficial)

        # 중앙 원
        ax.scatter(0, 0, s=1800, color='#FFEAA7', edgecolors='#FDCB6E', linewidth=2.0, zorder=2)
        ax.text(0, 0, center_id, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=9.5, weight='bold'), ha='center', va='center', color='#2D3436', zorder=3)

        # 체계 노드 상자 (체계명: 7.5pt, 역할: 5.2pt / 행간 간격 확장을 위한 좌표 재조정)
        def draw_node_box(n_list, bg_color, border_color):
            for n in n_list:
                x, y = pos[n['name']]
                
                bbox_props = dict(boxstyle="round,pad=0.35", fc=bg_color, ec=border_color, lw=1.2)
                
                # 텍스트 박스 높이 확보를 위한 템플릿
                disp_text = f"{n['name']}\n({n['role']})" if n.get('role') else f"{n['name']}"
                ax.text(x, y, disp_text, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=7.5, weight='bold'),
                        ha='center', va='center', color='none', zorder=3, bbox=bbox_props, linespacing=1.6)

                # 실제 글자 배치 (행간을 시원하게 띄움)
                if n.get('role'):
                    ax.text(x, y + 0.032, n['name'], fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=7.5, weight='bold'),
                            ha='center', va='center', color='#2D3436', zorder=4)
                    ax.text(x, y - 0.038, f"({n['role']})", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=5.2),
                            ha='center', va='center', color='#636E72', zorder=4)
                else:
                    ax.text(x, y, n['name'], fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=7.5, weight='bold'),
                            ha='center', va='center', color='#2D3436', zorder=4)

        draw_node_box(official, "#E3F2FD", "#90CAF9")
        draw_node_box(unofficial, "#E8F5E9", "#A5D6A7")

        # 화살표 연결 (정밀 좌표 오프셋으로 글자 가림 현상 정밀 해결)
        for n in nodes:
            target_x, target_y = pos[n['name']]
            lw = 2.2 if "강" in n['strength'] else (1.0 if "약" in n['strength'] else 1.4)
            style = 'dashed' if "약" in n['strength'] else 'solid'
            color = '#000000' if "강" in n['strength'] else ('#636E72' if "약" in n['strength'] else '#2D3436')

            if "체계 ➔ 대상자" in n['direction']: 
                start_pt, end_pt, arr_style = (target_x, target_y), (0, 0), "->"
                sA, sB = 26, 20
            elif "대상자 ➔ 체계" in n['direction']: 
                start_pt, end_pt, arr_style = (0, 0), (target_x, target_y), "->"
                sA, sB = 20, 28  # 체계 박스 테두리 겉면에 정확히 맞춤
            elif "쌍방향" in n['direction']: 
                start_pt, end_pt, arr_style = (target_x, target_y), (0, 0), "<->"
                sA, sB = 26, 20
            else: 
                start_pt, end_pt, arr_style = (target_x, target_y), (0, 0), "-"
                sA, sB = 26, 20

            arrow = dict(arrowstyle=arr_style, linestyle=style, linewidth=lw, color=color, shrinkA=sA, shrinkB=sB)
            ax.annotate("", xy=end_pt, xytext=start_pt, arrowprops=arrow, zorder=5)

        ax.text(0, -1.3, "↔ 쌍방향·강함     ➔ 일방향·보통     ---> 점선·약함", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=8, weight='bold'), ha='center', va='center', color='#2D3436')
        
        ax.set_xlim(-1.45, 1.45)
        ax.set_ylim(-1.45, 1.45)
        plt.axis("off")
        plt.tight_layout()
        return fig

    # 차트 출력
    fig1 = draw_pretty_ecomap(st.session_state.nodes, st.session_state.client_name)
    st.pyplot(fig1, use_container_width=False)

    buf1 = io.BytesIO()
    fig1.savefig(buf1, format="png", bbox_inches='tight', dpi=300)
    st.download_button(label="💾 생태도 고화질 이미지 다운로드 (PNG)", data=buf1.getvalue(), file_name=f"생태도_{st.session_state.client_name}.png", mime="image/png")

# =============================================================
# [MODE 2] 가계도 모드
# =============================================================
else:
    st.sidebar.header("👨‍👩‍👧‍👦 [가계도] 정보 입력")
    gc_name = st.sidebar.text_input("당사자 이름", value=st.session_state.gen_client['name'], key="gen_name")
    gc_gender = st.sidebar.radio("당사자 성별", ["남성", "여성"], index=0 if st.session_state.gen_client['gender'] == "남성" else 1, horizontal=True, key="gen_gender")
    gc_age = st.sidebar.text_input("당사자 나이", value=st.session_state.gen_client['age'], key="gen_age")
    st.session_state.gen_client = {"name": gc_name, "gender": gc_gender, "age": gc_age, "is_alive": True}

    st.sidebar.markdown("---")
    with st.sidebar.form("add_family_form"):
        st.subheader("➕ 가족 추가")
        f_rel = st.selectbox("관계", ["배우자", "자녀", "부(아버지)", "모(어머니)"])
        f_name = st.text_input("이름/호칭 (예: 장남 등)")
        f_gender = st.radio("성별", ["남성", "여성"], horizontal=True, key="fam_gender")
        f_age = st.text_input("나이 (사망 시 '사망' 입력)")
        f_rel_type = st.selectbox("당사자와의 관계", ["보통", "밀접/친밀", "소원/불화"])
        
        if st.form_submit_button("가족 추가하기") and f_name:
            is_alive = False if f_age == "사망" else True
            st.session_state.family_members.append({
                "relation": f_rel, "name": f_name, "gender": f_gender, "age": f_age, "is_alive": is_alive, "rel_type": f_rel_type
            })
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ 등록된 가족 목록")
    for idx, m in enumerate(st.session_state.family_members):
        fc1, fc2 = st.sidebar.columns([3, 1])
        fc1.write(f"• **[{m['relation']}] {m['name']}** ({m['gender']}/{m['age']})")
        if fc2.button("삭제", key=f"del_fam_{idx}"):
            st.session_state.family_members.pop(idx)
            st.rerun()

    def draw_pretty_genogram(client, members):
        fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=200)
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')

        parents = [m for m in members if "부" in m['relation'] or "모" in m['relation']]
        spouse = [m for m in members if "배우자" in m['relation']]
        children = [m for m in members if "자녀" in m['relation']]

        def draw_person(x, y, name, age, gender, is_alive, is_target=False):
            box_s = 0.22
            color = '#FFEAA7' if is_target else ('#E3F2FD' if gender == '남성' else '#FCE4EC')
            edge_c = '#FDCB6E' if is_target else ('#1976D2' if gender == '남성' else '#C2185B')
            lw = 2.2 if is_target else 1.6

            if gender == '남성':
                rect = patches.Rectangle((x - box_s/2, y - box_s/2), box_s, box_s, facecolor=color, edgecolor=edge_c, linewidth=lw, zorder=4)
                ax.add_patch(rect)
            else:
                circle = patches.Circle((x, y), box_s/2, facecolor=color, edgecolor=edge_c, linewidth=lw, zorder=4)
                ax.add_patch(circle)

            if not is_alive:
                ax.plot([x - box_s/2.5, x + box_s/2.5], [y - box_s/2.5, y + box_s/2.5], color='#D63031', lw=1.8, zorder=5)
                ax.plot([x - box_s/2.5, x + box_s/2.5], [y + box_s/2.5, y - box_s/2.5], color='#D63031', lw=1.8, zorder=5)

            disp_txt = f"{name}\n({age}세)" if is_alive else f"{name}\n(사망)"
            ax.text(x, y - box_s/2 - 0.08, disp_txt, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=7.5, weight='bold'),
                    ha='center', va='top', color='#2D3436', zorder=5)

        cx, cy = (0, 0.1) if not spouse else (-0.45, 0.1)
        draw_person(cx, cy, client['name'], client['age'], client['gender'], client['is_alive'], is_target=True)

        if spouse:
            sx, sy = (0.45, 0.1)
            sp = spouse[0]
            draw_person(sx, sy, sp['name'], sp['age'], sp['gender'], sp['is_alive'])
            line_style = '-' if sp['rel_type'] != '소원/불화' else '--'
            color = '#D63031' if sp['rel_type'] == '소원/불화' else '#2D3436'
            ax.plot([cx + 0.11, sx - 0.11], [cy, sy], color=color, linestyle=line_style, lw=2, zorder=2)
            if sp['rel_type'] == '밀접/친밀':
                ax.plot([cx + 0.11, sx - 0.11], [cy + 0.03, sy + 0.03], color='#1976D2', lw=2, zorder=2)

        if parents:
            py = 0.9
            father = [p for p in parents if "부" in p['relation']]
            mother = [p for p in parents if "모" in p['relation']]
            
            p_fx, p_mx = -0.45, 0.45

            if father: draw_person(p_fx, py, father[0]['name'], father[0]['age'], father[0]['gender'], father[0]['is_alive'])
            if mother: draw_person(p_mx, py, mother[0]['name'], mother[0]['age'], mother[0]['gender'], mother[0]['is_alive'])

            if father and mother:
                ax.plot([p_fx + 0.11, p_mx - 0.11], [py, py], color='#B2BEC3', linestyle='--', lw=1.5, zorder=1)
                ax.plot([0, 0], [py, py - 0.3], color='#B2BEC3', linestyle=':', lw=1.5, zorder=1)
                ax.plot([0, cx], [py - 0.3, cy + 0.11], color='#B2BEC3', linestyle=':', lw=1.5, zorder=1)
            elif father: ax.plot([p_fx, cx], [py - 0.11, cy + 0.11], color='#B2BEC3', linestyle=':', lw=1.5, zorder=1)
            elif mother: ax.plot([p_mx, cx], [py - 0.11, cy + 0.11], color='#B2BEC3', linestyle=':', lw=1.5, zorder=1)

        if children:
            chy = -0.85
            branch_y = -0.42
            ch_xs = np.linspace(-0.55, 0.55, len(children))
            mid_x = (cx + sx)/2 if spouse else cx
            ax.plot([mid_x, mid_x], [cy, branch_y], color='#2D3436', lw=1.5, zorder=1)
            
            if len(children) > 1:
                ax.plot([ch_xs[0], ch_xs[-1]], [branch_y, branch_y], color='#2D3436', lw=1.5, zorder=1)

            for idx, ch in enumerate(children):
                chx = ch_xs[idx]
                draw_person(chx, chy, ch['name'], ch['age'], ch['gender'], ch['is_alive'])
                ax.plot([chx, chx], [branch_y, chy + 0.11], color='#2D3436', lw=1.5, zorder=1)

        ax.text(0, -1.3, "□ 남성   ○ 여성   [색상/굵은선] 당사자   [X] 사망   ═ 밀접   --- 불화", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=8, weight='bold'), ha='center', va='center', color='#636E72')
        
        ax.set_xlim(-1.45, 1.45)
        ax.set_ylim(-1.45, 1.45)
        plt.axis("off")
        plt.tight_layout()
        return fig

    # 차트 출력
    fig2 = draw_pretty_genogram(st.session_state.gen_client, st.session_state.family_members)
    st.pyplot(fig2, use_container_width=False)

    buf2 = io.BytesIO()
    fig2.savefig(buf2, format="png", bbox_inches='tight', dpi=300)
    st.download_button(label="💾 가계도 고화질 이미지 다운로드 (PNG)", data=buf2.getvalue(), file_name=f"가계도_{st.session_state.gen_client['name']}.png", mime="image/png")
