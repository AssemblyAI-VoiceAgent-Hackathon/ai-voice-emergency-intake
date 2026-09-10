# Team PDF update convention

Current team document: `AI_Emergency_Intake_Team_Workflow_Roles.pdf`.

`AI_Emergency_Intake_Team_Workflow_Roles_v5.pdf` is an exact versioned mirror of the current document. Team links should use the stable filename above so a future approved revision does not create competing “current” files. The v4 file is preserved as the previous approved version.

- Keep the original landscape layout, role colours, swimlanes, section order and step references.
- Update the relevant parts in place. Mark changes by version/date and explain what changed from the previous shared version.
- Add a clearly labelled continuation page only when needed; do not replace the established document with a differently structured report.
- Keep the team document in English. Do not include private guidance, personal coaching or a Malay guide for Fazwan.
- The current v5 document must retain the confirmed names: Soha Raees, Fazwan Zainuddin, Mozzam Shahid, Ishaan Sama, Jonathan and Mariam Habib.
- Retain page 6, which records how Ishaan Sama's EmergencyVoice tech-stack contribution is incorporated and which choices remain open.
- Publish the current document as `AI_Emergency_Intake_Team_Workflow_Roles.pdf` and keep the exact v5 mirror; preserve v4 and earlier copies.
- Separate the team's current direction from proposals and decisions awaiting confirmation. Do not infer implementation completion.
- Preserve prior versions in `archive/`; do not share the superseded nine-page alignment report.

Current revision: v5, updated 10 September 2026. The original four pages and confirmed ownership are retained. Pages 5–6 now record implementation evidence, the verified local run path, Supabase setup, security remediation, and the remaining integration/demo gates.

The builder at `scripts/update_team_workflow_pdf.py` uses the archived 30 August baseline, validates a QA candidate under `tmp/pdfs/`, then publishes the stable current file and its exact v5 mirror. Render and visually inspect the stable file before sharing it.

## Companion: Role 3 and Role 4 simple flowchart

`Role3_Role4_Simple_Flowchart.pdf` is a two-page plain-English picture of Role 3 (front desk) and Role 4 (records room) for non-technical teammates. It does not replace v4 and does not change the confirmed role ownership or swimlanes.

Rebuild with `python scripts/build_role3_role4_flowchart_pdf.py` (needs `reportlab`). A browser version lives at `../Role3_Role4_Simple_Flowchart.html`.
