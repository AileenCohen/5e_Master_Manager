import pandas as pd
import json
import re


class AbilityManager:
    def __init__(self):
        self.library = pd.DataFrame()
        self.loadout = pd.DataFrame()
        self.resources = {"Slots": {f"lvl_{i}": 0 for i in range(1, 10)}, "Dice": 4}
        self.current_file_name = ""

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
        """Extracts Range, Time, and Duration into a readable string."""
        lvl = row.get('level', 0)
        lvl_str = "Cantrip" if lvl == 0 else f"Level {lvl}"

        # Check if it's a spell structure (has 'time' or 'range' as objects)
        if not isinstance(row.get('time'), list) and not isinstance(row.get('range'), dict):
            return f"⚔️ {lvl_str} Maneuver"

        meta = [f"✨ {lvl_str}"]
        try:
            if 'time' in row and isinstance(row['time'], list) and len(row['time']) > 0:
                t = row['time'][0]
                meta.append(f"⏳ {t.get('number')} {t.get('unit')}")

            if 'range' in row and isinstance(row['range'], dict):
                dist = row['range'].get('distance', {})
                meta.append(f"🎯 {dist.get('amount', dist.get('type', 'Self'))} {dist.get('unit', '')}")
        except Exception:
            return f"⚔️ {lvl_str} Custom Ability"

        return " | ".join(meta)

    def load_file(self, uploaded_file):
        if self.current_file_name == uploaded_file.name and not self.library.empty:
            return self.library

        data = json.load(uploaded_file)
        raw_list = data.get('spell', data) if isinstance(data, dict) else data
        df = pd.DataFrame(raw_list)
        df.columns = [str(c).lower().strip() for c in df.columns]

        if 'name' not in df.columns: df['name'] = df.iloc[:, 0]
        if 'level' in df.columns:
            df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(0).astype(int)
        else:
            df['level'] = 0

        desc_col = next((c for c in ['entries', 'description', 'desc', 'text'] if c in df.columns), None)
        df['description'] = df[desc_col].apply(self.flatten_entries) if desc_col else "No description."

        self.library = df
        self.current_file_name = uploaded_file.name
        return self.library

    def add_to_loadout(self, row):
        if self.loadout.empty or row['name'] not in self.loadout['name'].values:
            self.loadout = pd.concat([self.loadout, pd.DataFrame([row])], ignore_index=True)

    def remove_from_loadout(self, index):
        self.loadout = self.loadout.drop(index).reset_index(drop=True)