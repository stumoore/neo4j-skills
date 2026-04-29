# Neo4j Data Importer GUI

## When to Use

| Condition | Use Data Importer |
|---|---|
| Dataset < 1M rows | YES |
| No Cypher knowledge | YES |
| Need visual model + import in one step | YES |
| Aura (no file:/// access) | YES — upload local CSVs |
| Need list/array properties on import | NO — strings only; post-process after |
| > 1M rows | NO — use LOAD CSV + CALL IN TRANSACTIONS |
| Need custom type coercion during load | NO — post-process after |

## Access in Aura

1. Log in: `console.neo4j.io`
2. Open AuraDB instance
3. Click **Import** in left sidebar — Data Importer opens pre-connected

Standalone URL (any Neo4j version): `https://data-importer.neo4j.io/versions/0.7.0/?acceptTerms=true`
Provide WebSocket Bolt URL + password to connect.

## Requirements

- CSV files on local filesystem (drag-and-drop into Files pane)
- CSV must have headers
- CSV must be clean (no encoding errors, consistent delimiters)
- IDs must be unique per node type
- DBMS must be running

## Import Steps

1. Upload CSV(s) to Files pane (drag or Browse)
2. Click **Add node label** — enter label, select CSV file, map columns
3. Set unique ID (key icon) — Data Importer auto-creates uniqueness constraint + index
4. Drag edge between nodes to create relationship — select type, CSV file, from/to ID columns
5. Add optional relationship properties
6. Click **Run import**
7. View summary; verify in Query tool

## Data Types Supported

Data Importer stores: `String`, `Integer` (Long), `Float` (Double), `Boolean`, `Datetime`.

Lists/arrays NOT supported — stored as delimited strings. Post-process with `split()`.

## What Data Importer Creates Automatically

- Uniqueness constraint on each node's unique ID property
- Index for each constrained property
- `MERGE` semantics on re-import (no duplicates if re-run)

## Multi-pass for De-normalized Data

De-normalized CSV (one row = person + movie + role) requires multiple passes:
- Cannot create multiple node types from one file in single pass via GUI
- Pass 1: Map CSV → Person nodes; import
- Pass 2: Map same CSV → Movie nodes; import
- Pass 3: Map same CSV → ACTED_IN relationships; import

## Model Save / Export

- Save model: give it a name, click **Save** (auto-saved on change)
- Export: `...` menu → **Download model (with data)** — ZIP with mappings + CSVs
- Restore: `...` menu → **Open model (with data)**

## Common Mistakes

**No unique ID set**
Consequence: duplicate nodes on re-import; relationship creation fails.
Fix: always set key icon on ID column before running.

**Foreign key kept as property**
Example: keeping `order_id` as property on Customer node instead of creating relationship.
Fix: foreign keys → relationships, not properties.

**Type mismatch (silent failure)**
If Data Importer cannot convert a source value to the specified type (e.g., text in Integer column), import succeeds but that property is silently omitted on affected nodes.
Fix: verify node counts + spot-check properties after import; use string import + Cypher coercion if needed.

**All data imports as strings**
Fix: set correct type per column in mapping panel; or post-process with `toInteger()`, `date()`, `split()`.

**Importing before constraint creation**
Data Importer creates constraints automatically — this is fine for the GUI path.
For Cypher path: create constraints manually BEFORE import.
