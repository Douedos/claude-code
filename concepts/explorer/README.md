# Concept Atlas — dictionary explorer

Interactive dependency-graph viewer for the concept dictionary (DICT-00..21).

- `build_graph.py` — parses `../DICT-*.md` into `graph.json` (concepts + dependency
  edges; heuristic extraction from formulas plus a curated edge list for composites).
- `app_template.html` — the self-contained viewer app; `/*__GRAPH__*/` is the
  injection point for the JSON.
- `index.html` — generated artifact: template with graph.json inlined.

Rebuild after editing dictionary files:

    python3 build_graph.py
    python3 -c "import json,pathlib; d=pathlib.Path('.'); \
      (d/'index.html').write_text((d/'app_template.html').read_text().replace('/*__GRAPH__*/', \
      json.dumps(json.load(open(d/'graph.json')), separators=(',',':'))))"

Open `index.html` in any browser. Nodes are concepts (size = degree, color = tier);
edges point from a concept to its inputs; selecting a node highlights its full
lineage (transitive inputs and dependents) and the side panel gives definition,
formula, and clickable neighbors for traversal.
