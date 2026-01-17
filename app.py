import streamlit as st
import json
import pandas as pd
import time
from engine import AbilityManager

st.set_page_config(page_title="Hero Manager Pro", layout="wide", initial_sidebar_state="expanded")

# --- UI STYLING ---
st.markdown("""
<style>
    .main { background: #0b0e14; color: #e0e0e0; }
    .stMetric { background: #161b22; border: 1px solid #30363d; border-radius: 10px; }
    .roll-card { text-align: center; background: #1f242d; border: 2px solid #58a6ff; border-radius: 8px; padding: 10px; }
    .manual-box { 
        background: rgba(88, 166, 255, 0.08); 
        border: 1px solid #58a6ff; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 20px; 
        font-size: 0.95rem;
    }
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

def learn_btn_cb(row):
    engine.learn_ability(row)
    st.toast(f"✨ {row['name']} added to Known list!")

def prep_btn_cb(row):
    engine.prepare_ability(row)
    st.toast(f"🎯 {row['name']} prepared in Loadout!")

def load_bundle_cb():
    if st.session_state.bundle_uploader:
        b = json.load(st.session_state.bundle_uploader)
        for lvl in range(1, 10): st.session_state[f"input_lvl_{lvl}"] = b['res']['Slots'].get(f"lvl_{lvl}", 0)
        st.session_state["dice_widget"] = b['res'].get("Dice", 4)
        if b.get('library') is not None: engine.library = pd.DataFrame(b['library'])
        if b.get('known') is not None: engine.known = pd.DataFrame(b['known'])
        if b.get('loadout') is not None: engine.loadout = pd.DataFrame(b['loadout'])
        if 'character' in b:
            c = b['character']
            engine.stats, engine.hp, engine.ac, engine.level = c['stats'], c['hp'], c['ac'], c['level']
            engine.proficiencies = c.get('proficiencies', [])
            engine.casting_stat = c.get('cast_stat', 'INT')

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Resources")
    res_mode = st.radio("Resource Mode", ["Spells", "Maneuvers"], horizontal=True)
    if res_mode == "Spells":
        for l in range(1, 10): st.number_input(f"Lvl {l} Slots", 0, 20, key=f"input_lvl_{l}")
    else:
        st.number_input("Dice Remaining", 0, 20, key="dice_widget")
    st.divider()
    if st.button("💤 Long Rest", use_container_width=True):
        st.toast(engine.long_rest()); st.rerun()

# --- HEADER ---
with st.container():
    h1, h2, h3, h4 = st.columns([2,1,1,1])
    with h1:
        st.write(f"**❤️ HP: {engine.hp['current']} / {engine.hp['max']}**")
        st.progress(engine.hp['current']/engine.hp['max'] if engine.hp['max'] > 0 else 0)
        adj_c1, adj_c2 = st.columns([2,1])
        adj = adj_c1.number_input("HP Change", -500, 500, 0, label_visibility="collapsed", key="hp_adj")
        if adj_c2.button("Apply"): engine.update_hp(adj); st.rerun()
    h2.metric("🛡️ AC", engine.ac)
    h3.metric("🧠 Spell DC", engine.get_dc(), help=f"8 + Prof + {engine.casting_stat} Mod")
    h4.metric("👁️ Passive Perc", engine.get_passive("Perception"))

st.divider()

# --- MAIN NAVIGATION ---
tabs = st.tabs(["👤 Hero", "📚 Library", "🧠 Known", "🎯 Loadout", "🌟 Traits", "✍️ Creator", "💾 Data"])

with tabs[0]: # HERO TAB
    st.markdown('<div class="manual-box"><b>USER MANUAL:</b> Click Stat cards for ability checks. Mark proficiency boxes to add your bonus to skills. <b>Edit Mode</b> lets you change stats and set your <b>Spellcasting Ability</b> for DC calculation.</div>', unsafe_allow_html=True)
    edit = st.toggle("🛠️ EDIT CHARACTER", key="hero_edit_toggle")
    if edit:
        c1, c2, c3, c4 = st.columns(4)
        engine.hp['max'] = c1.number_input("Max HP", 1, 500, engine.hp['max'], key="ed_hp")
        engine.ac = c2.number_input("Base AC", 0, 40, engine.ac, key="ed_ac")
        engine.level = c3.number_input("Level", 1, 20, engine.level, key="ed_lvl")
        engine.casting_stat = c4.selectbox("Spellcasting Stat (DC)", ["STR","DEX","CON","INT","WIS","CHA"], index=["STR","DEX","CON","INT","WIS","CHA"].index(engine.casting_stat), key="ed_cast")
        es = st.columns(6)
        for i, s in enumerate(engine.stats):
            engine.stats[s] = es[i].number_input(s, 0, 30, engine.stats[s], key=f"ed_stat_{s}")
    else:
        cols = st.columns(6)
        for i, (stat, val) in enumerate(engine.stats.items()):
            with cols[i]:
                mod = engine.get_mod(val)
                st.markdown(f"<div style='text-align:center;'><small>{stat}</small><br><span style='font-size:24px; color:#58a6ff;'><b>{mod:+}</b></span></div>", unsafe_allow_html=True)
                res_p = st.empty()
                if st.button("Roll", key=f"roll_{stat}", use_container_width=True):
                    r, t = engine.roll_dice(20, 1, mod)
                    res_p.markdown(f"<div class='roll-card'><b>{t}</b></div>", unsafe_allow_html=True); time.sleep(3); res_p.empty()
        st.divider()
        st.subheader("🎯 Skills")
        all_sk = {"Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT", "Athletics": "STR", "Deception": "CHA", "History": "INT", "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT", "Medicine": "WIS", "Nature": "INT", "Perception": "WIS", "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT", "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS"}
        skc1, skc2 = st.columns(2)
        for i, (sk, smap) in enumerate(all_sk.items()):
            target = skc1 if i < 9 else skc2
            with target:
                c1, c2, c3 = st.columns([1,4,2])
                prof = c1.checkbox("", key=f"p_check_{sk}", value=(sk in engine.proficiencies))
                if prof and sk not in engine.proficiencies: engine.proficiencies.append(sk)
                elif not prof and sk in engine.proficiencies: engine.proficiencies.remove(sk)
                bonus = engine.get_mod(engine.stats[smap]) + (engine.get_prof_bonus() if prof else 0)
                c2.write(f"**{sk}** <small>({smap})</small>", unsafe_allow_html=True)
                sr = st.empty()
                if c3.button(f"{bonus:+}", key=f"r_skill_{sk}", use_container_width=True):
                    r, t = engine.roll_dice(20, 1, bonus); sr.success(f"{t}"); time.sleep(2); sr.empty()

with tabs[1]: # LIBRARY TAB
    st.markdown('<div class="manual-box"><b>USER MANUAL:</b> Upload JSON libraries here. <b>Learn</b> adds a spell to your permanent collection (Known). <b>Prepare</b> moves it to your combat Loadout immediately.</div>', unsafe_allow_html=True)
    st.file_uploader("Upload Libraries", accept_multiple_files=True, key="lib_upload")
    if st.session_state.lib_upload:
        for f in st.session_state.lib_upload: engine.load_file(f)
    search = st.text_input("Filter Library...", key="lib_search")
    if not engine.library.empty:
        lib_res = engine.library[engine.library['name'].str.contains(search, case=False, na=False)]
        for idx, row in lib_res.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1: exp = st.expander(f"{row['name']} ({engine.parse_metadata(row)})")
            c2.button("Learn", key=f"l_btn_{idx}", on_click=learn_btn_cb, args=(row,), use_container_width=True)
            c3.button("Prepare", key=f"p_btn_{idx}", on_click=prep_btn_cb, args=(row,), use_container_width=True)
            with exp: st.write(row['description'])

with tabs[2]: # KNOWN TAB
    st.markdown('<div class="manual-box"><b>USER MANUAL:</b> This is your permanent spell collection. Click <b>Prepare</b> to move these into your combat Loadout for active use. Click <b>Forget</b> to remove them.</div>', unsafe_allow_html=True)
    if engine.known.empty: st.info("No abilities learned yet.")
    for idx, row in engine.known.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['name']}** ({engine.parse_metadata(row)})")
            c2.button("Prepare", key=f"k_prep_{idx}", on_click=prep_btn_cb, args=(row,), use_container_width=True)
            if c3.button("Forget", key=f"k_f_{idx}", use_container_width=True): engine.forget_ability(idx); st.rerun()

with tabs[3]: # LOADOUT TAB
    st.markdown('<div class="manual-box"><b>USER MANUAL:</b> Your active combat dashboard. Click <b>Cast</b> to subtract a spell slot from the sidebar automatically. Use <b>Remove</b> to unprepare.</div>', unsafe_allow_html=True)
    if engine.loadout.empty: st.info("Loadout is empty.")
    for idx, row in engine.loadout.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"### {row['name']}")
            if res_mode == "Spells":
                c2.button("Cast", key=f"lo_cast_{idx}", on_click=cast_spell_cb, args=(row['level'],), use_container_width=True)
            else:
                if c2.button("Use Dice", key=f"lo_dice_{idx}", use_container_width=True):
                    if st.session_state.dice_widget > 0: st.session_state.dice_widget -= 1; st.rerun()
            if c3.button("Remove", key=f"lo_rem_{idx}", use_container_width=True): engine.remove_from_loadout(idx); st.rerun()
            st.caption(engine.parse_metadata(row))
            with st.expander("Details"): st.write(row['description'])

with tabs[6]: # DATA TAB
    st.markdown('<div class="manual-box"><b>USER MANUAL:</b> Always <b>Export Save</b> before closing your browser to save your character. <b>Import Save</b> to restore your progress.</div>', unsafe_allow_html=True)
    save_b = json.dumps({
        "res": {"Slots": {f"lvl_{i}": st.session_state.get(f"input_lvl_{i}", 0) for i in range(1, 10)}, "Dice": st.session_state.get("dice_widget", 4)},
        "library": engine.library.to_dict(orient='records') if not engine.library.empty else None,
        "known": engine.known.to_dict(orient='records') if not engine.known.empty else None,
        "loadout": engine.loadout.to_dict(orient='records') if not engine.loadout.empty else None,
        "character": {"stats": engine.stats, "hp": engine.hp, "ac": engine.ac, "level": engine.level, "proficiencies": engine.proficiencies, "cast_stat": engine.casting_stat}
    })
    st.download_button("💾 Export Save Bundle", data=save_b, file_name="hero_save.json", use_container_width=True)
    st.file_uploader("📂 Import Save Bundle", type=['json'], key="bundle_uploader", on_change=load_bundle_cb)
