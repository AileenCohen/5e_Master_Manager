import streamlit as st
import json
import pandas as pd
import time
from engine import AbilityManager

st.set_page_config(page_title="Character Manager V1.9", layout="wide", initial_sidebar_state="expanded")

# --- STYLING ---
st.markdown("""
<style>
    .main { background: #0b0e14; color: #e0e0e0; }
    .stMetric { background: #161b22; border: 1px solid #30363d; border-radius: 10px; }
    .manual-box { background: rgba(88, 166, 255, 0.08); border-left: 5px solid #58a6ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.9rem; }
    .roll-card { text-align: center; background: #1f242d; border: 2px solid #58a6ff; border-radius: 8px; padding: 10px; margin-bottom: 5px; }
    .history-card { background: #1c2128; border: 1px solid #30363d; padding: 8px; border-radius: 5px; margin-bottom: 5px; }
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
                engine.stats, engine.hp, engine.ac, engine.level = c['stats'], c['hp'], c['ac'], c['level']
                engine.casting_stat = c.get('cast_stat', 'INT')
                engine.proficiencies = c.get('proficiencies', [])
                engine.save_profs = c.get('save_profs', [])
            if b.get('library') is not None: engine.library = pd.DataFrame(b['library'])
            if b.get('known') is not None: engine.known = pd.DataFrame(b['known'])
            if b.get('loadout') is not None: engine.loadout = pd.DataFrame(b['loadout'])
            engine.features = b.get('features', [])
        except: st.error("Import Failed")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Resources")
    side_tabs = st.tabs(["Slots", "History"])
    with side_tabs[0]:
        for l in range(1, 10): st.number_input(f"Lvl {l} Slots", 0, 20, key=f"input_lvl_{l}")
        st.divider()
        if st.button("💤 Long Rest", use_container_width=True):
            st.toast(engine.long_rest()); st.rerun()
    with side_tabs[1]:
        st.subheader("🎲 Roll Log")
        if st.button("Clear History", use_container_width=True): engine.roll_history = []; st.rerun()
        for roll in engine.roll_history:
            st.markdown(f'<div class="history-card"><div style="display:flex; justify-content:space-between;"><span style="color:#58a6ff;"><b>{roll["result"]}</b></span><small style="color:#8b949e;">{roll["time"]}</small></div><small style="color:#8b949e;">{roll["formula"]}</small></div>', unsafe_allow_html=True)

# --- HEADER ---
with st.container():
    h1, h2, h3, h4 = st.columns([2,1,1,1])
    with h1:
        st.write(f"**❤️ HP: {engine.hp['current']} / {engine.hp['max']}**")
        st.progress(engine.hp['current']/engine.hp['max'] if engine.hp['max'] > 0 else 0)
        adj_c1, adj_c2 = st.columns([2,1])
        adj = adj_c1.number_input("HP Adj", -500, 500, 0, label_visibility="collapsed", key="hp_adj")
        if adj_c2.button("Apply"): engine.update_hp(adj); st.rerun()
    h2.metric("🛡️ AC", engine.ac)
    h3.metric("🧠 Spell DC", engine.get_dc())
    h4.metric("👁️ Passive", engine.get_passive("Perception"))

st.divider()

# --- MAIN NAV ---
tabs = st.tabs(["👤 Hero", "📚 Library", "🧠 Known", "🎯 Loadout", "🌟 Traits", "✍️ Creator", "💾 Data"])

with tabs[0]: # HERO
    st.markdown('<div class="manual-box"><b>Hero Tab:</b> Roll checks, saves, and skills. Check boxes for <b>Proficiency</b>. Use <b>Edit Mode</b> to set stats and your <b>Spellcasting Stat</b>.</div>', unsafe_allow_html=True)
    edit = st.toggle("🛠️ EDIT MODE", key="hero_edit_toggle")
    if edit:
        c1, c2, c3, c4 = st.columns(4)
        engine.hp['max'] = c1.number_input("Max HP", 1, 500, engine.hp['max'], key="ed_hp")
        engine.ac = c2.number_input("AC", 0, 40, engine.ac, key="ed_ac")
        engine.level = c3.number_input("Level", 1, 20, engine.level, key="ed_lvl")
        engine.casting_stat = c4.selectbox("DC Stat:", ["STR","DEX","CON","INT","WIS","CHA"], index=["STR","DEX","CON","INT","WIS","CHA"].index(engine.casting_stat), key="ed_cast")
        es = st.columns(6)
        for i, s in enumerate(engine.stats): engine.stats[s] = es[i].number_input(s, 0, 30, engine.stats[s], key=f"ed_stat_{s}")
    else:
        cols = st.columns(6)
        for i, (stat, val) in enumerate(engine.stats.items()):
            with cols[i]:
                mod = engine.get_mod(val)
                st.markdown(f"<div style='text-align:center;'><small>{stat}</small><br><span style='font-size:24px; color:#58a6ff;'><b>{mod:+}</b></span></div>", unsafe_allow_html=True)
                res_p = st.empty()
                if st.button("Roll", key=f"roll_{stat}", use_container_width=True):
                    total = engine.roll_dice(20, 1, mod)
                    res_p.markdown(f"<div class='roll-card'><b>{total}</b></div>", unsafe_allow_html=True); time.sleep(3); res_p.empty()
        st.divider(); st.subheader("🛡️ Saving Throws")
        sv1, sv2 = st.columns(2)
        for i, stat in enumerate(engine.stats.keys()):
            target = sv1 if i < 3 else sv2
            with target:
                c1, c2, c3 = st.columns([1,4,2])
                is_p = c1.checkbox("", key=f"sv_p_{stat}", value=(stat in engine.save_profs))
                if is_p and stat not in engine.save_profs: engine.save_profs.append(stat)
                elif not is_p and stat in engine.save_profs: engine.save_profs.remove(stat)
                bonus = engine.get_mod(engine.stats[stat]) + (engine.get_prof_bonus() if is_p else 0)
                c2.write(f"**{stat} Save**")
                res_sv = st.empty()
                if c3.button(f"{bonus:+}", key=f"roll_sv_{stat}", use_container_width=True):
                    t = engine.roll_dice(20, 1, bonus); res_sv.success(f"{t}"); time.sleep(2); res_sv.empty()
        st.divider(); st.subheader("🎯 Skills")
        all_sk = {"Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT", "Athletics": "STR", "Deception": "CHA", "History": "INT", "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT", "Medicine": "WIS", "Nature": "INT", "Perception": "WIS", "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT", "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS"}
        skc1, skc2 = st.columns(2)
        for i, (sk, smap) in enumerate(all_sk.items()):
            target = skc1 if i < 9 else skc2
            with target:
                c1, c2, c3 = st.columns([1,4,2]); prof = c1.checkbox("", key=f"p_c_{sk}", value=(sk in engine.proficiencies))
                if prof and sk not in engine.proficiencies: engine.proficiencies.append(sk)
                elif not prof and sk in engine.proficiencies: engine.proficiencies.remove(sk)
                bonus = engine.get_mod(engine.stats[smap]) + (engine.get_prof_bonus() if prof else 0)
                c2.write(f"**{sk}** <small>({smap})</small>", unsafe_allow_html=True)
                res_sk = st.empty()
                if c3.button(f"{bonus:+}", key=f"r_s_{sk}", use_container_width=True):
                    t = engine.roll_dice(20, 1, bonus); res_sk.info(f"{t}"); time.sleep(2); res_sk.empty()

with tabs[1]: # LIBRARY
    st.markdown('<div class="manual-box"><b>Library:</b> Upload JSONs. <b>Learn</b> adds to Known. <b>Prepare</b> sends to Loadout.</div>', unsafe_allow_html=True)
    st.file_uploader("Upload Libraries", accept_multiple_files=True, key="lib_upload")
    if st.session_state.lib_upload:
        for f in st.session_state.lib_upload: engine.load_file(f)
    search = st.text_input("Filter Library...", key="lib_search")
    if not engine.library.empty:
        lib_res = engine.library[engine.library['name'].str.contains(search, case=False, na=False)]
        for idx, row in lib_res.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1: exp = st.expander(f"{row['name']} ({engine.parse_metadata(row)})")
            if c2.button("Learn", key=f"l_b_{idx}"): engine.learn_ability(row); st.toast("Learned")
            if c3.button("Prepare", key=f"p_b_{idx}"): engine.prepare_ability(row); st.toast("Prepared")
            with exp: st.write(row['description'])

with tabs[2]: # KNOWN
    st.markdown('<div class="manual-box"><b>Known:</b> Permanent collection. Click <b>Prepare</b> for Loadout.</div>', unsafe_allow_html=True)
    if engine.known.empty: st.info("No abilities learned.")
    for idx, row in engine.known.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['name']}** ({engine.parse_metadata(row)})")
            if c2.button("Prepare", key=f"k_p_{idx}"): engine.prepare_ability(row); st.toast("Prepared")
            if c3.button("Forget", key=f"k_f_{idx}"): engine.forget_ability(idx); st.rerun()
            with st.expander("Details"): st.write(row['description'])

with tabs[3]: # LOADOUT
    st.markdown('<div class="manual-box"><b>Loadout:</b> Active combat dashboard. <b>Cast</b> subtracts a slot from the sidebar.</div>', unsafe_allow_html=True)
    if engine.loadout.empty: st.info("Loadout is empty.")
    for idx, row in engine.loadout.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"### {row['name']}")
            if c2.button("Cast", key=f"lo_cast_{idx}", on_click=cast_spell_cb, args=(row['level'],)): st.rerun()
            if c3.button("Remove", key=f"lo_rem_{idx}"): engine.remove_from_loadout(idx); st.rerun()
            st.caption(engine.parse_metadata(row))
            with st.expander("Show Text"): st.write(row['description'])

with tabs[4]: # TRAITS
    st.markdown('<div class="manual-box"><b>Traits:</b> Custom racial traits or feats.</div>', unsafe_allow_html=True)
    with st.expander("➕ Add Trait"):
        f_n = st.text_input("Name", key="tr_n"); f_d = st.text_area("Effect", key="tr_d")
        if st.button("Save Trait"): engine.features.append({"name": f_n, "desc": f_d}); st.rerun()
    for i, feat in enumerate(engine.features):
        with st.container(border=True):
            c1, c2 = st.columns([4, 1]); c1.markdown(f"**{feat['name']}**")
            if c2.button("🗑️", key=f"del_f_{i}"): engine.features.pop(i); st.rerun()
            st.write(feat['desc'])

with tabs[5]: # CREATOR
    st.markdown('<div class="manual-box"><b>Creator:</b> Design homebrew Spells/Maneuvers. Saved items go to <b>Library</b>.</div>', unsafe_allow_html=True)
    m_cr = st.radio("Type", ["Spell", "Maneuver"], horizontal=True, key="cr_t")
    c1, c2 = st.columns(2)
    with c1: cr_n = st.text_input("Name", key="cr_name"); cr_l = st.number_input("Lvl", 0, 9, key="cr_lvl")
    with c2:
        if m_cr == "Spell": cr_ti = st.text_input("Time", key="cr_time"); cr_r = st.text_input("Range", key="cr_rng")
        else: cr_co = st.text_input("Cost", key="cr_cost")
    cr_de = st.text_area("Effect Text", key="cr_desc")
    if st.button("✨ Save to Library"):
        if m_cr == "Spell": engine.add_custom_spell(cr_n, cr_l, cr_ti, cr_r, cr_de)
        else: engine.add_custom_maneuver(cr_n, cr_l, cr_co, cr_de)
        st.success("Added!"); st.rerun()

with tabs[6]: # DATA
    save_b = json.dumps({
        "res": {"Slots": {f"lvl_{i}": st.session_state.get(f"input_lvl_{i}", 0) for i in range(1, 10)}, "Dice": st.session_state.get("dice_widget", 4)},
        "library": engine.library.to_dict(orient='records') if not engine.library.empty else None,
        "known": engine.known.to_dict(orient='records') if not engine.known.empty else None,
        "loadout": engine.loadout.to_dict(orient='records') if not engine.loadout.empty else None,
        "features": engine.features,
        "character": {"stats": engine.stats, "hp": engine.hp, "ac": engine.ac, "level": engine.level, "proficiencies": engine.proficiencies, "save_profs": engine.save_profs, "cast_stat": engine.casting_stat}
    })
    st.download_button("💾 Export Bundle", data=save_b, file_name="hero_save.json", use_container_width=True)
    st.file_uploader("📂 Import Bundle", type=['json'], key="bundle_uploader", on_change=load_bundle_cb)
