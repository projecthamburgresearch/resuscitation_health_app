# Resource Atlas: Resuscitation Health App

## 1. Historical Provenance
1. `appendix/guidance/exit/logs/raw/`
- canonical raw terminal transcripts for continuity and ethos recovery

2. `appendix/guidance/materials/`
- legacy local notes and non-authority materials

## 2. Product Runtime Sources
1. `app/src/`
- primary runtime logic, state machine, styles, automation hooks

2. `app/dev-mode/`
- dev-mode mirror and overlay surface

3. `prototype/`
- schema and flow reference for the decision wheel

## 3. Current-State Authority Sources
1. `appendix/guidance/warden/research/system/`
- constitution, methodology, and product-law surface

2. `appendix/guidance/warden/research/tickets/`
- implementation lineage and current Warden contract

3. `appendix/guidance/warden/report/latest_analysis.md`
- current summary of the Warden evidence surface

4. `appendix/guidance/warden/blueprint_outputs/`, `scans_outputs/`, `design/`, `report/`
- current canonical Warden output roots in this repo

## 4. Future-State Authority Sources
1. `appendix/guidance/headmaster/`
- future-state research, source maps, syllabus, and handoffs

2. `appendix/guidance/switchboard/`
- delegate routing and message history

3. `appendix/guidance/exit/`
- continuity state, prompt generation, and recovery packets

## 5. Integration Sources
1. `integrations/access/`
- local integration-readiness surface generated from the external Toolkit access package

2. `scripts/integrations/run_toolkit_access.js`
- local wrapper for generating project-specific access outputs without copying Toolkit into the repo

## 6. External Corpus (Do Not Mirror Wholesale)
1. `/Users/mordecaimachazire/Documents/local-projects/toolkit/librarian/resources/`
- Toolkit Librarian canonical corpus

2. `/Users/mordecaimachazire/Documents/local-projects/toolkit/packages/`
- reusable capability modules (`access`, `blueprint`, `checker`, `domscan`)

3. `/Users/mordecaimachazire/Documents/local-projects/toolkit/workspace/`
- reusable authority templates (`warden`, `headmaster`, `switchboard`, `exit`)

## 7. Nearby Local Reference Projects
1. `appendix/css-web-ui-demos/`
- nested repo used as a design/reference corpus

2. `prototype/`
- local design/interaction reference already owned by this project

## 8. Documentation and Tooling
1. `docs/`
- high-level architecture documents, implementation plans, and run-mode guides

2. `.specstory/history/`
- AI-assisted session history and tool-driven discovery records

3. `app/algorithms/`
- canonical runtime algorithm JSON files consumed by the state machine

4. `prototype/json-algorithms/`
- upstream design/source algorithm files and schema references

## 9. Selection Rule
Use project-local runtime, Warden evidence, and raw logs first. Use Toolkit Librarian and other nearby corpora second, as supporting reference rather than copy target.
