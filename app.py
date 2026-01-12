import streamlit as st
import json
import pandas as pd
import random
import time
from engine import AbilityManager

# Page Configuration
st.set_page_config(page_title="5e Master Manager", layout="wide")

# Custom CSS
st.markdown("""
    <style>
        section[data-testid="stSidebar"] { width: 250px !important; }
        [data-testid="column"] { padding: 0 1rem; }
    </style>
""", unsafe_allow_html=True)

if 'engine' not in st.session_state:
    st.session_state.engine = AbilityManager()
engine = st.session_state.engine


# CALLBACKS 
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
        if bundle.get('library') is not None:
            engine.library = pd.DataFrame(bundle['library'])
        if bundle.get('loadout') is not None:
            engine.loadout = pd.DataFrame(bundle['loadout'])


# MAIN LAYOUT SPLIT 
col_main, col_right = st.columns([3, 1], gap="medium")

# LEFT SIDEBAR 
with st.sidebar:
    st.title("🧙‍♂️ Session Control")
    save_data = json.dumps({
        "res": {
            "Slots": {f"lvl_{i}": st.session_state.get(f"input_lvl_{i}", 0) for i in range(1, 10)},
            "Dice": st.session_state.get("dice_widget", 4)
        },
        "loadout": engine.loadout.to_dict(orient='records'),
        "library": engine.library.to_dict(orient='records') if not engine.library.empty else None
    })
    st.download_button("💾 Export Everything", data=save_data, file_name="session_bundle.json",
                       use_container_width=True)
    st.file_uploader("📂 Import Bundle", type=['json'], key="bundle_uploader", on_change=load_bundle_cb)
    st.divider()
    mode = st.radio("Resource Mode:", ["Spells", "Maneuvers"])
    if mode == "Spells":
        for lvl in range(1, 10): st.number_input(f"Lvl {lvl}", 0, 20, key=f"input_lvl_{lvl}")
    else:
        st.number_input("Dice Remaining", 0, 20, key="dice_widget")

# MAIN UI 
with col_main:
    #  SYSTEM MANUAL
    with st.expander("📖 COMPLETE SYSTEM MANUAL - Click to Open"):
        help_tabs = st.tabs(["🚀 Getting Started", "⚔️ Combat", "✍️ Homebrew", "💾 Saving/Loading"])

        with help_tabs[0]:
            st.markdown("""
            ### Initial Setup
            1. **Upload Libraries:** Drag and drop one or more JSON files (spells, maneuvers, or items) into the **Library Uploader**.
            2. **Browse & Filter:** Use the **📚 Library** tab. You can search by name or filter by Level (0-9).
            3. **Prepare:** Click **Prepare** on any ability. This moves it to your **Active Loadout** for quick access.

            **Note:** The top-right of each entry shows which file it came from!
            """)

        with help_tabs[1]:
            st.markdown("""
            ### Managing Combat
            1. **Resource Mode:** In the sidebar, select **Spells** (to track slots) or **Maneuvers** (to track dice/points).
            2. **The Dashboard:** Use the **🎯 Active Loadout** tab during your turn.
            3. **Consumption:** * **Cast:** Subtracts 1 slot from the corresponding level in the sidebar. (Cantrips are free).
                * **Use Dice:** Subtracts 1 from your "Dice Remaining" counter.
            4. **Quick Info:** Click **Details** on any prepared ability to see the full description without leaving the tab.
            """)

        with help_tabs[2]:
            st.markdown("""
            ### Creating Custom Content
            1. **The Creator:** Open the **✍️ Creator** tab.
            2. **Choose Type:**
                * **Spell:** Asks for Casting Time, Range, and Duration.
                * **Maneuver:** Asks for Resource Cost and Additional Info.
            3. **Saving:** Once added, these items appear in your Library. They are **permanently saved** when you export your Session Bundle.
            """)

        with help_tabs[3]:
            st.markdown("""
            ### Persistent Sessions (Very Important!)
            Streamlit apps "refresh" and lose data if the browser closes. To prevent this:
            1. **Export Everything:** Use the sidebar button. This bundles your **Library + Loadout + Resources** into one `.json` file.
            2. **The Reload:** Next time you play, **only upload your Bundle file** into the "Import Bundle" slot. 

            **Warning:** Do not re-upload the original library files if you are importing a bundle; the bundle already contains them!
            """)

    uploaded_files = st.file_uploader("Library Uploader (Multiple JSONs)", type=['json'], accept_multiple_files=True)
    if uploaded_files:
        for f in uploaded_files:
            engine.load_file(f)

    tab1, tab2, tab3 = st.tabs(["📚 Library", "🎯 Active Loadout", "✍️ Creator"])
    lvl_options = ["All"] + [str(i) for i in range(10)]

    with tab1:
        if not engine.library.empty:
            c1, c2 = st.columns([3, 1])
            search_lib = c1.text_input("Search Library...", key="lib_s")
            filter_lib = c2.selectbox("Level Filter", lvl_options, key="lib_f")
            lib_res = engine.library[engine.library['name'].str.contains(search_lib, case=False, na=False)]
            if filter_lib != "All":
                lib_res = lib_res[lib_res['level'] == int(filter_lib)]
            for idx, row in lib_res.iterrows():
                h_col, s_col = st.columns([4, 1])
                with h_col:
                    exp = st.expander(f"📖 {row['name']} (Lvl {row['level']})")
                with s_col:
                    st.caption(f"📂 {row.get('source_file', 'Custom')[:12]}")
                with exp:
                    st.caption(engine.parse_metadata(row));
                    st.write(row['description'])
                    if st.button("Prepare", key=f"p_{idx}"):
                        engine.add_to_loadout(row);
                        st.toast("Added!")

    with tab2:
        if not engine.loadout.empty:
            c1_lo, c2_lo = st.columns([3, 1])
            search_lo = c1_lo.text_input("Search Prepared...", key="lo_s")
            filter_lo = c2_lo.selectbox("Level Filter", lvl_options, key="lo_f")
            disp_load = engine.loadout.copy()
            disp_load = disp_load[disp_load['name'].str.contains(search_lo, case=False, na=False)]
            if filter_lo != "All":
                disp_load = disp_load[disp_load['level'] == int(filter_lo)]
            for idx, row in disp_load.iterrows():
                orig_idx = engine.loadout[engine.loadout['name'] == row['name']].index[0]
                with st.container(border=True):
                    t_col, r_col = st.columns([3, 1])
                    t_col.markdown(f"### {row['name']}")
                    tag = row.get('resource_cost') or row.get('source_file', 'Custom')
                    r_col.markdown(f"**`{tag}`**")
                    col_i, col_a = st.columns([4, 1])
                    with col_i:
                        st.caption(engine.parse_metadata(row));
                        with st.expander("Details"): st.write(row['description'])
                    with col_a:
                        lvl = int(row['level'])
                        if mode == "Spells":
                            st.button("Cast", key=f"c_lo_{idx}", on_click=cast_spell_cb, args=(lvl,))
                        else:
                            st.button("Use Dice", key=f"d_lo_{idx}", on_click=use_dice_cb)
                        if st.button("Remove", key=f"r_lo_{idx}"):
                            engine.remove_from_loadout(orig_idx);
                            st.rerun()

    with tab3:
        st.subheader("✍️ Creator")
        c_type = st.radio("Type", ["Spell", "Maneuver"], horizontal=True)
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name", key="cre_n");
            level = st.number_input("Level", 0, 9, key="cre_l")
        if c_type == "Spell":
            with c2:
                duration = st.text_input("Duration", key="cre_d")
            t_col, r_col = st.columns(2)
            t_text = t_col.text_input("Casting Time", key="cre_t");
            r_text = r_col.text_input("Range", key="cre_r")
            desc = st.text_area("Description", key="cre_desc_s")
            if st.button("Add Spell"):
                engine.add_custom_spell(name, level, t_text, r_text, duration, desc);
                st.rerun()
        else:
            with c2:
                res_cost = st.text_input("Resource Cost", key="cre_res")
            info = st.text_input("Additional Info", key="cre_info");
            desc = st.text_area("Description", key="cre_desc_m")
            if st.button("Add Maneuver"):
                engine.add_custom_maneuver(name, level, res_cost, info, desc);
                st.rerun()

# RIGHT SIDEBAR
with col_right:
    st.markdown("### 🎲 Dice & Logs")
    d_tab, h_tab = st.tabs(["Roller", "History"])

    with d_tab:
        with st.container(border=True):
            dtype = st.selectbox("Die", [20, 12, 10, 8, 6, 4], format_func=lambda x: f"d{x}")
            c_q, c_m = st.columns(2)
            damt = c_q.number_input("Qty", 1, 20, 1)
            dmod = c_m.number_input("Mod", -20, 20, 0)

            if st.button("🔥 ROLL", use_container_width=True):
                placeholder = st.empty()
                for _ in range(6):  # Animation
                    temp = [random.randint(1, dtype) for _ in range(damt)]
                    placeholder.markdown(
                        f"<h3 style='text-align: center; color: #555; margin:0;'>{' '.join(map(str, temp))}</h3>",
                        unsafe_allow_html=True)
                    time.sleep(0.05)

                rolls, total = engine.roll_dice(dtype, damt, dmod)
                color = "#FFD700" if (dtype == 20 and 20 in rolls) else "#00ffcc"
                if dtype == 20 and 1 in rolls: color = "#FF4B4B"

                placeholder.markdown(f"""
                    <div style="text-align: center; background: #1a1c24; border-radius: 10px; padding: 15px; border: 2px solid {color};">
                        <h1 style="color: {color}; margin: 0; font-size: 3rem;">{total}</h1>
                        <p style="color: #aaa; font-size: 0.8rem; margin: 0;">({'+ '.join(map(str, rolls))}) {'+' if dmod >= 0 else ''}{dmod}</p>
                    </div>
                """, unsafe_allow_html=True)

    with h_tab:
        if not engine.roll_history:
            st.caption("No rolls yet.")
        for item in engine.roll_history:
            with st.container(border=True):
                st.markdown(f"**{item['result']}** ({item['formula']})")
                st.caption(f"{item['time']} | {item['details']}")
