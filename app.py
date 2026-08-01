import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches
import matplotlib.path as mpath
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

# [핵심] 스케일 유지 + 스크롤 방지를 위해 스트림릿의 숨겨진 모든 수직 여백을 극한으로 깎아냅니다.
st.markdown("""
<style>
    .block-container { 
        padding-top: 0rem !important; 
        padding-bottom: 0rem !important; 
        margin-top: -50px !important; 
    }
    header { display: none !important; }
    div[data-testid="column"] { transition: none !important; } 
    /* 이미지와 다운로드 버튼 사이의 불필요한 간격을 없애 버튼을 위로 끌어올립니다. */
    div[data-testid="stImage"] { margin-bottom: -1.5rem !important; }
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
    st.session_state.gen_client = {"name": "홍길동", "gender": "남성", "age": "72", "is_alive": True, "is_cohabit": True}

if "family_members" not in st.session_state:
    st.session_state.family_members = [
        {"relation": "배우자", "name": "배우자", "gender": "여성", "age": "70", "is_alive": True, "rel_type": "밀접/친밀", "is_cohabit": True},
        {"relation": "자녀", "name": "장남", "gender": "남성", "age": "45", "is_alive": True, "rel_type": "보통", "is_cohabit": False},
        {"relation": "사위/며느리", "name": "큰며느리", "gender": "여성", "age": "43", "is_alive": True, "rel_type": "보통", "is_cohabit": False},
        {"relation": "자녀", "name": "차남", "gender": "남성", "age": "44", "is_alive": True, "rel_type": "보통", "is_cohabit": True}
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
            radii = [0.60] * count
            angles = np.linspace(start_angle, end_angle, count + 2)[1:-1] if count > 1 else [(start_angle + end_angle)/2]
        else:
            half = (count + 1) // 2
            radii = [0.55] * half + [0.72] * (count - half)
            angles_inner = np.linspace(start_angle, end_angle, half + 2)[1:-1]
            angles_outer = np.linspace(start_angle, end_angle, (count - half) + 2)[1:-1]
            angles = list(angles_inner) + list(angles_outer)

        for idx, n in enumerate(node_list):
            positions[n['name']] = (radii[idx] * np.cos(angles[idx]), radii[idx] * np.sin(angles[idx]))
        return positions

    def get_box_intersection_precise(center_x, center_y, width, height, target_x, target_y):
        dx = target_x - center_x
        dy = target_y - center_y
        if dx == 0 and dy == 0: return center_x, center_y
        w_margin = width / 2 + 0.012
        h_margin = height / 2 + 0.012
        scale_x = w_margin / abs(dx) if dx != 0 else float('inf')
        scale_y = h_margin / abs(dy) if dy != 0 else float('inf')
        scale = min(scale_x, scale_y)
        return center_x + dx * scale, center_y + dy * scale

    def draw_pretty_ecomap(nodes, client_name):
        fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=200)
        ax.set_aspect('equal')
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')

        center_id = client_name
        official = [n for n in nodes if n['type'] == "공식체계"]
        unofficial = [n for n in nodes if n['type'] == "비공식체계"]

        pos = {center_id: (0, 0)}
        pos.update(calculate_positions_ecomap(official, is_official=True))
        pos.update(calculate_positions_ecomap(unofficial, is_official=False))

        circle_r = 0.88
        ax.add_patch(plt.Circle((0, 0), circle_r, color='#B2BEC3', fill=False, linestyle='-', linewidth=1.2))
        ax.plot([0, 0], [-circle_r, circle_r], color='#B2BEC3', linestyle='--', linewidth=1.5, zorder=1)

        bbox_official = dict(boxstyle="round,pad=0.30", fc="#E3F2FD", ec="#1E88E5", lw=1.5)
        bbox_unofficial = dict(boxstyle="round,pad=0.30", fc="#E8F5E9", ec="#43A047", lw=1.5)

        ax.text(-0.45, circle_r, "공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=10.0, weight='bold'), ha='center', va='center', color='#0D47A1', zorder=2, bbox=bbox_official)
        ax.text(0.45, circle_r, "비공식체계", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=10.0, weight='bold'), ha='center', va='center', color='#1B5E20', zorder=2, bbox=bbox_unofficial)

        center_r = 0.14
        ax.scatter(0, 0, s=1800, color='#FFEAA7', edgecolors='#FDCB6E', linewidth=2.0, zorder=2)
        ax.text(0, 0, center_id, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=9.5, weight='bold'), ha='center', va='center', color='#2D3436', zorder=3)

        box_w, box_h = 0.38, 0.145

        def draw_node_box(n_list, bg_color, border_color):
            for n in n_list:
                x, y = pos[n['name']]
                rect = patches.FancyBboxPatch(
                    (x - box_w/2, y - box_h/2), box_w, box_h,
                    boxstyle="round,pad=0.01,rounding_size=0.025",
                    facecolor=bg_color, edgecolor=border_color, linewidth=1.2, zorder=3
                )
                ax.add_patch(rect)
                if n.get('role'):
                    ax.text(x, y + 0.028, n['name'], fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=7.2, weight='bold'), ha='center', va='center', color='#2D3436', zorder=4)
                    ax.text(x, y - 0.032, f"({n['role']})", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=5.0), ha='center', va='center', color='#636E72', zorder=4)
                else:
                    ax.text(x, y, n['name'], fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=7.2, weight='bold'), ha='center', va='center', color='#2D3436', zorder=4)

        draw_node_box(official, "#E3F2FD", "#90CAF9")
        draw_node_box(unofficial, "#E8F5E9", "#A5D6A7")

        for n in nodes:
            x, y = pos[n['name']]
            lw = 2.0 if "강" in n['strength'] else (1.0 if "약" in n['strength'] else 1.3)
            style = 'dashed' if "약" in n['strength'] else 'solid'
            color = '#000000' if "강" in n['strength'] else ('#636E72' if "약" in n['strength'] else '#2D3436')
            bx, by = get_box_intersection_precise(x, y, box_w, box_h, 0, 0)
            angle = np.arctan2(y, x)
            cx = (center_r + 0.01) * np.cos(angle)
            cy = (center_r + 0.01) * np.sin(angle)

            if "체계 ➔ 대상자" in n['direction']: p_from, p_to, a_style = (bx, by), (cx, cy), "->"
            elif "대상자 ➔ 체계" in n['direction']: p_from, p_to, a_style = (cx, cy), (bx, by), "->"
            elif "쌍방향" in n['direction']: p_from, p_to, a_style = (bx, by), (cx, cy), "<->"
            else: p_from, p_to, a_style = (bx, by), (cx, cy), "-"

            arrow_patch = patches.FancyArrowPatch(p_from, p_to, arrowstyle=a_style, linestyle=style, linewidth=lw, color=color, mutation_scale=8.5, zorder=5)
            ax.add_patch(arrow_patch)

        ax.set_xlim(-1.25, 1.25)
        ax.set_ylim(-1.25, 1.25)
        plt.axis("off")
        fig.tight_layout(pad=0.0) 
        return fig

    fig1 = draw_pretty_ecomap(st.session_state.nodes, st.session_state.client_name)
    
    # [비율 고정] 3.0~3.1 비율로 화면에 꽉 차면서도 스크롤을 유발하지 않도록 최적화
    col_e1, col_e2, col_e3 = st.columns([1, 3.0, 1])
    with col_e2:
        buf1 = io.BytesIO()
        fig1.savefig(buf1, format="png", bbox_inches='tight', pad_inches=0.0, dpi=300)
        st.image(buf1, use_container_width=True)
        st.download_button(label="💾 생태도 이미지 다운로드", data=buf1.getvalue(), file_name=f"생태도_{st.session_state.client_name}.png", mime="image/png", use_container_width=True)

# =============================================================
# [MODE 2] 가계도 모드
# =============================================================
else:
    st.sidebar.header("👨‍👩‍👧‍👦 [가계도] 정보 입력")
    
    gc_name = st.sidebar.text_input("당사자 이름", value=st.session_state.gen_client['name'], key="gen_name")
    gc_gender = st.sidebar.radio("당사자 성별", ["남성", "여성"], index=0 if st.session_state.gen_client['gender'] == "남성" else 1, horizontal=True, key="gen_gender")
    gc_age = st.sidebar.text_input("당사자 나이", value=st.session_state.gen_client['age'], key="gen_age")
    gc_cohabit = st.sidebar.checkbox("🏠 당사자 동거 여부", value=st.session_state.gen_client.get('is_cohabit', True), key="gen_cohabit")
    
    st.session_state.gen_client = {"name": gc_name, "gender": gc_gender, "age": gc_age, "is_alive": True, "is_cohabit": gc_cohabit}

    st.sidebar.markdown("---")
    
    with st.sidebar.form("add_family_form"):
        st.subheader("➕ 가족/동거인 추가")
        f_rel = st.selectbox("관계 구분", ["배우자", "자녀", "동거인", "사위/며느리", "손자/손녀", "부(아버지)", "모(어머니)", "반려동물"])
        f_name = st.text_input("이름/호칭 (예: 장남, 큰며느리, 차남 등)")
        f_gender = st.radio("성별", ["남성", "여성", "기타(반려동물)"], horizontal=True, key="fam_gender")
        f_age = st.text_input("나이 (사망 시 '사망' 입력)")
        f_rel_type = st.selectbox("당사자/가족과의 관계 상태", ["동거/혼인", "사실혼", "동거인", "별거", "이혼", "불화/갈등", "소원", "단절", "보통", "밀접/친밀"])
        f_cohabit = st.checkbox("🏠 현재 당사자와 동거 중", value=False)
        
        if st.form_submit_button("가족/동거인 추가하기") and f_name:
            is_alive = False if f_age == "사망" else True
            st.session_state.family_members.append({
                "relation": f_rel, "name": f_name, "gender": f_gender, "age": f_age, "is_alive": is_alive, "rel_type": f_rel_type, "is_cohabit": f_cohabit
            })
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ 등록된 가족/동거인 목록")
    for idx, m in enumerate(st.session_state.family_members):
        fc1, fc2 = st.sidebar.columns([3, 1])
        co_icon = "🏠" if m.get('is_cohabit', False) else "🚪"
        fc1.write(f"• **[{m['relation']}] {m['name']}** ({m['rel_type']}) {co_icon}")
        if fc2.button("삭제", key=f"del_fam_{idx}"):
            st.session_state.family_members.pop(idx)
            st.rerun()

    def draw_pretty_genogram(client, members):
        fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=200)
        ax.set_aspect('equal') 
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')

        parents = [m for m in members if "부" in m['relation'] or "모" in m['relation']]
        spouse = [m for m in members if "배우자" in m['relation']]
        cohabitants = [m for m in members if "동거인" in m['relation']]
        children = [m for m in members if "자녀" in m['relation']]
        in_laws = [m for m in members if "사위" in m['relation'] or "며느리" in m['relation']]
        grand_children = [m for m in members if "손자" in m['relation']]
        pets = [m for m in members if "반려동물" in m['relation']]

        cohabit_points = []

        def draw_person(x, y, name, age, gender, is_alive, is_target=False):
            box_s = 0.18
            color = '#FFEAA7' if is_target else ('#E3F2FD' if gender == '남성' else ('#FCE4EC' if gender == '여성' else '#E8F5E9'))
            edge_c = '#FDCB6E' if is_target else ('#1976D2' if gender == '남성' else ('#C2185B' if gender == '여성' else '#388E3C'))
            lw = 2.2 if is_target else 1.5

            if gender == '남성':
                rect = patches.Rectangle((x - box_s/2, y - box_s/2), box_s, box_s, facecolor=color, edgecolor=edge_c, linewidth=lw, zorder=4)
                ax.add_patch(rect)
            elif gender == '여성':
                circle = patches.Circle((x, y), box_s/2, facecolor=color, edgecolor=edge_c, linewidth=lw, zorder=4)
                ax.add_patch(circle)
            else:
                diamond = patches.RegularPolygon((x, y), numVertices=4, radius=box_s/1.6, facecolor=color, edgecolor=edge_c, linewidth=lw, zorder=4)
                ax.add_patch(diamond)

            if not is_alive:
                ax.plot([x - box_s/2.2, x + box_s/2.2], [y - box_s/2.2, y + box_s/2.2], color='#D63031', lw=1.8, zorder=5)
                ax.plot([x - box_s/2.2, x + box_s/2.2], [y + box_s/2.2, y - box_s/2.2], color='#D63031', lw=1.8, zorder=5)

            disp_txt = f"{name}\n({age}세)" if is_alive else f"{name}\n(사망)"
            ax.text(x, y - box_s/2 - 0.03, disp_txt, fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'),
                    ha='center', va='top', color='#2D3436', zorder=5)

        cx, cy = (0, 0.85) if (not spouse and not cohabitants) else (-0.45, 0.85)
        draw_person(cx, cy, client['name'], client['age'], client['gender'], client['is_alive'], is_target=True)
        if client.get('is_cohabit', True): cohabit_points.append((cx, cy))

        if spouse:
            sx, sy = (0.45, 0.85)
            sp = spouse[0]
            draw_person(sx, sy, sp['name'], sp['age'], sp['gender'], sp['is_alive'])
            if sp.get('is_cohabit', False): cohabit_points.append((sx, sy))

            rel = sp.get('rel_type', '동거/혼인')
            mid_x = (cx + sx) / 2
            lbl_bbox = dict(boxstyle="round,pad=0.2", fc="#FFFFFF", ec="none", alpha=0.85)

            if rel == '사실혼':
                ax.plot([cx + 0.1, sx - 0.1], [cy, sy], color='#2D3436', linestyle='--', lw=1.5, zorder=2)
                ax.text(mid_x, cy + 0.08, "사실혼", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#27AE60', zorder=4, bbox=lbl_bbox)
            elif rel == '이혼':
                ax.plot([cx + 0.1, sx - 0.1], [cy, sy], color='#2D3436', lw=1.5, zorder=2)
                ax.plot([mid_x - 0.04, mid_x - 0.01], [cy - 0.05, cy + 0.05], color='#D63031', lw=1.8, zorder=3)
                ax.plot([mid_x + 0.01, mid_x + 0.04], [cy - 0.05, cy + 0.05], color='#D63031', lw=1.8, zorder=3)
                ax.text(mid_x, cy + 0.08, "이혼", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#D63031', zorder=4, bbox=lbl_bbox)
            elif rel == '별거':
                ax.plot([cx + 0.1, sx - 0.1], [cy, sy], color='#2D3436', lw=1.5, zorder=2)
                ax.plot([mid_x, mid_x + 0.03], [cy - 0.05, cy + 0.05], color='#E67E22', lw=1.8, zorder=3)
                ax.text(mid_x, cy + 0.08, "별거", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#E67E22', zorder=4, bbox=lbl_bbox)
            elif rel == '불화/갈등':
                xs = np.linspace(cx + 0.1, sx - 0.1, 20)
                ys = cy + 0.02 * np.sin(xs * 30)
                ax.plot(xs, ys, color='#D63031', lw=1.8, zorder=2)
                ax.text(mid_x, cy + 0.08, "불화", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#D63031', zorder=4, bbox=lbl_bbox)
            elif rel == '소원':
                ax.plot([cx + 0.1, sx - 0.1], [cy, sy], color='#7F8C8D', linestyle='--', lw=1.5, zorder=2)
                ax.text(mid_x, cy + 0.08, "소원", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#7F8C8D', zorder=4, bbox=lbl_bbox)
            elif rel == '단절':
                ax.plot([cx + 0.1, sx - 0.1], [cy, sy], color='#2D3436', lw=1.5, zorder=2)
                ax.plot([mid_x - 0.03, mid_x + 0.03], [cy - 0.04, cy + 0.04], color='#2D3436', lw=2.0, zorder=3)
                ax.plot([mid_x - 0.03, mid_x + 0.03], [cy + 0.04, cy - 0.04], color='#2D3436', lw=2.0, zorder=3)
                ax.text(mid_x, cy + 0.08, "단절", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#2D3436', zorder=4, bbox=lbl_bbox)
            elif rel == '밀접/친밀':
                ax.plot([cx + 0.1, sx - 0.1], [cy + 0.015, sy + 0.015], color='#1976D2', lw=1.8, zorder=2)
                ax.plot([cx + 0.1, sx - 0.1], [cy - 0.015, sy - 0.015], color='#1976D2', lw=1.8, zorder=2)
                ax.text(mid_x, cy + 0.08, "친밀", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#1976D2', zorder=4, bbox=lbl_bbox)
            else:
                ax.plot([cx + 0.1, sx - 0.1], [cy, sy], color='#2D3436', lw=1.5, zorder=2)

        if cohabitants and not spouse:
            coh = cohabitants[0]
            coh_x, coh_y = (0.45, 0.85)
            draw_person(coh_x, coh_y, coh['name'], coh['age'], coh['gender'], coh['is_alive'])
            if coh.get('is_cohabit', True): cohabit_points.append((coh_x, coh_y))

            mid_x = (cx + coh_x) / 2
            lbl_bbox = dict(boxstyle="round,pad=0.2", fc="#FFFFFF", ec="none", alpha=0.85)
            ax.plot([cx + 0.1, coh_x - 0.1], [cy, coh_y], color='#2E7D32', linestyle=':', lw=1.5, zorder=2)
            ax.text(mid_x, cy + 0.08, "동거인", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='center', va='center', color='#2E7D32', zorder=4, bbox=lbl_bbox)

        # 2. 부모님 (1세대)
        if parents:
            py = 1.25
            father = [p for p in parents if "부" in p['relation']]
            mother = [p for p in parents if "모" in p['relation']]
            p_fx, p_mx = -0.45, 0.45

            if father:
                draw_person(p_fx, py, father[0]['name'], father[0]['age'], father[0]['gender'], father[0]['is_alive'])
                if father[0].get('is_cohabit'): cohabit_points.append((p_fx, py))
            if mother:
                draw_person(p_mx, py, mother[0]['name'], mother[0]['age'], mother[0]['gender'], mother[0]['is_alive'])
                if mother[0].get('is_cohabit'): cohabit_points.append((p_mx, py))

            if father and mother:
                ax.plot([p_fx + 0.1, p_mx - 0.1], [py, py], color='#B2BEC3', linestyle='--', lw=1.2, zorder=1)
                p_mid_y = py - 0.20
                ax.plot([0, 0], [py, p_mid_y], color='#B2BEC3', linestyle=':', lw=1.2, zorder=1)
                ax.plot([0, cx], [p_mid_y, p_mid_y], color='#B2BEC3', linestyle=':', lw=1.2, zorder=1)
                ax.plot([cx, cx], [p_mid_y, cy + 0.1], color='#B2BEC3', linestyle=':', lw=1.2, zorder=1)

        # 3. 자녀 세대 배치 (선 겹침 및 간격 자동 조절 로직)
        child_coords_map = {}
        if children:
            chy = 0.35
            branch_y = 0.55 
            
            family_groups = []
            for ch_idx, ch in enumerate(children):
                il = in_laws[ch_idx] if ch_idx < len(in_laws) else None
                if il:
                    family_groups.append({"type": "pair", "child": ch, "in_law": il, "child_idx": ch_idx})
                else:
                    family_groups.append({"type": "single", "child": ch, "child_idx": ch_idx})

            group_count = len(family_groups)
            parent_mid_x = (cx + (sx if spouse else (coh_x if cohabitants else cx))) / 2
            
            if group_count == 1:
                group_xs = [parent_mid_x]
            else:
                spacing = min(0.55, 3.0 / (group_count - 1))
                total_w = spacing * (group_count - 1)
                group_xs = list(np.linspace(parent_mid_x - total_w/2, parent_mid_x + total_w/2, group_count))

            for g_idx, group in enumerate(family_groups):
                gx = group_xs[g_idx]
                ch = group['child']

                if group['type'] == 'single':
                    draw_person(gx, chy, ch['name'], ch['age'], ch['gender'], ch['is_alive'])
                    child_coords_map[group['child_idx']] = gx
                    if ch.get('is_cohabit'): cohabit_points.append((gx, chy))
                else:
                    il = group['in_law']
                    ch_x = gx - 0.15
                    il_x = gx + 0.15
                    
                    draw_person(ch_x, chy, ch['name'], ch['age'], ch['gender'], ch['is_alive'])
                    draw_person(il_x, chy, il['name'], il['age'], il['gender'], il['is_alive'])
                    
                    ax.plot([ch_x + 0.09, il_x - 0.09], [chy, chy], color='#2D3436', lw=1.2, zorder=2)
                    
                    child_coords_map[group['child_idx']] = ch_x
                    if ch.get('is_cohabit'): cohabit_points.append((ch_x, chy))
                    if il.get('is_cohabit'): cohabit_points.append((il_x, chy))

                    if grand_children:
                        gcy = -0.15
                        gc_mid = (ch_x + il_x) / 2
                        ax.plot([gc_mid, gc_mid], [chy, chy - 0.18], color='#2D3436', lw=1.2, zorder=1)
                        
                        gc_xs = list(np.linspace(gc_mid - 0.22, gc_mid + 0.22, len(grand_children))) if len(grand_children) > 1 else [gc_mid]
                        if len(grand_children) > 1:
                            ax.plot([gc_xs[0], gc_xs[-1]], [chy - 0.18, chy - 0.18], color='#2D3436', lw=1.2, zorder=1)

                        for g_idx, gc in enumerate(grand_children):
                            grx = gc_xs[g_idx]
                            draw_person(grx, gcy, gc['name'], gc['age'], gc['gender'], gc['is_alive'])
                            ax.plot([grx, grx], [chy - 0.18, gcy + 0.1], color='#2D3436', lw=1.2, zorder=1)
                            if gc.get('is_cohabit'): cohabit_points.append((grx, gcy))

            real_ch_xs = [child_coords_map[k] for k in sorted(child_coords_map.keys())]

            if group_count == 1:
                target_gx = group_xs[0]
                ax.plot([target_gx, target_gx], [cy - 0.1, chy + 0.1], color='#2D3436', lw=1.3, zorder=1)
            else:
                ax.plot([parent_mid_x, parent_mid_x], [cy - 0.1, branch_y], color='#2D3436', lw=1.3, zorder=1)
                ax.plot([real_ch_xs[0], real_ch_xs[-1]], [branch_y, branch_y], color='#2D3436', lw=1.3, zorder=1)

                for ch_idx, ch in enumerate(children):
                    chx = child_coords_map[ch_idx]
                    ch_rel = ch.get('rel_type', '보통')
                    ch_mid_y = (branch_y + (chy + 0.1)) / 2 
                    lbl_bbox_small = dict(boxstyle="round,pad=0.15", fc="#FFFFFF", ec="none", alpha=0.85)

                    if ch_rel == '불화/갈등':
                        ax.plot([chx, chx], [branch_y, chy + 0.1], color='#D63031', linestyle='--', lw=1.5, zorder=2)
                        ax.text(chx + 0.08, ch_mid_y, "불화", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='left', va='center', color='#D63031', zorder=4, bbox=lbl_bbox_small)
                    elif ch_rel == '소원':
                        ax.plot([chx, chx], [branch_y, chy + 0.1], color='#7F8C8D', linestyle='--', lw=1.3, zorder=2)
                        ax.text(chx + 0.08, ch_mid_y, "소원", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='left', va='center', color='#7F8C8D', zorder=4, bbox=lbl_bbox_small)
                    elif ch_rel == '단절':
                        ax.plot([chx, chx], [branch_y, chy + 0.1], color='#2D3436', lw=1.3, zorder=2)
                        ax.plot([chx - 0.03, chx + 0.03], [ch_mid_y - 0.03, ch_mid_y + 0.03], color='#2D3436', lw=1.8, zorder=3)
                        ax.plot([chx - 0.03, chx + 0.03], [ch_mid_y + 0.03, ch_mid_y - 0.03], color='#2D3436', lw=1.8, zorder=3)
                        ax.text(chx + 0.08, ch_mid_y, "단절", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='left', va='center', color='#2D3436', zorder=4, bbox=lbl_bbox_small)
                    elif ch_rel == '밀접/친밀':
                        ax.plot([chx - 0.015, chx - 0.015], [branch_y, chy + 0.1], color='#1976D2', lw=1.5, zorder=2)
                        ax.plot([chx + 0.015, chx + 0.015], [branch_y, chy + 0.1], color='#1976D2', lw=1.5, zorder=2)
                        ax.text(chx + 0.08, ch_mid_y, "친밀", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=6.5, weight='bold'), ha='left', va='center', color='#1976D2', zorder=4, bbox=lbl_bbox_small)
                    else:
                        ax.plot([chx, chx], [branch_y, chy + 0.1], color='#2D3436', lw=1.3, zorder=1)

        # 5. 반려동물
        if pets:
            pet_y = 0.35 if not children else -0.15
            pet_x = 1.10
            for p_idx, pt in enumerate(pets):
                px = pet_x - (p_idx * 0.28)
                draw_person(px, pet_y, pt['name'], pt['age'], pt['gender'], pt['is_alive'])
                if pt.get('is_cohabit'): cohabit_points.append((px, pet_y))

        # 6. 다각형 하단 확장 및 관계선 교차 방지 로직
        if len(cohabit_points) > 0:
            y_groups = {}
            for px, py in cohabit_points:
                found = False
                for gy in y_groups.keys():
                    if abs(gy - py) < 0.1:
                        y_groups[gy].append(px)
                        found = True
                        break
                if not found:
                    y_groups[py] = [px]
            
            sorted_ys = sorted(y_groups.keys(), reverse=True)
            
            min_x = {gy: min(y_groups[gy]) - 0.24 for gy in sorted_ys}
            max_x = {gy: max(y_groups[gy]) + 0.24 for gy in sorted_ys}
            top_y = {gy: gy + 0.22 for gy in sorted_ys}
            
            bot_y = {}
            for gy in sorted_ys:
                if abs(gy - 0.85) < 0.1: 
                    bot_y[gy] = gy - 0.24 
                else: 
                    bot_y[gy] = gy - 0.32 

            bridge_y = {}
            for i in range(1, len(sorted_ys)):
                top_layer = sorted_ys[i-1]
                bot_layer = sorted_ys[i]
                bridge_y[(top_layer, bot_layer)] = (bot_y[top_layer] + top_y[bot_layer]) / 2.0

            verts = []
            codes = []
            
            for i, gy in enumerate(sorted_ys):
                mx = min_x[gy]
                ty = top_y[gy]
                by = bot_y[gy]
                if i == 0:
                    verts.append((mx, ty))
                    codes.append(mpath.Path.MOVETO)
                else:
                    prev_gy = sorted_ys[i-1]
                    mid_y = bridge_y[(prev_gy, gy)]
                    prev_mx = min_x[prev_gy]
                    verts.append((prev_mx, mid_y))
                    codes.append(mpath.Path.LINETO)
                    verts.append((mx, mid_y))
                    codes.append(mpath.Path.LINETO)
                    verts.append((mx, ty))
                    codes.append(mpath.Path.LINETO)
                verts.append((mx, by))
                codes.append(mpath.Path.LINETO)
                
            reversed_ys = list(reversed(sorted_ys))
            for i, gy in enumerate(reversed_ys):
                mx = max_x[gy]
                by = bot_y[gy]
                ty = top_y[gy]
                if i == 0:
                    verts.append((mx, by))
                    codes.append(mpath.Path.LINETO)
                else:
                    prev_gy = reversed_ys[i-1]
                    mid_y = bridge_y[(gy, prev_gy)]
                    prev_mx = max_x[prev_gy]
                    verts.append((prev_mx, mid_y))
                    codes.append(mpath.Path.LINETO)
                    verts.append((mx, mid_y))
                    codes.append(mpath.Path.LINETO)
                    verts.append((mx, by))
                    codes.append(mpath.Path.LINETO)
                verts.append((mx, ty))
                codes.append(mpath.Path.LINETO)
                
            verts.append((min_x[sorted_ys[0]], top_y[sorted_ys[0]]))
            codes.append(mpath.Path.CLOSEPOLY)
            
            path = mpath.Path(verts, codes)
            patch = patches.PathPatch(path, facecolor="#E8F5E9", edgecolor="#2E7D32", 
                                      linestyle="--", linewidth=2.5, alpha=0.35, 
                                      zorder=0, joinstyle='round', capstyle='round')
            ax.add_patch(patch)
            
            top_y_val = top_y[sorted_ys[0]]
            mid_x_val = (min_x[sorted_ys[0]] + max_x[sorted_ys[0]]) / 2.0
            ax.text(mid_x_val, top_y_val + 0.03, "🏠 동거 가족 영역", fontproperties=fm.FontProperties(fname="NanumGothic.ttf", size=7.5, weight='bold'), ha='center', va='bottom', color='#1B5E20', zorder=1)

        ax.set_xlim(-1.65, 1.65)
        ax.set_ylim(-1.80, 1.50)
        
        plt.axis("off")
        fig.tight_layout(pad=0.0) 
        return fig

    fig2 = draw_pretty_genogram(st.session_state.gen_client, st.session_state.family_members)
    
    col_g1, col_g2, col_g3 = st.columns([1, 3.0, 1])
    with col_g2:
        buf2 = io.BytesIO()
        fig2.savefig(buf2, format="png", bbox_inches='tight', pad_inches=0.0, dpi=300)
        st.image(buf2, use_container_width=True)
        st.download_button(label="💾 가계도 이미지 다운로드", data=buf2.getvalue(), file_name=f"가계도_{st.session_state.gen_client['name']}.png", mime="image/png", use_container_width=True)
