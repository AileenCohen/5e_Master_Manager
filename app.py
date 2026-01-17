import streamlit as st
import json
import pandas as pd
import random
import time
from engine import AbilityManager

st.set_page_config(page_title="5e Master Manager", layout="wide")
st.markdown("<style>section[data-testid='stSidebar'] { width: 250px !important; }</style>", unsafe_allow_html=True)

if 'engine' not in st.session_state:
    st.session_state.engine = AbilityManager()
engine = st.session_state.engine

# --- CALLBACKS ---
def cast_spell_cb(lvl):
    key = f"input_lvl_{lvl}"
    if key in st.session_state and st.session_state[key] > 0:
        st.session_state[key] -= 1

def use_dice_cb():
    if "dice_widget" in st.session_state and st.session_state["dice_widget"] > 0:
        st.session_state["dice_widget"] -= 1

def load_bundle_cb():
    if st.session_state.bundle_uploader:
        bundle = json.load(st.session_state.bundle_uploader)
        for lvl in range(1, 10):
            st.session_state[f"input_lvl_{lvl}"] = bundle['res']['Slots'].get(f"lvl_{lvl}", 0)
        st.session_state["dice_widget"] = bundle['res'].get("Dice", 4)
        if bundle.get('library') is not None: engine.library = pd.DataFrame(bundle['library'])
        if bundle.get('known') is not None: engine.known = pd.DataFrame(bundle['known'])
        if bundle.get('loadout') is not None: engine.loadout = pd.DataFrame(bundle['loadout'])
        if 'character' in bundle:
            char = bundle['character']
            engine.stats = char.get('stats', engine.stats)
            engine.hp = char.get('hp', engine.hp)
            engine.ac = char.get('ac', engine.ac)
            engine.level = char.get('level', engine.level)
            engine.proficiencies = char.get('proficiencies', [])

# --- MAIN LAYOUT ---
col_main, col_dice = st.columns([3, 1], gap="medium")

with st.sidebar:
    st.title("🧙‍♂️ Session Control")
    save_data = json.dumps({
        "res": {"Slots": {f"lvl_{i}": st.session_state.get(f"input_lvl_{i}", 0) for i in range(1, 10)}, "Dice": st.session_state.get("dice_widget", 4)},
        "library": engine.library.to_dict(orient='records') if not engine.library.empty else None,
        "known": engine.known.to_dict(orient='records') if not engine.known.empty else None,
        "loadout": engine.loadout.to_dict(orient='records') if not engine.loadout.empty else None,
        "character": {
            "stats": engine.stats, "hp": engine.hp, "ac": engine.ac,
            "level": engine.level, "proficiencies": engine.proficiencies
        }
    })
    st.download_button("💾 Export Everything", data=save_data, file_name="session_bundle.json", use_container_width=True)
    st.file_uploader("📂 Import Bundle", type=['json'], key="bundle_uploader", on_change=load_bundle_cb)
    st.divider()
    mode = st.radio("Resource Mode:", ["Spells", "Maneuvers"])
    if mode == "Spells":
        for lvl in range(1, 10): st.number_input(f"Lvl {lvl}", 0, 20, key=f"input_lvl_{lvl}")
    else: st.number_input("Dice Remaining", 0, 20, key="dice_widget")

with col_main:
    # --- FULL SYSTEM MANUAL ---
    with st.expander("📖 COMPLETE SYSTEM MANUAL - Click to Open"):
        help_tabs = st.tabs(["🚀 Setup", "👤 Character Sheet", "⚔️ Combat", "🧠 Spell Management", "💾 Saving"])
        
        with help_tabs[0]:
            st.markdown("""
            ### Initial Setup
            1. **Upload Libraries:** Drag and drop JSON files into the **Library Uploader**.
            2. **The Source:** The top-right of entries shows which file they came from.
            """)

        with help_tabs[1]:
            st.markdown("""
            ### Character Sheet
            1. **Stats & Skills:** Bonuses calculate automatically.
            2. **Edit Mode:** Toggle to change base scores. **⚠️ YOU MUST PRESS ENTER** after typing to save.
            3. **Rolls:** Result cards appear directly above buttons for 5 seconds.
            """)
            
        with help_tabs[2]:
            st.markdown("""
            ### Combat
            1. **Mode:** Switch between Spell Slots or Maneuver Dice in the sidebar.
            2. **Dashboard:** Use the **🎯 Active Loadout** tab during your turn to cast or use abilities.
            """)

        with help_tabs[3]:
            st.markdown("""
            ### Flexible Spell Management
            - **Divine/Prepared Casters (Cleric/Paladin/Martials):** Go to **📚 Library** and click **Prepare**. It goes straight to your Loadout.
            - **Spells Known Casters (Wizard/Sorcerer/Bard):** 1. Go to **📚 Library** and click **Learn** to add to your **🧠 Known** tab (Spellbook).
                2. During a rest, go to the **🧠 Known** tab and click **Prepare** for today's list.
            """)
            
        with help_tabs[4]:
            st.markdown("""
            ### Persistent Sessions
            Streamlit clears on refresh. Use **Export Everything** to create a `.json` backup. Use **Import Bundle** to restore your Library, Known Spells, Loadout, and Stats.
            """)

    uploaded_files = st.file_uploader("Library Uploader", type=['json'], accept_multiple_files=True)
    if uploaded_files:
        for f in uploaded_files: engine.load_file(f)

    tab_sheet, tab_lib, tab_known, tab_load, tab_cre = st.tabs(["👤 Sheet", "📚 Library", "🧠 Known", "🎯 Active Loadout", "✍️ Creator"])
    
    with tab_sheet:
        edit_mode = st.toggle("🛠️ EDIT MODE - Press ENTER after typing!", value=False)
        st.divider()

        if edit_mode:
            st.subheader("🛠️ Character Editor")
            e1, e2, e3 = st.columns(3)
            engine.hp['max'] = e1.number_input("Max HP", 1, 500, engine.hp['max'])
            engine.ac = e2.number_input("Base AC", 0, 40, engine.ac)
            engine.level = e3.number_input("Level", 1, 20, engine.level)
            es = st.columns(6)
            for i, s in enumerate(engine.stats):
                engine.stats[s] = es[i].number_input(s, 0, 30, engine.stats[s], key=f"ed_{s}")
        else:
            hp_col, ac_col, init_col, prof_col = st.columns([2, 1, 1, 1])
            with hp_col:
                st.write(f"**HP: {engine.hp['current']} / {engine.hp['max']}**")
                st.progress(engine.hp['current'] / engine.hp['max'] if engine.hp['max'] > 0 else 0)
                h1, h2, h3 = st.columns([2, 1, 1])
                amt = h1.number_input("Amt", 0, 500, 0, key="hp_in", label_visibility="collapsed")
                if h2.button("💥 Hit", use_container_width=True): engine.update_hp(-amt); st.rerun()
                if h3.button("💚 Heal", use_container_width=True): engine.update_hp(amt); st.rerun()
            ac_col.metric("AC", engine.ac)
            init_col.metric("Init", f"{engine.get_mod(engine.stats['DEX']):+}")
            prof_col.metric("Prof", f"+{engine.get_prof_bonus()}")

            st.divider()
            sc = st.columns(6)
            for i, s in enumerate(engine.stats):
                with sc[i]:
                    mod = engine.get_mod(engine.stats[s])
                    st.markdown(f"<p style='text-align:center; margin:0;'>{s}</p><h2 style='text-align:center; color:#00ffcc; margin:0;'>{mod:+}</h2>", unsafe_allow_html=True)
                    res_p = st.empty()
                    if st.button("Roll", key=f"br_{s}", use_container_width=True):
                        r, t = engine.roll_dice(20, 1, mod)
                        res_p.markdown(f"<div style='text-align:center; background:#1a1c24; border:1px solid #00ffcc; border-radius:5px;'><h3 style='color:#00ffcc; margin:0;'>{t}</h3><small>({r[0]}{mod:+})</small></div>", unsafe_allow_html=True)
                        time.sleep(5); res_p.empty()

        st.divider()
        st.subheader("🎯 Skills")
        skills = {"Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT", "Athletics": "STR", "Deception": "CHA", "History": "INT", "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT", "Medicine": "WIS", "Nature": "INT", "Perception": "WIS", "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT", "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS"}
        sk1, sk2 = st.columns(2)
        for i, (sk, st_map) in enumerate(skills.items()):
            target = sk1 if i < 9 else sk2
            with target:
                res_sk = st.empty()
                c_p, c_n, c_r = st.columns([1, 4, 2])
                is_p = c_p.checkbox("", key=f"prof_{sk}", value=(sk in engine.proficiencies))
                if is_p and sk not in engine.proficiencies: engine.proficiencies.append(sk)
                elif not is_p and sk in engine.proficiencies: engine.proficiencies.remove(sk)
                mod = engine.get_mod(engine.stats[st_map])
                total = mod + (engine.get_prof_bonus() if is_p else 0)
                c_n.markdown(f"**{sk}** <small>({st_map})</small>", unsafe_allow_html=True)
                if c_r.button(f"{total:+}", key=f"roll_{sk}", use_container_width=True):
                    r, t = engine.roll_dice(20, 1, total)
                    res_sk.markdown(f"<div style='text-align:center; background:#1a1c24; border:1px solid #00ffcc; border-radius:5px;'><h4 style='color:#00ffcc; margin:0;'>{t}</h4></div>", unsafe_allow_html=True)
                    time.sleep(5); res_sk.empty()

    with tab_lib:
        if not engine.library.empty:
            lc1, lc2 = st.columns([3, 1])
            search = lc1.text_input("Search Library...", key="lib_s")
            filt = lc2.selectbox("Filter Level", ["All"]+[str(i) for i in range(10)], key="lib_f")
            lib_res = engine.library[engine.library['name'].str.contains(search, case=False, na=False)]
            if filt != "All": lib_res = lib_res[lib_res['level'] == int(filt)]
            for idx, row in lib_res.iterrows():
                h, s, p = st.columns([3, 1, 1])
                with h: exp = st.expander(f"📖 {row['name']} ({row['level']})")
                with s: 
                    if st.button("Learn", key=f"learn_{idx}", use_container_width=True):
                        engine.learn_spell(row); st.toast(f"{row['name']} learned!")
                with p:
                    if st.button("Prepare", key=f"libprep_{idx}", use_container_width=True):
                        engine.add_to_loadout(row); st.toast(f"{row['name']} prepared!")
                with exp:
                    st.caption(engine.parse_metadata(row)); st.write(row['description'])

    with tab_known:
        st.subheader("🧠 Known Spells")
        if engine.known.empty: st.info("Learn spells from the Library tab first.")
        else:
            for idx, row in engine.known.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**{row['name']}** ({engine.parse_metadata(row)})")
                    if c2.button("Prepare", key=f"prep_{idx}", use_container_width=True):
                        engine.add_to_loadout(row); st.toast(f"{row['name']} prepared!")
                    if c3.button("Forget", key=f"unl_{idx}", use_container_width=True):
                        engine.unlearn_spell(idx); st.rerun()

    with tab_load:
        st.subheader("🎯 Active Loadout")
        if not engine.loadout.empty:
            for idx, row in engine.loadout.iterrows():
                with st.container(border=True):
                    t_c, r_c = st.columns([3, 1])
                    t_c.markdown(f"### {row['name']}")
                    ci, ca = st.columns([4, 1])
                    with ci: 
                        st.caption(engine.parse_metadata(row))
                        with st.expander("Details"): st.write(row['description'])
                    with ca:
                        if mode == "Spells": st.button("Cast", key=f"c_lo_{idx}", on_click=cast_spell_cb, args=(int(row['level']),))
                        else: st.button("Use Dice", key=f"d_lo_{idx}", on_click=use_dice_cb)
                        if st.button("Remove", key=f"unp_{idx}", use_container_width=True): engine.remove_from_loadout(idx); st.rerun()

    with tab_cre:
        st.subheader("✍️ Creator")
        c_type = st.radio("Type", ["Spell", "Maneuver"], horizontal=True)
        c1, c2 = st.columns(2)
        with c1: name = st.text_input("Name"); level = st.number_input("Level", 0, 9)
        if c_type == "Spell":
            with c2: dur = st.text_input("Duration")
            if st.button("Add Spell"): engine.add_custom_spell(name, level, "", "", dur, ""); st.rerun()
        else:
            with c2: cost = st.text_input("Resource Cost")
            if st.button("Add Maneuver"): engine.add_custom_maneuver(name, level, cost, "", ""); st.rerun()

# --- DICE COLUMN ---
with col_dice:
    st.markdown("### 🎲 Dice Tray")
    sides = st.selectbox("Die", [20, 12, 10, 8, 6, 4], format_func=lambda x: f"d{x}")
    cq, cm = st.columns(2)
    qty = cq.number_input("Qty", 1, 20, 1); mod = cm.number_input("Mod", -20, 20, 0)
    if st.button("🔥 ROLL", use_container_width=True):
        r, t = engine.roll_dice(sides, qty, mod)
        st.markdown(f"<div style='text-align:center; background:#1a1c24; border:2px solid #00ffcc;'><h1 style='color:#00ffcc;'>{t}</h1></div>", unsafe_allow_html=True)
    st.divider()
    for item in engine.roll_history[:5]:
        st.caption(f"{item['time']} | {item['formula']} = **{item['result']}**")