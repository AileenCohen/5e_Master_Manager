# 5e Master Manager

A lightweight, powerful, and structure-aware ability manager for D&D 5e. This tool allows players to upload massive libraries of spells or maneuvers, prepare them into a custom loadout, and track combat resources (Spell Slots and Superiority Dice) in real-time.

---

## Features

* **Smart Parsing:** Automatically handles 5eTools JSON schemas and simple custom maneuver lists.
* **Metadata Extraction:** Automatically unwraps complex JSON to show Casting Time, Range, and Duration.
* **Dual Tracking:** Switch between **Spellcaster Mode** (Level 1-9 slots) and **Martial Mode** (Superiority Dice).
* **Session Bundles:** Export your entire session—including the library, prepared spells, and remaining slots—into a single file to resume later.
* **Advanced Filtering:** Search and filter both the main library and your prepared list by name or level.

---

## Getting Started

### 1. Requirements
You need Python 3.8+ installed. You will also need the following libraries:

```bash
pip install streamlit pandas
```

### 2. Installation
Clone this repository or download the files.

Ensure app.py and engine.py are in the same folder.

Run the application:

```
streamlit run app.py
```
---
## How to Use
### Step 1: Upload a Library
- Upload a .json file containing your spells or maneuvers.

- Spells: Supports the standard 5e JSON format (containing a "spell": [...] key).

- Maneuvers: Supports simple lists of objects. It will automatically detect keywords like Enhanced: to highlight special effects.

### Step 2: Prepare Abilities
Browse the Library tab, use the search and level filters to find your abilities, and click Prepare. They will move to your Active Loadout.

### Step 3: Manage Combat
- Select your mode (Spells or Maneuvers) in the sidebar.
- In the Active Loadout tab, you can view the full details of your prepared abilities.
- Click Cast or Use Dice to subtract resources from your sidebar counters.

### Step 4: Save Your Progress
- Don't lose your work! Use the Export All Data button in the sidebar. This creates a 5e_session_bundle.json which contains:
    - Your entire uploaded Library.
    - Your currently Prepared Abilities.
    - Your remaining Spell Slots and Dice.

To resume, simply upload that bundle into the Import All Data slot.

## Tech Stack
Frontend: Streamlit
Data Processing: Pandas
Logic: Python Class-based Engine

## License
MIT License - feel free to use and modify for your own homebrew games!

