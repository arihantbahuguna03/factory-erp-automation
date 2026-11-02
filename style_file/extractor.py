"""
Meeting Transcript → Style File Extractor
==========================================
Sends a meeting transcript to the Claude API and extracts structured style
file fields. Every extracted value is tagged with a confidence level:

  heard     — field was stated clearly in the meeting
  inferred  — field was not stated but can be reasonably inferred
  open      — field was not mentioned; human must fill it before production

Usage
-----
    export ANTHROPIC_API_KEY=your_key_here
    python extractor.py sample_transcript.txt
    python extractor.py sample_transcript.txt --meeting-number 2 --prev-version v1_output.json

The --prev-version flag loads the previous style file version so the
extractor only shows CHANGED or newly-filled fields — the diff view.

Output JSON shape
-----------------
{
  "meeting_number": 1,
  "meeting_date":   "2026-11-03",
  "style_number":   "DEMO-RUG-2026-004",
  "fields": {
    "style_number":  { "value": "DEMO-RUG-2026-004", "confidence": "heard",    "note": "" },
    "kpsi":          { "value": 100,                  "confidence": "heard",    "note": "" },
    "pile_height_mm":{ "value": 9.0,                  "confidence": "heard",    "note": "Buyer said '9 mm for now' — confirm before PP sample." },
    "warp_material": { "value": null,                 "confidence": "open",     "note": "Not discussed in this meeting." },
    ...
  }
}
"""

import anthropic
import json
import sys
from datetime import date
from pathlib import Path

from schema import FIELDS, FIELD_MAP


# ── Prompt builder ───────────────────────────────────────────────────────────

def build_extraction_prompt(transcript: str, meeting_number: int) -> str:
    field_lines = '\n'.join(
        f'  - {f.key} ({f.label}): {f.hint}'
        for f in FIELDS
    )

    return f"""You are extracting structured data from a factory order meeting transcript for a hand-knotted carpet/rug manufacturer.

Extract the following fields. For EVERY field, return a JSON object with:
  "value"      : the extracted value (null if not mentioned)
  "confidence" : one of "heard" / "inferred" / "open"
  "note"       : a short note if the value is uncertain, qualified, or inferred

Confidence rules:
  heard    — clearly and explicitly stated in the meeting
  inferred — not stated but can be reasonably concluded from context
  open     — not discussed at all; value must be null

Fields to extract:
{field_lines}

Important:
- For list fields (sizes, pantone_references), return a JSON array.
- For date fields, return ISO format YYYY-MM-DD where possible.
- For float fields, return a number (not a string).
- If a value was stated but qualified ("for now", "to be confirmed", "tentatively"), use confidence "heard" but add a note flagging the qualification.
- Do NOT invent values. If genuinely unknown, set value to null and confidence to "open".

Meeting number: {meeting_number}

Transcript:
{transcript}

Return ONLY valid JSON in this exact shape:
{{
  "meeting_number": {meeting_number},
  "extracted_at": "today",
  "fields": {{
    "<field_key>": {{"value": <value_or_null>, "confidence": "<heard|inferred|open>", "note": "<string>"}},
    ...
  }}
}}"""


# ── Diff against previous version ────────────────────────────────────────────

def compute_diff(current: dict, previous: dict) -> dict:
    """
    Returns only the fields that changed or are newly filled compared to
    the previous version. Used to generate the meeting-to-meeting delta.
    """
    diff = {}
    curr_fields = current.get('fields', {})
    prev_fields = previous.get('fields', {})

    for key, curr in curr_fields.items():
        prev = prev_fields.get(key, {})
        prev_val = prev.get('value')
        curr_val = curr.get('value')

        if curr_val != prev_val:
            diff[key] = {
                'previous': prev_val,
                'current':  curr_val,
                'confidence': curr['confidence'],
                'note':       curr.get('note', ''),
            }
    return diff


# ── Display helpers ───────────────────────────────────────────────────────────

def print_extraction(result: dict, diff: dict | None = None) -> None:
    CONF_ICON = {'heard': '✅', 'inferred': '🔶', 'open': '⬜'}
    fields    = result.get('fields', {})

    print(f"\n{'='*65}")
    print(f"  STYLE FILE EXTRACTION — Meeting {result.get('meeting_number', '?')}")
    print(f"{'='*65}\n")

    sections: dict[str, list] = {}
    for key, entry in fields.items():
        fd = FIELD_MAP.get(key)
        section = fd.section if fd else 'Other'
        sections.setdefault(section, []).append((key, entry, fd))

    for section, entries in sections.items():
        print(f"  ── {section} ──")
        for key, entry, fd in entries:
            label      = fd.label if fd else key
            value      = entry.get('value')
            confidence = entry.get('confidence', 'open')
            note       = entry.get('note', '')
            icon       = CONF_ICON.get(confidence, '  ')
            changed    = diff and key in diff

            val_str = str(value) if value is not None else '—'
            change_marker = ' ◀ CHANGED' if changed else ''
            print(f"    {icon}  {label:<30} {val_str}{change_marker}")
            if note:
                print(f"        └─ {note}")
        print()

    open_fields = [
        FIELD_MAP[k].label for k, e in fields.items()
        if e.get('confidence') == 'open' and k in FIELD_MAP
    ]
    if open_fields:
        print(f"  ⬜ OPEN (needs human input before production):")
        for lbl in open_fields:
            print(f"     • {lbl}")
        print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <transcript.txt> [--meeting-number N] [--prev-version <prev.json>]")
        sys.exit(1)

    transcript_path  = sys.argv[1]
    meeting_number   = 1
    prev_version_path = None

    if '--meeting-number' in sys.argv:
        idx            = sys.argv.index('--meeting-number')
        meeting_number = int(sys.argv[idx + 1])
    if '--prev-version' in sys.argv:
        idx               = sys.argv.index('--prev-version')
        prev_version_path = sys.argv[idx + 1]

    transcript = Path(transcript_path).read_text()
    prompt     = build_extraction_prompt(transcript, meeting_number)

    client = anthropic.Anthropic()
    print(f"\nSending transcript to Claude API (meeting {meeting_number})…")

    message = client.messages.create(
        model      = 'claude-opus-4-5',
        max_tokens = 4096,
        messages   = [{'role': 'user', 'content': prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1]
        raw = raw.rsplit('```', 1)[0]

    result = json.loads(raw)

    # Compute diff if previous version supplied
    diff = None
    if prev_version_path:
        prev = json.loads(Path(prev_version_path).read_text())
        diff = compute_diff(result, prev)
        print(f"\n{len(diff)} field(s) changed since last meeting.")

    print_extraction(result, diff)

    # Save output
    out_path = f"v{meeting_number}_extraction.json"
    Path(out_path).write_text(json.dumps(result, indent=2, default=str))
    print(f"Full extraction saved to: {out_path}")


if __name__ == '__main__':
    main()
