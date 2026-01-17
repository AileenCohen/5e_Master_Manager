import streamlit as st
import json
import pandas as pd
import time
from engine import AbilityManager

st.set_page_config(page_title="Hero Manager Pro", layout="wide")

# --- UI STYLING ---
st.markdown("""
<style>
    .main { background: #0b0e14; color: #e0e0e0; }
    .stMetric { background: #161b22; border: 1px solid #30363d; border-radius: 10px; }
    .tab-manual { background: rgba(88, 166, 255, 0.08); border-left: 5px solid #58a6ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

if 'engine' not in st.session_state:
    st.session_state.engine = AbilityManager()
engine = st.session_state.engine

# --- CALLBACKS ---
def cast_spell_cb(lvl):
    key = f"input_lvl_{lvl}"
    if key in st.session_state and st.session_state[key] > 0:
        st.session_state[key] -= 1

def load_bundle_cb():
    if st.session_state.bundle_uploader:
        try:
            b = json.load(st.session_state.bundle_uploader)
            if 'character' in b:
                c = b['character']
                engine.stats = c.get('stats', engine.stats)
                engine.hp = c.get('hp', engine.hp)
                engine.ac = c.get('ac', engine.ac)
                engine.level = c.get('level', engine.level)
                engine.casting_stat = c.get('cast_stat', 'INT')
            if 'library' in b and b['library'] is not None: engine.library = pd.DataFrame(b['library'])
            if 'known' in b and b['known'] is not None: engine.known = pd.DataFrame(b['known'])
            if 'loadout' in b and b['loadout'] is not None: engine.loadout = pd.DataFrame(b['loadout'])
            engine.features = b.get('features', [])
        except Exception as e:
            st.error(f"Import failed: {e}")

# --- HEADER ---
with st.container():
    h1, h2, h3, h4 = st.columns([2,1,1,1])
    with h1:
        st.write(f"**❤️ HP: {engine.hp['current']} / {engine.hp['max']}**")
        st.progress(engine.hp['current']/engine.hp['max'] if engine.hp['max'] > 0 else 0)
        adj_c1, adj_c2 = st.columns([2,1])
        adj = adj_c1.number_input("Hit/Heal", -500, 500, 0, label_visibility="collapsed", key="hp_adj")
        if adj_c2.button("Apply"): engine.update_hp(adj); st.rerun()
    h2.metric("🛡️ AC", engine.ac)
    h3.metric("🧠 Spell DC", engine.get_dc())
    h4.metric("👁️ Passive", engine.get_passive("Perception"))

st.divider()

# --- TABS ---
tabs = st.tabs(["👤 Hero", "📚 Library", "🧠 Known", "🎯 Loadout", "🌟 Traits", "✍️ Creator", "💾 Data"])

with tabs[0]: # HERO
    st.markdown('<div class="tab-manual"><b>HERO SHEET:</b> Roll checks or saves. Toggle <b>Edit Mode</b> to set base scores and <b>Spellcasting Stat</b>.</div>', unsafe_allow_html=True)
    edit = st.toggle("🛠️ EDIT CHARACTER", key="hero_edit_toggle")
    if edit:
        c1, c2, c3, c4 = st.columns(4)
        engine.hp['max'] = c1.number_input("Max HP", 1, 500, engine.hp['max'], key="ed_hp")
        engine.ac = c2.number_input("AC", 0, 40, engine.ac, key="ed_ac")
        engine.level = c3.number_input("Level", 1, 20, engine.level, key="ed_lvl")
        engine.casting_stat = c4.selectbox("DC Stat:", ["STR","DEX","CON","INT","WIS","CHA"], index=["STR","DEX","CON","INT","WIS","CHA"].index(engine.casting_stat), key="ed_cast")
        es = st.columns(6)
        for i, s in enumerate(engine.stats):
            engine.stats[s] = es[i].number_input(s, 0, 30, engine.stats[s], key=f"ed_stat_{s}")
    else:
        cols = st.columns(6)
        for i, (stat, val) in enumerate(engine.stats.items()):
            with cols[i]:
                mod = engine.get_mod(val)
                st.markdown(f"<div style='text-align:center;'><small>{stat}</small><br><span style='font-size:24px; color:#58a6ff;'><b>{mod:+}</b></span></div>", unsafe_allow_html=True)
                if st.button("Roll", key=f"roll_{stat}", use_container_width=True):
                    rolls, total = engine.roll_dice(20, 1, mod)
                    st.toast(f"{stat} Roll: {total}")

with tabs[1]: # LIBRARY
    st.markdown('<div class="tab-manual"><b>LIBRARY:</b> Upload JSONs. <b>Learn</b> adds to Known. <b>Prepare</b> sends to Loadout.</div>', unsafe_allow_html=True)
    st.file_uploader("Upload Libraries", accept_multiple_files=True, key="lib_upload")
    if st.session_state.lib_upload:
        for f in st.session_state.lib_upload: engine.load_file(f)
    search = st.text_input("Filter Library...", key="lib_search")
    if not engine.library.empty:
        res = engine.library[engine.library['name'].str.contains(search, case=False, na=False)]
        for idx, row in res.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1: exp = st.expander(f"{row['name']} ({engine.parse_metadata(row)})")
            c2.button("Learn", key=f"l_btn_{idx}", on_click=engine.learn_ability, args=(row,), use_container_width=True)
            c3.button("Prepare", key=f"p_btn_{idx}", on_click=engine.prepare_ability, args=(row,), use_container_width=True)
            with exp: st.write(row['description'])

with tabs[2]: # KNOWN
    st.markdown('<div class="tab-manual"><b>KNOWN:</b> Permanent collection. Click <b>Prepare</b> to move to Loadout.</div>', unsafe_allow_html=True)
    if engine.known.empty: st.info("No abilities learned.")
    for idx, row in engine.known.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{row['name']}** ({engine.parse_metadata(row)})")
            c2.button("Prepare", key=f"k_prep_{idx}", on_click=engine.prepare_ability, args=(row,), use_container_width=True)
            with st.expander("Show Details"): st.write(row['description'])

with tabs[6]: # DATA
    save_b = json.dumps({
        "res": {"Slots": {f"lvl_{i}": st.session_state.get(f"input_lvl_{i}", 0) for i in range(1, 10)}, "Dice": st.session_state.get("dice_widget", 4)},
        "library": engine.library.to_dict(orient='records') if not engine.library.empty else None,
        "known": engine.known.to_dict(orient='records') if not engine.known.empty else None,
        "loadout": engine.loadout.to_dict(orient='records') if not engine.loadout.empty else None,
        "features": engine.features,
        "character": {"stats": engine.stats, "hp": engine.hp, "ac": engine.ac, "level": engine.level, "proficiencies": engine.proficiencies, "cast_stat": engine.casting_stat}
    })
    st.download_button("💾 Export Bundle", data=save_b, file_name="hero_save.json", use_container_width=True)
    st.file_uploader("📂 Import Bundle", type=['json'], key="bundle_uploader", on_change=load_bundle_cb)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Resources")
    for l in range(1, 10): st.number_input(f"Lvl {l} Slots", 0, 20, key=f"input_lvl_{l}")
    st.divider()
    if st.button("💤 Long Rest", use_container_width=True):
        st.toast(engine.long_rest()); st.rerun()
