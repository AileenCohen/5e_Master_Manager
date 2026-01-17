import pandas as pd
import json
import re
import random

class AbilityManager:
    def __init__(self):
        self.library = pd.DataFrame()
        self.known = pd.DataFrame()  # Permanent "Collection"
        self.loadout = pd.DataFrame() # Active "Daily" list
        self.resources = {"Slots": {f"lvl_{i}": 0 for i in range(1, 10)}, "Dice": 4}
        self.current_file_names = []
        
        # --- CHARACTER CORE ---
        self.roll_history = []
        self.stats = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
        self.hp = {"current": 10, "max": 10, "temp": 0}
        self.level = 1
        self.ac = 10
        self.proficiencies = [] 

    def get_mod(self, score):
        return (score - 10) // 2

    def get_prof_bonus(self):
        return (self.level - 1) // 4 + 2

    def update_hp(self, amount):
        new_hp = self.hp["current"] + amount
        self.hp["current"] = max(0, min(new_hp, self.hp["max"]))

    def roll_dice(self, sides, amount, modifier=0):
        rolls = [random.randint(1, sides) for _ in range(amount)]
        total = sum(rolls) + modifier
        mod_str = f"{'+' if modifier >= 0 else ''}{modifier}"
        entry = {
            "time": pd.Timestamp.now().strftime("%H:%M:%S"),
            "formula": f"{amount}d{sides}{mod_str}",
            "result": total,
            "details": f"{rolls} {mod_str}"
        }
        self.roll_history.insert(0, entry)
        if len(self.roll_history) > 20: self.roll_history.pop()
        return rolls, total

    def flatten_entries(self, entry):
        if isinstance(entry, str): 
            return re.sub(r'\{@\w+ ([^|}]*)[^}]*\}', r'\1', entry)
        if isinstance(entry, list): 
            return "\n".join([self.flatten_entries(e) for e in entry])
        if isinstance(entry, dict):
            for key in ['entries', 'text', 'items']:
                if key in entry: return self.flatten_entries(entry[key])
        return str(entry)

    def parse_metadata(self, row):
        lvl = row.get('level', 0)
        lvl_str = "Cantrip" if lvl == 0 else f"Level {lvl}"
        if row.get('type') == 'Maneuver': return f"⚔️ {lvl_str} Maneuver"
        meta = [f"✨ {lvl_str}"]
        try:
            time = row.get('time_text') or (row.get('time')[0].get('unit') if isinstance(row.get('time'), list) else None)
            if time: meta.append(f"⏳ {time}")
            rng = row.get('range_text') or (row.get('range', {}).get('distance', {}).get('type') if isinstance(row.get('range'), dict) else None)
            if rng: meta.append(f"🎯 {rng}")
            if row.get('duration_text'): meta.append(f"⏱️ {row['duration_text']}")
        except: return f"✨ {lvl_str} Ability"
        return " | ".join(meta)

    def load_file(self, uploaded_file):
        if uploaded_file.name in self.current_file_names: return
        data = json.load(uploaded_file)
        raw_list = data.get('spell', data) if isinstance(data, dict) else data
        df = pd.DataFrame(raw_list)
        df.columns = [str(c).lower().strip() for c in df.columns]
        df['source_file'] = uploaded_file.name
        if 'name' not in df.columns: df['name'] = "Unnamed"
        df['level'] = pd.to_numeric(df.get('level', 0), errors='coerce').fillna(0).astype(int)
        desc_col = next((c for c in ['entries', 'description', 'desc', 'text'] if c in df.columns), None)
        df['description'] = df[desc_col].apply(self.flatten_entries) if desc_col else "No description."
        self.library = pd.concat([self.library, df], ignore_index=True).drop_duplicates(subset=['name']).reset_index(drop=True)
        self.current_file_names.append(uploaded_file.name)

    def learn_spell(self, row):
        if self.known.empty or row['name'] not in self.known['name'].values:
            self.known = pd.concat([self.known, pd.DataFrame([row])], ignore_index=True).reset_index(drop=True)

    def unlearn_spell(self, index):
        self.known = self.known.drop(index).reset_index(drop=True)

    def add_to_loadout(self, row):
        if self.loadout.empty or row['name'] not in self.loadout['name'].values:
            self.loadout = pd.concat([self.loadout, pd.DataFrame([row])], ignore_index=True).reset_index(drop=True)

    def remove_from_loadout(self, index):
        self.loadout = self.loadout.drop(index).reset_index(drop=True)

    def add_custom_spell(self, name, level, t_text, r_text, duration, desc):
        new_spell = {'name': name, 'level': int(level), 'description': desc, 'type': 'Spell', 'time_text': t_text, 'range_text': r_text, 'duration_text': duration, 'source_file': 'Custom'}
        self.library = pd.concat([self.library, pd.DataFrame([new_spell])], ignore_index=True).reset_index(drop=True)

    def add_custom_maneuver(self, name, level, resource, add_info, desc):
        new_man = {'name': name, 'level': int(level), 'description': f"{desc}\n\n**Additional Info:** {add_info}", 'type': 'Maneuver', 'resource_cost': resource, 'source_file': 'Custom'}
        self.library = pd.concat([self.library, pd.DataFrame([new_man])], ignore_index=True).reset_index(drop=True)