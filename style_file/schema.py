"""
Style File Schema — Carpet / Rug Orders
========================================
Defines every field in a carpet/rug style file, grouped by section.
Each field has:
  - key          : machine-readable identifier
  - label        : human-readable name (shown in the style file)
  - section      : which sheet/tab it belongs to
  - required     : whether the field must be filled before production starts
  - data_type    : str | float | int | date | list
  - hint         : what the LLM should look for in the transcript

This schema drives both the extraction prompt (extractor.py) and the
version tracker (version_tracker.py).
"""

from dataclasses import dataclass, field
from typing import Literal

DataType = Literal['str', 'float', 'int', 'date', 'list']
Section  = Literal[
    'Style Summary',
    'Tech Specs',
    'CAD & Sizes',
    'BOM',
    'Colour Master',
    'Packing & Logistics',
    'Quality & T&A',
]


@dataclass
class FieldDef:
    key:       str
    label:     str
    section:   Section
    required:  bool
    data_type: DataType
    hint:      str


# ── Field definitions ────────────────────────────────────────────────────────

FIELDS: list[FieldDef] = [

    # ── Style Summary ────────────────────────────────────────────────────────
    FieldDef('style_number',       'Style number',           'Style Summary', True,  'str',
             'Buyer article number, style code or order reference mentioned in the meeting.'),
    FieldDef('style_name',         'Style name',             'Style Summary', False, 'str',
             'Descriptive name for the design (e.g. "Diamond runner", "Floral 9x12").'),
    FieldDef('buyer_name',         'Buyer name',             'Style Summary', True,  'str',
             'Name of the international buyer or brand placing the order.'),
    FieldDef('season',             'Season',                 'Style Summary', False, 'str',
             'Collection season (e.g. "Spring/Summer 2027", "AW26").'),
    FieldDef('order_quantity',     'Order quantity (pcs)',   'Style Summary', True,  'int',
             'Total number of pieces across all sizes.'),
    FieldDef('sizes',              'Sizes',                  'Style Summary', True,  'list',
             'Size breakdown — foot dimensions (e.g. 5x8, 8x10, 9x12) and qty per size if mentioned.'),
    FieldDef('colourway',          'Colourway',              'Style Summary', True,  'str',
             'Colour combination for this order (e.g. "Ivory/Charcoal", "Navy/Gold").'),
    FieldDef('ex_factory_date',    'Ex-factory date',        'Style Summary', True,  'date',
             'Date goods must leave the factory.'),

    # ── Tech Specs ───────────────────────────────────────────────────────────
    FieldDef('construction_type',  'Construction type',      'Tech Specs',    True,  'str',
             'Hand-knotted, hand-tufted, flatweave, etc.'),
    FieldDef('knot_type',          'Knot type',              'Tech Specs',    False, 'str',
             'Persian (Senneh) knot or Turkish (Ghiordes) knot.'),
    FieldDef('kpsi',               'Knots per sq. inch',     'Tech Specs',    True,  'int',
             'KPSI — knot density. Usually 60–200 for commercial hand-knotted.'),
    FieldDef('pile_type',          'Pile type',              'Tech Specs',    True,  'str',
             'Cut pile, loop pile, cut-and-loop, flatweave.'),
    FieldDef('pile_height_mm',     'Pile height (mm)',       'Tech Specs',    True,  'float',
             'Finished pile height in mm after shearing.'),
    FieldDef('face_weight_gsm',    'Face weight (g/m²)',     'Tech Specs',    True,  'float',
             'Pile yarn weight per square metre — sometimes called GSM.'),
    FieldDef('pile_yarn',          'Pile yarn',              'Tech Specs',    True,  'str',
             'Fibre content, ply, count and twist of the pile yarn (e.g. "100% NZ wool, 2-ply, Nm6, S twist").'),
    FieldDef('warp_material',      'Warp material',          'Tech Specs',    False, 'str',
             'Warp yarn (e.g. "Cotton 3-ply").'),
    FieldDef('edge_finish',        'Edge finish',            'Tech Specs',    False, 'str',
             'How the rug edges are finished (overcast binding, serging, etc.) and width in mm.'),
    FieldDef('fringe',             'Fringe',                 'Tech Specs',    False, 'str',
             'Fringe style and length, or "none".'),

    # ── BOM ──────────────────────────────────────────────────────────────────
    FieldDef('wool_grade',         'Wool grade(s)',           'BOM',           True,  'str',
             'Which wool grade(s) will be used — important for stock allocation.'),
    FieldDef('wool_kg_per_sqm',    'Wool consumption (kg/m²)', 'BOM',         True,  'float',
             'Pile yarn kg per square metre of finished carpet.'),
    FieldDef('wool_wastage_pct',   'Wool wastage %',          'BOM',          False, 'float',
             'Expected cutting/knot wastage as a percentage (e.g. 0.08 = 8%).'),
    FieldDef('warp_kg_per_sqm',    'Warp consumption (kg/m²)', 'BOM',         False, 'float',
             'Cotton warp kg per square metre.'),

    # ── Colour Master ────────────────────────────────────────────────────────
    FieldDef('pantone_references', 'Pantone references',     'Colour Master', False, 'list',
             'Pantone TCX codes for each colour in the colourway.'),
    FieldDef('delta_e_limit',      'Delta E limit',          'Colour Master', False, 'float',
             'Acceptable colour deviation from reference (usually ≤1.0).'),
    FieldDef('light_source',       'Light source',           'Colour Master', False, 'str',
             'Metamerism check light source (D65, TL84, A, etc.).'),
    FieldDef('fastness_requirements', 'Fastness requirements', 'Colour Master', False, 'str',
             'Crocking, wash and light fastness grades required.'),

    # ── Packing & Logistics ──────────────────────────────────────────────────
    FieldDef('rolling_direction',  'Rolling direction',      'Packing & Logistics', False, 'str',
             'Face in or face out.'),
    FieldDef('packing_type',       'Packing type',           'Packing & Logistics', False, 'str',
             'Shrink wrap, polybag, bale, carton — as specified by buyer.'),
    FieldDef('pieces_per_bale',    'Pieces per bale',        'Packing & Logistics', False, 'int',
             'How many pieces per shipping bale.'),
    FieldDef('port_of_loading',    'Port of loading',        'Packing & Logistics', False, 'str',
             'Departure port.'),
    FieldDef('port_of_discharge',  'Port of discharge',      'Packing & Logistics', False, 'str',
             'Destination port.'),

    # ── Quality & T&A ────────────────────────────────────────────────────────
    FieldDef('aql_level',          'AQL level',              'Quality & T&A', False, 'str',
             'Acceptable Quality Level for final inspection (e.g. AQL 1.5, AQL 2.5).'),
    FieldDef('pp_sample_deadline', 'PP sample deadline',     'Quality & T&A', False, 'date',
             'Date by which the pre-production sample must be approved.'),
    FieldDef('weaving_start',      'Weaving start',          'Quality & T&A', False, 'date',
             'Planned weaving start date.'),
    FieldDef('final_inspection',   'Final inspection date',  'Quality & T&A', False, 'date',
             'Planned final inspection date.'),
    FieldDef('certification',      'Certification requirements', 'Quality & T&A', False, 'str',
             'GRS, RWS, OEKO-TEX, or other certification requirements mentioned.'),
]

# Lookup by key
FIELD_MAP: dict[str, FieldDef] = {f.key: f for f in FIELDS}

# Required fields — production cannot start without these
REQUIRED_FIELDS: list[FieldDef] = [f for f in FIELDS if f.required]
