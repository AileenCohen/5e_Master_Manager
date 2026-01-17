import pandas as pd
import json
import re
import random

class AbilityManager:
    def __init__(self):
        self.stats = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
        self.casting_stat = "INT"
        self.hp = {"current": 10, "max": 10}
        self.level = 1
        self.ac = 10
        self.proficiencies = [] # For Skills
        self.save_profs = []    # For Saving Throws
        
        self.library = pd.DataFrame()
        self.known = pd.DataFrame()
        self.loadout = pd.DataFrame()
        self.features = [] 
        self.roll_history = []
        self.current_file_names = []

    def get_mod(self, score):
        return (score - 10) // 2

    def get_prof_bonus(self):
        return (self.level - 1) // 4 + 2

    def get_dc(self):
        return 8 + self.get_prof_bonus() + self.get_mod(self.stats.get(self.casting_stat, 10))

    def get_passive(self, skill_name, stat="WIS"):
        mod = self.get_mod(self.stats.get(stat, 10))
        prof = self.get_prof_bonus() if skill_name in self.proficiencies else 0
        return 10 + mod + prof

    def long_rest(self):
        self.hp["current"] = self.hp["max"]
        return "Long Rest Complete."

    def update_hp(self, amount):
        self.hp["current"] = max(0, min(self.hp["current"] + amount, self.hp["max"]))

    def roll_dice(self, sides, amount, modifier=0):
        rolls = [random.randint(1, sides) for _ in range(amount)]
        total = sum(rolls) + modifier
        entry = {"time": pd.Timestamp.now().strftime("%H:%M:%S"), "formula": f"{amount}d{sides}{modifier:+}", "result": total}
        self.roll_history.insert(0, entry)
        return rolls, total

    def flatten_entries(self, entry):
        if isinstance(entry, str): return re.sub(r'\{@\w+ ([^|}]*)[^}]*\}', r'\1', entry)
        if isinstance(entry, list): return "\n".join([self.flatten_entries(e) for e in entry])
        if isinstance(entry, dict):
            for key in ['entries', 'text', 'items']:
                if key in entry: return self.flatten_entries(entry[key])
        return str(entry)

    def parse_metadata(self, row):
        lvl = row.get('level', 0)
        lvl_str = "Cantrip" if lvl == 0 else f"Lvl {lvl}"
        meta = [f"✨ {lvl_str}"]
        try:
            t_data = row.get('time')
            time = row.get('time_text') or (f"{t_data[0].get('number')} {t_data[0].get('unit')}" if isinstance(t_data, list) else None)
            if time: meta.append(f"⏳ {time}")
            
            rng_data = row.get('range', {})
            dist = rng_data.get('distance', {})
            r_type = str(rng_data.get('type', '')).lower()
            amt, unit = dist.get('amount'), dist.get('type', 'ft')
            
            if row.get('range_text'): range_val = row['range_text']
            elif 'self' in r_type or 'self' in str(dist.get('type','')).lower():
                range_val = f"Self ({amt} {unit} radius)" if amt else "Self"
            elif 'touch' in r_type: range_val = "Touch"
            elif amt: range_val = f"{amt} {unit}"
            else: range_val = r_type.capitalize() if r_type != 'point' else "Special"
            meta.append(f"🎯 {range_val}")
            
            if isinstance(row.get('duration'), list) and row['duration'][0].get('concentration'):
                meta.append("⚠️ Conc.")
        except: meta.append("🎯 Special")
        return " | ".join(meta)

    def load_file(self, uploaded_file):
        data = json.load(uploaded_file)
        raw_list = data.get('spell', data) if isinstance(data, dict) else data
        df = pd.DataFrame(raw_list)
        df.columns = [str(c).lower().strip() for c in df.columns]
        df['level'] = pd.to_numeric(df.get('level', 0), errors='coerce').fillna(0).astype(int)
        desc_col = next((c for c in ['entries', 'description', 'desc', 'text'] if c in df.columns), 'description')
        df['description'] = df[desc_col].apply(self.flatten_entries)
        self.library = pd.concat([self.library, df], ignore_index=True).drop_duplicates(subset=['name']).reset_index(drop=True)

    def learn_ability(self, row):
        if self.known.empty or row['name'] not in self.known['name'].values:
            self.known = pd.concat([self.known, pd.DataFrame([row])], ignore_index=True).reset_index(drop=True)

    def prepare_ability(self, row):
        if self.loadout.empty or row['name'] not in self.loadout['name'].values:
            self.loadout = pd.concat([self.loadout, pd.DataFrame([row])], ignore_index=True).reset_index(drop=True)
