"""
Style File Version Tracker
===========================
Manages the full per-field version history across all meetings for an order.

Every time a meeting extraction runs, this module merges the new values into
the master style file and records WHAT changed, WHEN it changed, and FROM
WHICH meeting — so you can always answer:

  "What did we agree about pile height in meeting 2?"
  "Has the ex-factory date shifted since opening meeting?"
  "Which fields are still open after 3 meetings?"

Storage format (JSON)
---------------------
{
  "style_number": "DEMO-RUG-2026-004",
  "meetings": [
    { "meeting_number": 1, "date": "2026-11-03", "extracted_at": "..." }
  ],
  "fields": {
    "kpsi": {
      "current_value":      100,
      "current_confidence": "heard",
      "history": [
        {
          "meeting_number": 1,
          "meeting_date":   "2026-11-03",
          "value":          100,
          "confidence":     "heard",
          "note":           ""
        }
      ]
    },
    "pile_height_mm": {
      "current_value":      9.0,
      "current_confidence": "heard",
      "history": [
        { "meeting_number": 1, ..., "value": 9.0,  "note": "Draft — buyer to confirm." },
        { "meeting_number": 2, ..., "value": 10.0, "note": "Confirmed 10 mm in this call." }
      ]
    }
  }
}

Usage
-----
    # Initialise a new style file from the first meeting's extraction
    tracker = VersionTracker('DEMO-RUG-2026-004')
    tracker.apply_extraction('v1_extraction.json', meeting_date='2026-11-03')
    tracker.save('DEMO-RUG-2026-004_style_file.json')

    # Apply the second meeting
    tracker = VersionTracker.load('DEMO-RUG-2026-004_style_file.json')
    tracker.apply_extraction('v2_extraction.json', meeting_date='2026-11-10')
    tracker.save('DEMO-RUG-2026-004_style_file.json')

    # Query history for a field
    tracker.field_history('pile_height_mm')
"""

import json
from datetime import datetime, date
from pathlib import Path


class VersionTracker:

    def __init__(self, style_number: str):
        self.style_number = style_number
        self.meetings: list[dict] = []
        self.fields:   dict[str, dict] = {}

    # ── Load / save ──────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str) -> 'VersionTracker':
        data    = json.loads(Path(path).read_text())
        tracker = cls(data['style_number'])
        tracker.meetings = data.get('meetings', [])
        tracker.fields   = data.get('fields', {})
        return tracker

    def save(self, path: str) -> None:
        data = {
            'style_number': self.style_number,
            'meetings':     self.meetings,
            'fields':       self.fields,
        }
        Path(path).write_text(json.dumps(data, indent=2, default=str))
        print(f"Style file saved → {path}")

    # ── Apply a meeting extraction ────────────────────────────────────────────

    def apply_extraction(self, extraction_path: str, meeting_date: str) -> list[str]:
        """
        Merge a meeting extraction JSON into the master style file.
        Returns a list of field keys that changed.
        """
        extraction    = json.loads(Path(extraction_path).read_text())
        meeting_num   = extraction['meeting_number']
        extracted_at  = extraction.get('extracted_at', datetime.utcnow().isoformat())

        self.meetings.append({
            'meeting_number': meeting_num,
            'date':           meeting_date,
            'extracted_at':   extracted_at,
        })

        changed_fields: list[str] = []

        for key, entry in extraction.get('fields', {}).items():
            new_value      = entry.get('value')
            new_confidence = entry.get('confidence', 'open')
            new_note       = entry.get('note', '')

            if key not in self.fields:
                # First time we've seen this field
                self.fields[key] = {
                    'current_value':      new_value,
                    'current_confidence': new_confidence,
                    'history': [],
                }

            field = self.fields[key]

            # Only record a history entry if the value actually changed
            # (or this is the first meeting)
            prev_value = field['current_value']
            if new_value != prev_value or len(field['history']) == 0:
                field['history'].append({
                    'meeting_number': meeting_num,
                    'meeting_date':   meeting_date,
                    'value':          new_value,
                    'confidence':     new_confidence,
                    'note':           new_note,
                })
                if new_value is not None or len(field['history']) == 1:
                    field['current_value']      = new_value
                    field['current_confidence'] = new_confidence
                if new_value != prev_value and len(field['history']) > 1:
                    changed_fields.append(key)

        return changed_fields

    # ── Query helpers ─────────────────────────────────────────────────────────

    def field_history(self, key: str) -> list[dict]:
        """Return the full change history for a single field."""
        field = self.fields.get(key)
        if not field:
            return []
        return field['history']

    def open_fields(self) -> list[str]:
        """Return field keys where current_value is still None."""
        return [k for k, v in self.fields.items() if v['current_value'] is None]

    def changed_in_meeting(self, meeting_number: int) -> dict[str, dict]:
        """Return all fields that changed in a specific meeting."""
        result = {}
        for key, field in self.fields.items():
            for entry in field['history']:
                if entry['meeting_number'] == meeting_number:
                    result[key] = entry
        return result

    def print_status(self) -> None:
        """Print a summary of the current style file state."""
        from schema import FIELD_MAP, FIELDS
        CONF_ICON = {'heard': '✅', 'inferred': '🔶', 'open': '⬜'}

        print(f"\n{'='*65}")
        print(f"  STYLE FILE STATUS — {self.style_number}")
        print(f"  Meetings applied: {len(self.meetings)}")
        print(f"{'='*65}\n")

        sections: dict[str, list] = {}
        for f in FIELDS:
            fd    = FIELD_MAP.get(f.key)
            entry = self.fields.get(f.key, {'current_value': None, 'current_confidence': 'open'})
            sections.setdefault(f.section, []).append((f.key, entry, fd))

        for section, entries in sections.items():
            print(f"  ── {section} ──")
            for key, entry, fd in entries:
                label      = fd.label if fd else key
                value      = entry.get('current_value')
                confidence = entry.get('current_confidence', 'open')
                history    = entry.get('history', [])
                icon       = CONF_ICON.get(confidence, '⬜')
                val_str    = str(value) if value is not None else '—'
                revisions  = f"  ({len(history)} revision{'s' if len(history)!=1 else ''})" if len(history) > 1 else ''
                print(f"    {icon}  {label:<30} {val_str}{revisions}")
            print()

        open_f = self.open_fields()
        if open_f:
            print(f"  ⬜ {len(open_f)} open field(s) remaining:")
            for k in open_f:
                fd = FIELD_MAP.get(k)
                lbl = fd.label if fd else k
                print(f"     • {lbl}")
        else:
            print("  ✅ All fields filled — ready for production review.")
        print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 4:
        print("Usage: python version_tracker.py <style_number> <extraction.json> <meeting_date>")
        print("       python version_tracker.py <style_number> <extraction.json> <meeting_date> --load <existing_style_file.json>")
        sys.exit(1)

    style_num       = sys.argv[1]
    extraction_path = sys.argv[2]
    meeting_date    = sys.argv[3]
    load_path       = None

    if '--load' in sys.argv:
        idx       = sys.argv.index('--load')
        load_path = sys.argv[idx + 1]

    if load_path and Path(load_path).exists():
        tracker = VersionTracker.load(load_path)
    else:
        tracker = VersionTracker(style_num)

    changed = tracker.apply_extraction(extraction_path, meeting_date)

    if changed:
        print(f"\n{len(changed)} field(s) updated: {', '.join(changed)}")

    tracker.print_status()

    out = f"{style_num}_style_file.json"
    tracker.save(out)
