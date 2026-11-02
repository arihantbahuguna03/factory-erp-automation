# Factory ERP Automation + Meeting-to-Style-File Pipeline

> Two interconnected systems built on top of a client's existing legacy ERP
> (Microsoft SQL Server 2019) — without replacing it, retraining staff, or
> disrupting what was already working.

---

## The Problem

A hand-knotted carpet and rug manufacturer had a custom ERP with ~1,400 tables.
The data wasn't reaching it.

Three gaps were confirmed via database forensics on live data:

| Gap | Finding |
|---|---|
| **BOM module** | All 8 BOM tables had zero rows — module never used |
| **Raw material issuance** | `DEPARTMENTRAWISSUEMASTER` and `DEPARTMENTRAWISSUETRAN` had zero rows — ever. 500–700 daily issuance entries were written on paper only |
| **Dead stock** | Yarn bought for old orders sat unused for 6–8 months; no system visibility, so it was re-ordered |

The ERP's inventory numbers were disconnected from the factory floor. Stock
moved only through purchase-receiving and gate-out — never through proper
department issuance.

The owner's ask: *"Before I place my next purchase order, tell me what I
already have and whether I should buy more."*

---

## What We Built

### Build 1 — ERP Automation (3 modules)

An automation layer that writes into the existing ERP through its own stored
procedures — never via raw table inserts (the ERP has no foreign keys; all
integrity lives in the stored procedures).

```
Structured input (form / Excel)
         │
         ▼
   Python + Claude API
   (calculation + anomaly detection)
         │
         ▼
   Staging + human approval
         │
         ▼
   SQL Server stored procedures
   (PROCESSCONSUMPTIONMASTER, DEPARTMENTRAWISSUEMASTER, etc.)
         │
         ▼
   ERP auto-cascades to STOCK, STOCKTRAN, GatePass
```

**Module 1 — BOM (Bill of Materials)**
- Team enters GSM/consumption via structured form
- Python replicates the ERP's own math: consumption-per-piece × qty across all sizes
- Claude API checks each article's GSM against expected ranges, flags anomalies
- Manager reviews only flagged items (target: 1 hour → ~5 minutes)
- On approval: writes to `PROCESSCONSUMPTIONMASTER`, `PROCESSCONSUMPTIONDETAIL`, `ORDER_CONSUMPTION_DETAIL`

**Module 2 — Inventory & Issuance**
- Phase 1: structured issuance entry → staging → approval → ERP write
- Phase 2: photo of the paper register → Claude Vision reads it → department head approves a summary → `PRO_SAVE_DEPARTMENT_RAW_ISSUE` writes to ERP
- Once issuance is logged against BOM: dead stock alerts, actual vs. planned consumption, daily WhatsApp summary

**Module 3 — Master Creation**
- Structured form + approval to create items and categories cleanly
- Prevents the naming inconsistency that was forcing staff to bypass the ERP in favour of ad-hoc Excel

---

### Build 2 — Meeting-to-Style-File Pipeline

Every new carpet order starts with an opening meeting where construction,
materials, colour and timeline are discussed. Currently this information
lives in people's heads and scattered messages.

**The lifecycle:**
```
Week 1  →  Opening meeting  →  Style file v1 created
Week 2  →  Follow-up meeting  →  Style file updated to v2
Week 3+ →  Ongoing  →  v3, v4 … until order closes
```

Every field is tagged: **Heard** (stated clearly in the meeting),
**Inferred** (reasonable extraction), or **Open** (not yet discussed).
Changes between versions are tracked field by field — so you can always
answer "what did we agree last week about pile height?"

```
Meeting recording (Google Meet / Zoom)
         │
         ▼
   Vexa (self-hosted transcription bot)
   Handles English, Hindi, Hinglish
         │
         ▼
   Claude API
   Extracts structured fields, tags confidence
         │
         ▼
   n8n orchestration
         │
         ├──► Version diff (what changed vs last meeting)
         │
         ├──► Human review (flagged / inferred fields only)
         │
         └──► Google Sheets style file (updated version)
```

**Why Vexa (self-hosted)?**
Cloud transcription services receive raw meeting audio. For a manufacturer
discussing unreleased designs and buyer relationships, that's a data-security
risk. Self-hosted keeps the audio on the client's own infrastructure.

**Why n8n?**
No-code orchestration that connects transcription → LLM → Sheets → approval
flow without maintaining a custom Python service for each step.

**Why stored procedures — never raw inserts?**
The legacy ERP has zero foreign keys across its module tables. All data
integrity logic lives in the stored procedures. Bypassing them (direct INSERT)
would silently corrupt stock and cascading records.

---

## Repository Structure

```
factory-erp-automation/
├── sql/
│   ├── 01_bom_module_gap_analysis.sql       — confirm BOM module is unused
│   ├── 02_issuance_gap_analysis.sql         — confirm issuance gap
│   └── 03_dynamic_date_column_scanner.sql   — find active date columns across 997-col tables
│
├── bom/
│   ├── bom_calculator.py    — working BOM calculator (reads input, outputs consumption + dead stock flag)
│   ├── sample_input.json    — example order input
│   └── README.md
│
└── style_file/
    ├── schema.py            — field definitions for carpet/rug style file
    ├── extractor.py         — Claude API extraction from meeting transcript
    ├── version_tracker.py   — per-field version history across meetings
    ├── sample_transcript.txt — demo transcript (English/Hindi mix)
    └── README.md
```

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| ERP write path | SQL Server stored procedures | Data integrity lives in the procs — never raw inserts |
| BOM validation | Python + Claude API | Flags GSM anomalies before the manager sees them |
| Issuance OCR | Claude Vision API | Reads handwritten paper registers |
| Meeting transcription | Vexa (self-hosted) | Data security — audio stays on client infrastructure |
| LLM field extraction | Claude API | Structured JSON output with confidence tagging |
| Orchestration | n8n | No-code, handles the Sheets + approval flow |
| Style file output | Google Sheets API | Already in the team's workflow — no new tool |

---

## Status

Database forensics complete. All gaps confirmed with live data. Build plan
and pricing prepared. Client login to the ERP front-end pending for final
table mapping.

---

*All company names, buyer names, and identifying details have been
anonymised. SQL queries run against a Microsoft SQL Server 2019 instance
(the client's legacy ERP). Sample data is illustrative.*
