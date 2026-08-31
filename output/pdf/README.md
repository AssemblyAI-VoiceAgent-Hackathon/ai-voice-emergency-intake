# Team PDF update convention

Current Discord review document: `AI_Emergency_Intake_Team_Workflow_Roles.pdf`.

- Keep the stable filename and the original landscape layout, role colours, swimlanes, section order and step references.
- Update the relevant parts in place. Mark changes by version/date and explain what changed from the previous shared version.
- Add a clearly labelled continuation page only when needed; do not replace the established document with a differently structured report.
- Keep the team document in English. Do not include private guidance, personal coaching or a Malay guide for Fazwan.
- Separate the team's current direction from proposals and decisions awaiting confirmation. Do not infer implementation completion.
- Preserve prior versions in `archive/`; do not share the superseded nine-page alignment report.

Current revision: v2, 31 August 2026. The original four pages are retained with targeted SSE/handoff edits, followed by one team-status and next-actions page.

The builder at `scripts/update_team_workflow_pdf.py` uses the archived 30 August baseline and writes a QA candidate under `tmp/pdfs/`. Render and visually inspect before replacing the current PDF.
