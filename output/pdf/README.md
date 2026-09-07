# Team PDF update convention

Current Discord review document: `AI_Emergency_Intake_Team_Workflow_Roles_v4.pdf`.

- Keep the v4 filename and the original landscape layout, role colours, swimlanes, section order and step references.
- Update the relevant parts in place. Mark changes by version/date and explain what changed from the previous shared version.
- Add a clearly labelled continuation page only when needed; do not replace the established document with a differently structured report.
- Keep the team document in English. Do not include private guidance, personal coaching or a Malay guide for Fazwan.
- The current v4 document must retain the confirmed names: Soha Raees, Fazwan Zainuddin, Mozzam Shahid, Ishaan Sama, Jonathan and Mariam Habib.
- Retain page 6, which records how Ishaan Sama's EmergencyVoice tech-stack contribution is incorporated and which choices remain open.
- Publish the current document as `AI_Emergency_Intake_Team_Workflow_Roles_v4.pdf`; preserve earlier or user-edited copies in `archive/`.
- Separate the team's current direction from proposals and decisions awaiting confirmation. Do not infer implementation completion.
- Preserve prior versions in `archive/`; do not share the superseded nine-page alignment report.

Current revision: v4, 3 September 2026. The original four pages are retained with targeted SSE/handoff edits, followed by the team-status page and a confirmed-roles/Ishaan-contribution page. Role 1 is assigned to Soha Raees (`soharaees`).

The builder at `scripts/update_team_workflow_pdf.py` uses the archived 30 August baseline and writes a QA candidate under `tmp/pdfs/`. Render and visually inspect before publishing the current PDF.

## Companion: Role 3 and Role 4 simple flowchart

`Role3_Role4_Simple_Flowchart.pdf` is a two-page plain-English picture of Role 3 (front desk) and Role 4 (records room) for non-technical teammates. It does not replace v4 and does not change the confirmed role ownership or swimlanes.

Rebuild with `python scripts/build_role3_role4_flowchart_pdf.py` (needs `reportlab`). A browser version lives at `../Role3_Role4_Simple_Flowchart.html`.
