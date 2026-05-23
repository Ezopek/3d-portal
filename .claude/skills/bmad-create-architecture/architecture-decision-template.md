---
stepsCompleted: []
inputDocuments: []
workflowType: 'architecture'
project_name: '{{project_name}}'
user_name: '{{user_name}}'
date: '{{date}}'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Authoring guidance — required sections per Decision class

### Schema migrations with dual-field / dual-path shapes

**🚨 MANDATORY (TB-024 codification, 3d-portal Init 10 retro):** every Decision involving a schema migration that introduces a NEW field alongside an existing LEGACY field (e.g. `body → body + body_pl + body_en`, `id → uuid + legacy_id`, `tag → tag + tag_alias`) MUST enumerate the **read-path × write-path × {legacy, new} matrix** in the Decision body — minimum 4 path combinations:

| | Legacy field | New field |
|---|---|---|
| **Read path** | What happens when reading a row that ONLY has the legacy field populated? (Pre-migration data, migration in progress, fallback semantics.) | What happens when reading a row that ONLY has the new field? (Post-migration data, agent ingest, future shape.) |
| **Write path** | What happens when an admin / agent writes to the legacy field? (Backwards-compatibility — does it mirror to the new field? Reject?) | What happens when an admin / agent writes to the new field? (Forward shape — does it back-mirror to legacy? Replace?) |

Cell-by-cell rationale required: state the rule + the WHY. Example for `body → body_pl + body_en` (Init 10 Decision L):

| | Legacy `body` | New `body_pl` / `body_en` |
|---|---|---|
| **Read path** | Frontend DescriptionPanel locale-aware fallback chain: `body_pl OR body OR body_en`. WHY: pre-Init-10 catalog has body as ambiguous-language content (sometimes PL, sometimes EN, no marker); rendering depends on i18n locale. | Backend ShareModelView projection returns BOTH `notes_en` + `notes_pl` so the SPA can pick without a second roundtrip. WHY: client knows current locale; backend doesn't. |
| **Write path** | EditDescriptionSheet posts `body_pl + body_en`; backend mirrors `body = body_en OR body_pl` on save. WHY: preserve legacy-edit semantics until UI fully migrated. Don't seed `body_en` from `body` on save — pre-migration body is ambiguous-language. | Bilingual editor in EditDescriptionSheet writes `body_pl` and `body_en` directly. Backend mirror logic (above) keeps `body` populated for any consumers that haven't migrated. WHY: explicit > implicit; the bilingual fields are the canonical state going forward. |

Under-specified matrices cause Codex P1 catches mid-implementation. The cost of the 4-cell enumeration upfront is ~10 minutes; the cost of round-2 fix-ups for mirror-logic gaps is multiple commits + operator surface time.

Skip this gate ONLY when the migration is a pure rename (no semantic shift between legacy and new field) — in which case the Decision body should state that explicitly.

---
