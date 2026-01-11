import streamlit as st
import json
import pandas as pd
from engine import AbilityManager

st.set_page_config(page_title="5e Master Manager", layout="wide")

if 'engine' not in st.session_state:
    st.session_state.engine = AbilityManager()

engine = st.session_state.engine


# --- NEW BUNDLED PERSISTENCE LOGIC ---
def get_bundled_save_data():
    """Bundles Library, Loadout, and Resources into one file."""
    return json.dumps({
        "res": {
            "Slots": {f"lvl_{i}": st.session_state.get(f"input_lvl_{i}", 0) for i in range(1, 10)},
            "Dice": st.session_state.get("dice_widget", 4)
        },
        "loadout": engine.loadout.to_dict(orient='records'),
        "library": engine.library.to_dict(orient='records') if not engine.library.empty else None,
        "filename": engine.current_file_name
    })


def load_bundled_state_cb():
    """Unpacks everything from the bundle."""
    if st.session_state.bundle_uploader is not None:
        bundle = json.load(st.session_state.bundle_uploader)

        # 1. Restore Resources
        for lvl in range(1, 10):
            st.session_state[f"input_lvl_{lvl}"] = bundle['res']['Slots'].get(f"lvl_{lvl}", 0)
        st.session_state["dice_widget"] = bundle['res'].get("Dice", 4)

        # 2. Restore Library (The missing piece!)
        if bundle.get('library'):
            engine.library = pd.DataFrame(bundle['library'])
            engine.current_file_name = bundle.get('filename', "Restored_Library")

        # 3. Restore Loadout
        if bundle.get('loadout'):
            engine.loadout = pd.DataFrame(bundle['loadout'])

        st.success("Full Session Restored!")


# --- CALLBACKS FOR CASTING ---
def cast_spell_cb(lvl):
    key = f"input_lvl_{lvl}"
    if key in st.session_state and st.session_state[key] > 0:
        st.session_state[key] -= 1


def use_dice_cb():
    if "dice_widget" in st.session_state and st.session_state["dice_widget"] > 0:
        st.session_state["dice_widget"] -= 1


# --- SIDEBAR ---
with st.sidebar:
    st.title("🧙‍♂️ Session Bundle")

    # The "One-Click" Save/Load
    st.subheader("💾 Full Session Save")
    st.download_button(
        "Export All Data",
        data=get_bundled_save_data(),
        file_name="5e_session_bundle.json",
        help="Saves Library + Prepared + Slots into one file."
    )

    st.file_uploader(
        "Import All Data",
        type=['json'],
        key="bundle_uploader",
        on_change=load_bundled_state_cb
    )

    st.divider()
    mode = st.radio("Resource Mode:", ["Spells", "Maneuvers"])
    if mode == "Spells":
        for lvl in range(1, 10):
            st.number_input(f"Lvl {lvl}", 0, 20, key=f"input_lvl_{lvl}")
    else:
        st.number_input("Dice Remaining", 0, 20, key="dice_widget")

# --- MAIN UI ---
st.header("🛡️ 5e Master Manager")

# Still allow fresh library uploads
lib_file = st.file_uploader("Upload New Library JSON", type=['json'])
if lib_file:
    engine.load_file(lib_file)

tab1, tab2 = st.tabs(["📚 Ability Library", "🎯 Active Loadout"])
lvl_options = ["All"] + [str(i) for i in range(10)]

with tab1:
    if engine.library.empty:
        st.info("Library is empty. Upload a Library JSON or Import a Session Bundle.")
    else:
        c1, c2 = st.columns([3, 1])
        search_lib = c1.text_input("Search Library...")
        filter_lib = c2.selectbox("Level Filter", lvl_options, key="lib_f")

        lib_res = engine.library[engine.library['name'].str.contains(search_lib, case=False, na=False)]
        if filter_lib != "All":
            lib_res = lib_res[lib_res['level'] == int(filter_lib)]

        for idx, row in lib_res.iterrows():
            with st.expander(f"📖 [Lvl {row['level']}] {row['name']}"):
                st.caption(engine.parse_metadata(row))
                st.write(row['description'])
                if st.button("Prepare", key=f"p_{idx}"):
                    engine.add_to_loadout(row)
                    st.toast(f"{row['name']} Prepared!")

with tab2:
    if engine.loadout.empty:
        st.info("No prepared abilities.")
    else:
        c1_lo, c2_lo = st.columns([3, 1])
        search_lo = c1_lo.text_input("Search Prepared...")
        filter_lo = c2_lo.selectbox("Level Filter", lvl_options, key="lo_f")

        disp_load = engine.loadout.copy()
        disp_load = disp_load[disp_load['name'].str.contains(search_lo, case=False, na=False)]
        if filter_lo != "All":
            disp_load = disp_load[disp_load['level'] == int(filter_lo)]

        for idx, row in disp_load.iterrows():
            orig_idx = engine.loadout[engine.loadout['name'] == row['name']].index[0]
            with st.container(border=True):
                col_i, col_a = st.columns([4, 1])
                lvl = int(row.get('level', 0))
                with col_i:
                    st.markdown(f"### {row['name']}")
                    st.caption(engine.parse_metadata(row))
                    with st.expander("Details"): st.write(row['description'])
                with col_a:
                    if mode == "Spells":
                        if lvl == 0:
                            st.button("Cast", key=f"c_load_{idx}")
                        else:
                            st.button(f"Cast Lvl {lvl}", key=f"c_load_{idx}", on_click=cast_spell_cb, args=(lvl,))
                    else:
                        st.button("Use Dice", key=f"d_load_{idx}", on_click=use_dice_cb)

                    if st.button("Remove", key=f"r_load_{idx}"):
                        engine.remove_from_loadout(orig_idx)
                        st.rerun()