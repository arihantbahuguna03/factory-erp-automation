"""
BOM Calculator — Hand-Knotted Carpet / Rug
==========================================
Reads an order + material spec from a JSON input file, calculates total
raw material consumption per material grade across all sizes, and flags
dead stock that covers the requirement (so the buyer doesn't re-order).

This is the core of the BOM automation module: the same math the ERP
calculates internally, exposed as a standalone script so:
  1. The team can validate figures before writing to the ERP.
  2. The dead-stock check runs before any purchase order is raised.

Usage
-----
    python bom_calculator.py sample_input.json
    python bom_calculator.py sample_input.json --output consumption_report.csv

Input JSON schema
-----------------
See sample_input.json for the full structure.

  order.sizes[]          — size label, width_cm, length_cm, qty
  materials[]            — grade, kg_per_sqm, wastage_pct, stock_on_hand_kg

Output
------
  Console table + optional CSV:
    grade | kg_per_sqm | total_area_sqm | net_kg | gross_kg | stock_on_hand | status
"""

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class Size:
    label:     str
    width_cm:  float
    length_cm: float
    qty:       int

    @property
    def area_sqm(self) -> float:
        return round((self.width_cm / 100) * (self.length_cm / 100), 4)

    @property
    def total_area_sqm(self) -> float:
        return round(self.area_sqm * self.qty, 4)


@dataclass
class Material:
    grade:             str
    description:       str
    kg_per_sqm:        float
    wastage_pct:       float
    stock_on_hand_kg:  float


@dataclass
class ConsumptionLine:
    grade:             str
    description:       str
    kg_per_sqm:        float
    wastage_pct:       float
    total_area_sqm:    float
    net_kg:            float
    gross_kg:          float
    stock_on_hand_kg:  float
    shortfall_kg:      float
    status:            str      # COVERED / PARTIAL / BUY_NEW


# ── Core calculation ─────────────────────────────────────────────────────────

def calculate_total_area(sizes: list[Size]) -> float:
    return round(sum(s.total_area_sqm for s in sizes), 4)


def calculate_consumption(material: Material, total_area_sqm: float) -> ConsumptionLine:
    net_kg   = round(material.kg_per_sqm * total_area_sqm, 3)
    gross_kg = round(net_kg * (1 + material.wastage_pct), 3)

    stock    = material.stock_on_hand_kg
    shortfall = round(max(0.0, gross_kg - stock), 3)

    if stock >= gross_kg:
        status = 'COVERED'        # existing stock covers the full requirement
    elif stock > 0:
        status = 'PARTIAL'        # existing stock covers part — buy the shortfall only
    else:
        status = 'BUY_NEW'        # no stock on hand

    return ConsumptionLine(
        grade            = material.grade,
        description      = material.description,
        kg_per_sqm       = material.kg_per_sqm,
        wastage_pct      = material.wastage_pct,
        total_area_sqm   = total_area_sqm,
        net_kg           = net_kg,
        gross_kg         = gross_kg,
        stock_on_hand_kg = stock,
        shortfall_kg     = shortfall,
        status           = status,
    )


# ── I/O helpers ──────────────────────────────────────────────────────────────

def load_input(path: str) -> tuple[dict, list[Size], list[Material]]:
    with open(path) as f:
        data = json.load(f)

    order     = data['order']
    sizes     = [Size(
                    label     = s['size'],
                    width_cm  = s['width_cm'],
                    length_cm = s['length_cm'],
                    qty       = s['qty'],
                ) for s in order['sizes']]
    materials = [Material(
                    grade            = m['grade'],
                    description      = m['description'],
                    kg_per_sqm       = m['kg_per_sqm'],
                    wastage_pct      = m['wastage_pct'],
                    stock_on_hand_kg = m['stock_on_hand_kg'],
                ) for m in data['materials']]
    return order, sizes, materials


def print_size_summary(order: dict, sizes: list[Size]) -> None:
    print(f"\n{'='*70}")
    print(f"  BOM CALCULATION — {order['style_number']}  ({order['construction']})")
    print(f"{'='*70}")
    print(f"\n{'SIZE':<12} {'WIDTH':>8} {'LENGTH':>8} {'AREA m²':>9} {'QTY':>5} {'TOTAL m²':>10}")
    print('-' * 56)
    total = 0.0
    for s in sizes:
        print(f"{s.label:<12} {s.width_cm:>7}cm {s.length_cm:>7}cm {s.area_sqm:>9.4f} {s.qty:>5} {s.total_area_sqm:>10.4f}")
        total += s.total_area_sqm
    print('-' * 56)
    print(f"{'TOTAL':>45} {round(total, 4):>10.4f} m²\n")


def print_consumption_report(lines: list[ConsumptionLine]) -> None:
    STATUS_ICON = {'COVERED': '✅', 'PARTIAL': '⚠️ ', 'BUY_NEW': '🛒'}
    print(f"\n{'MATERIAL GRADE':<20} {'NET kg':>8} {'GROSS kg':>9} {'STOCK kg':>9} {'SHORTFALL':>10}  STATUS")
    print('-' * 75)
    for ln in lines:
        icon = STATUS_ICON.get(ln.status, '  ')
        print(
            f"{ln.grade:<20} {ln.net_kg:>8.2f} {ln.gross_kg:>9.2f} "
            f"{ln.stock_on_hand_kg:>9.2f} {ln.shortfall_kg:>10.2f}  {icon} {ln.status}"
        )
    print()

    covered  = [l for l in lines if l.status == 'COVERED']
    partial  = [l for l in lines if l.status == 'PARTIAL']
    buy_new  = [l for l in lines if l.status == 'BUY_NEW']

    if covered:
        print("✅ USE EXISTING STOCK (no purchase needed):")
        for ln in covered:
            print(f"   {ln.grade}: {ln.stock_on_hand_kg} kg on hand, need {ln.gross_kg} kg")
    if partial:
        print("⚠️  PARTIAL STOCK (buy only the shortfall):")
        for ln in partial:
            print(f"   {ln.grade}: {ln.stock_on_hand_kg} kg on hand, need {ln.gross_kg} kg — buy {ln.shortfall_kg} kg more")
    if buy_new:
        print("🛒 BUY NEW (no stock on hand):")
        for ln in buy_new:
            print(f"   {ln.grade}: buy {ln.gross_kg} kg")
    print()


def write_csv(lines: list[ConsumptionLine], path: str) -> None:
    fieldnames = [
        'grade', 'description', 'kg_per_sqm', 'wastage_pct',
        'total_area_sqm', 'net_kg', 'gross_kg',
        'stock_on_hand_kg', 'shortfall_kg', 'status',
    ]
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ln in lines:
            writer.writerow({k: getattr(ln, k) for k in fieldnames})
    print(f"CSV written to: {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python bom_calculator.py <input.json> [--output <report.csv>]")
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = None
    if '--output' in sys.argv:
        idx         = sys.argv.index('--output')
        output_path = sys.argv[idx + 1]

    order, sizes, materials = load_input(input_path)
    total_area              = calculate_total_area(sizes)
    lines                   = [calculate_consumption(m, total_area) for m in materials]

    print_size_summary(order, sizes)
    print_consumption_report(lines)

    if output_path:
        write_csv(lines, output_path)


if __name__ == '__main__':
    main()
