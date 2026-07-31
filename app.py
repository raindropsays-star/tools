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

st.markdown("""
<style>
    .main-title { font-size: 1.8rem; font-weight: bold; color: #2C3E50; margin-bottom: 0.5rem; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 사례관리 디지털 도구 (생태도 & 가계도)</div>', unsafe_allow_html=True)

# 공통 사이드바 (차트 크기 조절 옵션)
st.sidebar.header("⚙️ 화면 및 차트 크기 설정")
chart_size = st.sidebar.slider("🖼️ 차트 크기 조절 (스크린샷용)", min_value=3.5, max_value=7.5, value=5.0, step=0.5)

# 메인 탭 구성
tab1, tab2 = st.tabs(["🌳 사례관리 생태도(Eco-Map)", "👨‍👩‍👧‍👦 스마트 가계도(Genogram)"])

# ==========================================
# [TAB 1] 생태도 생성기
# ==========================================
with tab1:
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

    def calculate_positions_ecomap(node_list, is_official):
        positions = {}
        count = len(node_list)
        if count == 0: return positions

        if is_official: start_angle, end_angle = np.pi * 0.65, np.pi * 1.35
        else: start_angle, end_angle = -np.pi * 0.35, np.pi * 0.35

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
            positions[n['name']] = (radii[idx] * np.cos(angles[idx]), radii[idx] * np.sin(angles[idx]))
        return positions

    def draw_pretty_ecomap(nodes, client_name, size):
        fig, ax = plt.subplots(figsize=(size, size), dpi=200)
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')

        center_id = client_name
        official = [n for n in nodes if n['type'] == "공식체계"]
        unofficial = [n for n in nodes if n['type'] == "비공식체계"]

        pos = {center_id: (0, 0)}
        pos.update(calculate_positions_ecomap(official, is_official=True))
        pos.update(calculate_positions_ecomap(unofficial, is_official=False))

        circle_r = 1.08
        ax.add_patch(plt.Circle((0, 0), circle_r, color='#B2BEC3', fill=False, linestyle='-', linewidth=1.2))
        ax.plot([0, 0], [-circle_r, circle_r], color='#B2BEC3', linestyle='--', linewidth=1.5, zorder=1)

        bbox_official = dict(boxstyle="round,pad=0.4", fc="#E3F2FD", ec="#1E88E5", lw=1.8)
        bbox_unofficial = dict(boxstyle="round,pad=0.4", fc="#E8F5E9", ec="#43A047", lw=1.8)

        ax.text(-0.52, circle_r, "공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=12.5, weight='bold'), ha='center', va='center', color='#0D47A1', zorder=2, bbox=bbox_official)
        ax.text(0.52, circle_r, "비공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=12.5, weight='bold'), ha='center', va='center', color='#1B5E20', zorder=2, bbox=bbox_unofficial)

        ax.scatter(0, 0, s=2800, color='#FFEAA7', edgecolors='#FDCB6E', linewidth=2.2, zorder=2)
        ax.text(0, 0, center_id, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=12, weight='bold'), ha='center', va='center', color='#2D3436', zorder=3)

        def draw_node_box(n_list, bg_color, border_color):
            for n in n_list:
                x, y = pos[n['name']]
                full_text = f"{n['name']}\n({n['role']})" if n.get('role') else f"{n['name']}"
                bbox_props = dict(boxstyle="round,pad=0.5", fc=bg_color, ec=border_color, lw=1.5)
                ax.text(x, y, full_text, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=9, weight='bold'), ha='center', va='center', color='#2D3436', zorder=3, bbox=bbox_props, linespacing=1.2)

        draw_node_box(official, "#E3F2FD", "#90CAF9")
        draw_node_box(unofficial, "#E8F5E9", "#A5D6A7")

        for n in nodes:
            target_x, target_y = pos[n['name']]
            lw = 2.6 if "강" in n['strength'] else (1.1 if "약" in n['strength'] else 1.6)
            style = 'dashed' if "약" in n['strength'] else 'solid'
            color = '#000000' if "강" in n['strength'] else ('#636E72' if "약" in n['strength'] else '#2D3436')

            if "체계 ➔ 대상자" in n['direction']: start_pt, end_pt, arr_style, sA, sB = (target_x, target_y), (0, 0), "->", 38, 35
            elif "대상자 ➔ 체계" in n['direction']: start_pt, end_pt, arr_style, sA, sB = (0, 0), (target_x, target_y), "->", 35, 38
            elif "쌍방향" in n['direction']: start_pt, end_pt, arr_style, sA, sB = (target_x, target_y), (0, 0), "<->", 38, 35
            else: start_pt, end_pt, arr_style, sA, sB = (target_x, target_y), (0, 0), "-", 38, 35

            arrow = dict(arrowstyle=arr_style, linestyle=style, linewidth=lw, color=color, shrinkA=sA, shrinkB=sB)
            ax.annotate("", xy=end_pt, xytext=start_pt, arrowprops=arrow, zorder=4)

        ax.text(0, -1.25, "↔ 쌍방향·강함     ➔ 일방향·보통     ---> 점선·약함", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=8.5, weight='bold'), ha='center', va='center', color='#2D3436')
        ax.set_xlim(-1.35, 1.35)
        ax.set_ylim(-1.35, 1.35)
        plt.axis("off")
        plt.tight_layout()
        return fig

    col1, col2 = st.columns([2.2, 1])
    with col1:
        fig1 = draw_pretty_ecomap(st.session_state.nodes, st.session_state.client_name, chart_size)
        st.pyplot(fig1)

        # 이미지 다운로드 버튼
        buf1 = io.BytesIO()
        fig1.savefig(buf1, format="png", bbox_inches='tight', dpi=300)
        st.download_button(label="💾 생태도 고화질 이미지 다운로드", data=buf1.getvalue(), file_name=f"생태도_{st.session_state.client_name}.png", mime="image/png")

    with col2:
        st.subheader("👤 대상자 및 체계 관리")
        st.session_state.client_name = st.text_input("중앙 대상자 이름", value=st.session_state.client_name)
        st.markdown("---")
        with st.form("add_node_form"):
            node_name = st.text_input("체계명 (예: 경로당 등)")
            node_role = st.text_input("체계 역할 / 부가 설명")
            node_type = st.selectbox("체계 구분", ["공식체계", "비공식체계"])
            strength = st.selectbox("관계 강도", ["강함 (굵은 실선)", "보통 (일반 실선)", "약함 (점선)"])
            direction = st.selectbox("관계 방향", ["체계 ➔ 대상자", "대상자 ➔ 체계", "쌍방향 (↔)", "단순 연결"])
            if st.form_submit_button("체계 추가하기") and node_name:
                str_val = "강함" if "강함" in strength else ("약함" if "약함" in strength else "보통")
                st.session_state.nodes.append({"name": node_name, "role": node_role, "type": node_type, "strength": str_val, "direction": direction})
                st.rerun()

        for i, node in enumerate(st.session_state.nodes):
            c1, c2 = st.columns([3, 1])
            c1.write(f"• **{node['name']}** ({node.get('role', '')})")
            if c2.button("삭제", key=f"del_eco_{i}"):
                st.session_state.nodes.pop(i)
                st.rerun()

# ==========================================
# [TAB 2] 스마트 가계도 생성기
# ==========================================
with tab2:
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

    def draw_pretty_genogram(client, members, size):
        fig, ax = plt.subplots(figsize=(size, size), dpi=200)
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')

        parents = [m for m in members if "부" in m['relation'] or "모" in m['relation']]
        spouse = [m for m in members if "배우자" in m['relation']]
        children = [m for m in members if "자녀" in m['relation']]

        def draw_person(x, y, name, age, gender, is_alive, is_target=False, rel_type="보통"):
            box_s = 0.28
            color = '#FFEAA7' if is_target else ('#E3F2FD' if gender == '남성' else '#FCE4EC')
            edge_c = '#FDCB6E' if is_target else ('#1976D2' if gender == '남성' else '#C2185B')
            lw = 2.5 if is_target else 1.8

            if gender == '남성':
                rect = patches.Rectangle((x - box_s/2, y - box_s/2), box_s, box_s, facecolor=color, edgecolor=edge_c, linewidth=lw, zorder=3)
                ax.add_patch(rect)
            else:
                circle = patches.Circle((x, y), box_s/2, facecolor=color, edgecolor=edge_c, linewidth=lw, zorder=3)
                ax.add_patch(circle)

            if not is_alive:
                ax.plot([x - box_s/2.5, x + box_s/2.5], [y - box_s/2.5, y + box_s/2.5], color='#D63031', lw=2, zorder=4)
                ax.plot([x - box_s/2.5, x + box_s/2.5], [y + box_s/2.5, y - box_s/2.5], color='#D63031', lw=2, zorder=4)

            disp_txt = f"{name}\n({age}세)" if is_alive else f"{name}\n(사망)"
            ax.text(x, y - box_s/2 - 0.12, disp_txt, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=8.5, weight='bold'),
                    ha='center', va='top', color='#2D3436')

        cx, cy = (0, 0) if not spouse else (-0.4, 0)
        draw_person(cx, cy, client['name'], client['age'], client['gender'], client['is_alive'], is_target=True)

        if spouse:
            sx, sy = (0.4, 0)
            sp = spouse[0]
            draw_person(sx, sy, sp['name'], sp['age'], sp['gender'], sp['is_alive'], rel_type=sp['rel_type'])
            line_style = '-' if sp['rel_type'] != '소원/불화' else '--'
            color = '#D63031' if sp['rel_type'] == '소원/불화' else '#2D3436'
            ax.plot([cx + 0.14, sx - 0.14], [cy, sy], color=color, linestyle=line_style, lw=2, zorder=2)
            if sp['rel_type'] == '밀접/친밀':
                ax.plot([cx + 0.14, sx - 0.14], [cy + 0.03, sy + 0.03], color='#1976D2', lw=2, zorder=2)

        if parents:
            py = 0.8
            p_xs = np.linspace(-0.5, 0.5, len(parents))
            for idx, p in enumerate(parents):
                px = p_xs[idx]
                draw_person(px, py, p['name'], p['age'], p['gender'], p['is_alive'])
                ax.plot([px, cx], [py - 0.14, cy + 0.14], color='#B2BEC3', linestyle=':', lw=1.5, zorder=1)

        if children:
            chy = -0.8
            ch_xs = np.linspace(-0.6, 0.6, len(children))
            mid_x = (cx + sx)/2 if spouse else cx
            ax.plot([mid_x, mid_x], [cy - 0.14, cy - 0.45], color='#2D3436', lw=1.5, zorder=1)
            ax.plot([ch_xs[0], ch_xs[-1]], [cy - 0.45, cy - 0.45], color='#2D3436', lw=1.5, zorder=1)

            for idx, ch in enumerate(children):
                chx = ch_xs[idx]
                draw_person(chx, chy, ch['name'], ch['age'], ch['gender'], ch['is_alive'])
                ax.plot([chx, chx], [cy - 0.45, chy + 0.14], color='#2D3436', lw=1.5, zorder=1)

        ax.text(0, -1.35, "□ 남성   ○ 여성   [색상/굵은선] 당사자   [X] 사망   ═ 밀접   --- 불화", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=8, weight='bold'), ha='center', va='center', color='#636E72')
        ax.set_xlim(-1.4, 1.4)
        ax.set_ylim(-1.4, 1.4)
        plt.axis("off")
        plt.tight_layout()
        return fig

    g_col1, g_col2 = st.columns([2.2, 1])
    with g_col1:
        fig2 = draw_pretty_genogram(st.session_state.gen_client, st.session_state.family_members, chart_size)
        st.pyplot(fig2)

        buf2 = io.BytesIO()
        fig2.savefig(buf2, format="png", bbox_inches='tight', dpi=300)
        st.download_button(label="💾 가계도 고화질 이미지 다운로드", data=buf2.getvalue(), file_name=f"가계도_{st.session_state.gen_client['name']}.png", mime="image/png")

    with g_col2:
        st.subheader("👤 당사자(본인) 정보 설정")
        gc_name = st.text_input("이름", value=st.session_state.gen_client['name'])
        gc_gender = st.radio("성별", ["남성", "여성"], index=0 if st.session_state.gen_client['gender'] == "남성" else 1, horizontal=True)
        gc_age = st.text_input("나이", value=st.session_state.gen_client['age'])
        st.session_state.gen_client = {"name": gc_name, "gender": gc_gender, "age": gc_age, "is_alive": True}

        st.markdown("---")
        st.subheader("➕ 가족 구성원 추가")
        with st.form("add_family_form"):
            f_rel = st.selectbox("관계", ["배우자", "자녀", "부(아버지)", "모(어머니)"])
            f_name = st.text_input("이름/호칭 (예: 장남, 배우자)")
            f_gender = st.radio("성별", ["남성", "여성"], horizontal=True)
            f_age = st.text_input("나이 (사망 시 '사망' 입력)")
            f_rel_type = st.selectbox("당사자와의 관계", ["보통", "밀접/친밀", "소원/불화"])
            
            if st.form_submit_button("가족 추가하기") and f_name:
                is_alive = False if f_age == "사망" else True
                st.session_state.family_members.append({
                    "relation": f_rel, "name": f_name, "gender": f_gender, "age": f_age, "is_alive": is_alive, "rel_type": f_rel_type
                })
                st.rerun()

        st.markdown("---")
        st.subheader("🗑️ 등록된 가족 목록")
        for idx, m in enumerate(st.session_state.family_members):
            fc1, fc2 = st.columns([3, 1])
            fc1.write(f"• **[{m['relation']}] {m['name']}** ({m['gender']}/{m['age']})")
            if fc2.button("삭제", key=f"del_fam_{idx}"):
                st.session_state.family_members.pop(idx)
                st.rerun()
