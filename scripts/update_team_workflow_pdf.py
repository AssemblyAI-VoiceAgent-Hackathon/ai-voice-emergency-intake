"""Update the original team PDF without rebuilding its established visual layout.

The archived 30 Aug baseline is immutable input. The stable team filename is the
only current deliverable. Future updates should retain this layout and version map.
"""
from pathlib import Path
from io import BytesIO
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ContentStream, TextStringObject, NameObject

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/pdf/archive/AI_Emergency_Intake_Team_Workflow_Roles_2026-08-30_v1.pdf'
CURRENT = ROOT / 'output/pdf/AI_Emergency_Intake_Team_Workflow_Roles.pdf'
VERSIONED = ROOT / 'output/pdf/AI_Emergency_Intake_Team_Workflow_Roles_v5.pdf'
PREVIEW = ROOT / 'tmp/pdfs/workflow-v5-candidate.pdf'
W,H = 1190.551,841.8898
NAVY=colors.Color(.09,.196,.302)
MUTED=colors.Color(.36,.412,.459)
WHITE=colors.white
BLUE=colors.Color(.184,.42,1)
TEAL=colors.Color(.059,.545,.553)
ORANGE=colors.Color(.902,.494,.133)
PURPLE=colors.Color(.404,.314,.643)
GREEN=colors.Color(.18,.545,.341)
INK=colors.HexColor('#17232F')
PALE=colors.HexColor('#FFF2DC')
AMBER=colors.HexColor('#945511')
ROWCOLS=[colors.Color(.918,.945,1),colors.Color(.894,.961,.957),colors.Color(1,.941,.882),colors.Color(.941,.925,.98),colors.Color(.91,.961,.929)]
ROLE_NAMES={
    1:'SOHA RAEES',
    2:'FAZWAN ZAINUDDIN',
    3:'MOZZAM SHAHID',
    4:'ISHAAN SAMA',
    5:'JONATHAN',
}
reader=PdfReader(BASE)
assert len(reader.pages)==4
writer=PdfWriter()

def p(c,text,x,top,width,size=10.2,leading=None,color=INK,bold=False,align=0):
    sty=ParagraphStyle('p',fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,leading=leading or size*1.3,textColor=color,alignment=align)
    a=Paragraph(text,sty);_,height=a.wrap(width,H)
    assert top+height<800,(text[:70],top,height)
    a.drawOn(c,x,H-top-height)
    return top+height

def rect(c,x,top,w,h,fill,r=0,stroke=None):
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    if r:c.roundRect(x,H-top-h,w,h,r,fill=1,stroke=int(stroke is not None))
    else:c.rect(x,H-top-h,w,h,fill=1,stroke=int(stroke is not None))

def pill(c,label,x,top,w=94):
    rect(c,x,top,w,17,PALE,4)
    p(c,label,x+7,top+4,w-10,size=7.5,leading=8,color=AMBER,bold=True)

def footer(c,page):
    c.setFillColor(MUTED if page!=1 else colors.HexColor('#C8D7E5'))
    c.setFont('Helvetica',8.5)
    c.drawRightString(W-42,24,f'Implementation Workflow v5  |  Updated 10 Sep 2026  |  Page {page}')

def edit_text(page,mapping):
    stream=ContentStream(page.get_contents(),reader)
    seen=Counter()
    for args,op in stream.operations:
        if op==b'Tj':
            text=str(args[0])
            if text in mapping:
                args[0]=TextStringObject(mapping[text]);seen[text]+=1
        elif op==b'TJ':
            for idx,obj in enumerate(args[0]):
                if isinstance(obj,TextStringObject) and str(obj) in mapping:
                    old=str(obj);args[0][idx]=TextStringObject(mapping[old]);seen[old]+=1
    missing=set(mapping)-set(seen)
    assert not missing,missing
    page[NameObject('/Contents')]=stream

for i,page in enumerate(reader.pages,1):
    edits={}
    if i>1:edits[f'Architecture Draft v1  |  30 Aug 2026  |  Page {i}']=''
    if i==1:
        edits['A shared architecture proposal before implementation begins']='Implementation merged; integration and demo-readiness checkpoint | v5 | updated 10 Sep 2026'
        edits['Decision gate: the team reviews and agrees on this structure before role-level implementation starts.']='All five role components are on main. See pages 5-6 for verified evidence, secure setup and the remaining demo gates.'
    if i==3:
        edits.update({
          'Fazwan':'',
          'Persist event, notify staff and publish live status':'FastAPI validates and publishes SSE updates',
          '11. Live intake dashboard':'',
          'Summary, missing data, conflicts, tool status and':'',
          'alerts':'',
          'LIVE EVENT':'',
          'STAFF APPROVAL':'',
        })
    if i==4:
        edits.update({
            'Fazwan':'',
            'Askeri':'',
            'Ishan':'',
        })
        for line in [
            'Response instructions to Role 1; validated tool requests',
            'and structured case events to Role 3.',
            'FastAPI; authentication; endpoint contracts; tool execution;',
            'workflow orchestration; retries; staff notifications; event',
            'publishing.',
            'Database queries/commands to Role 4; live case events',
            'to Role 5; confirmed tool results to Role 2.',
            'Live case events, tool status and structured intake data',
            'from Role 3.',
        ]:edits[line]=''
    edit_text(page,edits)
    stream=BytesIO();c=canvas.Canvas(stream,pagesize=(W,H))
    if i==1:
        rect(c,55,631,1080,106,colors.Color(.122,.255,.365),10,colors.Color(.32,.46,.56))
        p(c,'10 SEP UPDATE - ALL FIVE ROLE COMPONENTS ARE NOW ON MAIN',68,644,1047,12,color=WHITE,bold=True)
        p(c,'<b>Verified locally:</b> backend, voice demo service and dashboard run together; a synthetic case was extracted and accepted by Role 3.',68,665,1047,11,color=WHITE)
        p(c,'<b>Next:</b> rotate exposed keys, configure Supabase securely, close domain review and complete the recorded end-to-end demo and rehearsal.',68,699,1047,10.5,color=WHITE)
        # Small notes in the existing cards; no changes to card order or role colours.
        pill(c,'SSE publisher',506,493,145)
        pill(c,'SSE receiver',944,493,145)
        for x,name,col in zip([55,270,485,700,915],ROLE_NAMES.values(),[BLUE,TEAL,ORANGE,PURPLE,GREEN]):
            p(c,name,x+12,538,179,9.1,11,color=col,bold=True,align=1)
    elif i==2:
        pill(c,'CURRENT FLOW',42,89,110)
    elif i==3:
        rect(c,42,85,1106,17,PALE,4)
        p(c,'CURRENT HANDOFF: step 9 publishes SSE updates to step 11; staff review returns through an API. Lane order and step numbers are unchanged.',49,89,1088,8.4,9,color=AMBER,bold=True)
        # Reuse the original label centres. Underlying old text was removed above.
        rect(c,630,516,62,13,PALE,3)
        p(c,'SSE UPDATE',636,519,60,7.5,8,color=GREEN,bold=True)
        rect(c,918,470,85,13,PALE,3)
        p(c,'STAFF REVIEW API',922,473,82,7.2,8,color=GREEN,bold=True)
        pill(c,'UPDATED',827,378,66)
        rect(c,833,641,64,11,PALE,3)
        p(c,'UPDATED',840,643,54,6.4,7,color=AMBER,bold=True)
        p(c,'11. Live intake dashboard',710,655,185,8.7,10,bold=True,align=1)
        p(c,'Draft, gaps, conflicts and tool status via SSE.<br/>Staff reviews the information.',708,667,189,8.7,11,align=1)
        for top,name in [(172,ROLE_NAMES[1]),(294,ROLE_NAMES[2]),(427,ROLE_NAMES[3]),(560,ROLE_NAMES[4]),(692,ROLE_NAMES[5])]:
            p(c,name,36,top,92,6.9,8,color=WHITE,bold=True,align=1)
    elif i==4:
        pill(c,'UPDATED CELLS',42,166,113)
        p(c,'Highlighted notes clarify the current SSE handoff. Role 1 is assigned to Soha Raees.',166,169,970,9,color=MUTED)
        # The original table grid is retained. Only four cells gain revised text.
        p(c,'<font color="#945511"><b>CURRENT</b></font><br/>Response text to Role 1; tool requests and structured extraction to Role 3. The backend owns the SSE event wrapper.',445,350,218,9,12)
        p(c,'<font color="#945511"><b>CURRENT</b></font><br/>FastAPI; authentication; validation; tool execution; workflow orchestration; SSE publishing and reconnection; staff-review APIs.',175,450,250,9,12)
        p(c,'<font color="#945511"><b>CURRENT</b></font><br/>Queries and approved saves to Role 4; live SSE updates to Role 5; actual tool results to Role 2.',445,450,218,9,12)
        p(c,'<font color="#945511"><b>CURRENT</b></font><br/>SSE updates with the draft, missing information, conflicts and tool status from Role 3; confirmed review/save responses.',680,645,218,9,12)
        for top,name in [(304,ROLE_NAMES[1]),(404,ROLE_NAMES[2]),(504,ROLE_NAMES[3]),(604,ROLE_NAMES[4]),(704,ROLE_NAMES[5])]:
            p(c,name,50,top,112,8.5,10,bold=True)
    footer(c,i)
    c.save();stream.seek(0)
    page.merge_page(PdfReader(stream).pages[0])
    writer.add_page(page)

# One continuation page: same dimensions, typography, headings, margins and role colours.
stream=BytesIO();c=canvas.Canvas(stream,pagesize=(W,H))
c.setFillColor(NAVY);c.setFont('Helvetica-Bold',23)
c.drawString(42,H-48,'4. Implementation Status and Demo Readiness')
p(c,'10 September update - all five role components are on main; credential rotation, integration and presentation gates remain.',42,58,1040,10.5,color=MUTED)
c.setStrokeColor(colors.HexColor('#D9E1E8'));c.line(42,H-78,W-42,H-78)
pill(c,'CURRENT v5',1056,33,92)
rect(c,42,94,1106,49,colors.HexColor('#EAF0FF'),8,colors.HexColor('#ADC4FF'))
p(c,'<b>Current implementation:</b> AssemblyAI-compatible voice + Role 2 extraction + FastAPI/SSE + Supabase/SQLite + Next.js dashboard.',50,104,1088,10.3)
p(c,'<b>Readiness rule:</b> component delivery is complete; competition readiness requires secure keys, domain sign-off and a recorded end-to-end rehearsal.',50,123,1088,10.1)

def table(headers,rows,widths,top,row_colours=None,size=9.5,pad=8):
    hs=ParagraphStyle('h',fontName='Helvetica-Bold',fontSize=size,leading=size*1.25,textColor=WHITE)
    bs=ParagraphStyle('b',fontName='Helvetica',fontSize=size,leading=size*1.3,textColor=INK)
    data=[[Paragraph(h,hs) for h in headers]]+[[Paragraph(v,bs) for v in row] for row in rows]
    t=Table(data,colWidths=widths)
    t.setStyle(TableStyle([
      ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
      ('LEFTPADDING',(0,0),(-1,-1),pad),('RIGHTPADDING',(0,0),(-1,-1),pad),
      ('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
      ('GRID',(0,0),(-1,-1),.5,colors.HexColor('#B9CAD6')),
      ('ROWBACKGROUNDS',(0,1),(-1,-1),row_colours or [WHITE,colors.HexColor('#F5F7FA')])
    ]))
    _,h=t.wrap(W,H)
    assert top+h<783,top+h
    t.drawOn(c,42,H-top-h)
    return top+h

p(c,'Verified implementation state',42,157,1100,12.5,bold=True,color=NAVY)
end=table(['Area','Evidence verified by 10 September','Meaning'],[
 ('Roles 1-5','All implementation paths are on main; Role 1-5 delivery issues are closed.','Component delivery is complete; PR #34 contains the final integration improvements.'),
 ('Local verification','49 Python tests, 6 dashboard tests, contract validation, Next.js 16.3.4 production build and npm audit pass.','Backend :8000, voice demo :8001 and dashboard :3000 can run together; the dependency audit reports zero known vulnerabilities.'),
 ('Hosted services','Team evidence reports AssemblyAI and Supabase testing; Fazwan\'s machine has no local .env yet.','Hosted access is not ready on this machine until fresh keys are configured securely.')
],[221,363,522],177,size=9.3,pad=7)

p(c,'Readiness actions in order',42,end+15,1100,12.5,bold=True,color=NAVY)
end=table(['Priority / owner','Action','Completion evidence'],[
 ('<b>1 - Security / key owners</b>','PR #35 merged with .env. PR #36 removes it, but key owners must still rotate every exposed value before public deployment.','Old keys revoked; fresh values exist only in approved secret stores; a secret scan passes.'),
 ('<b>2 - Ishaan + Fazwan</b>','Create a new local .env from .env.example; use the project URL and fresh server-side key. Never commit it.','python -m src.data --check-supabase reports OK without printing credentials.'),
 ('<b>3 - Role 4 + Role 3</b>','Confirm the Role 4 migration and tables in Supabase Table Editor; run one synthetic lookup and approved save.','Patient lookup, case, review, approved record and audit row are visible exactly once.'),
 ('<b>4 - All technical owners</b>','Run backend, voice and dashboard together; complete one synthetic intake-to-review-to-save flow.','Issue #7 has timestamps, case ID, screenshots/log summary and known limitations.'),
 ('<b>5 - Domain + Mariam</b>','Close clinical/safety decisions, prepare fallback screenshots/recording and run a timed rehearsal.','Issues #6 and #11 are closed with sign-off, script, timing and action items.')
],[173,460,473],end+36,row_colours=ROWCOLS+[colors.HexColor('#F5F7FA')],size=9.5,pad=8)

top=end+17
rect(c,42,top,1106,86,PALE,8,colors.HexColor('#EDC88C'))
p(c,'NEXT TEAM CHECKPOINT - DEMO READINESS, NOT MORE FEATURE BUILDING',52,top+10,1085,10.5,color=AMBER,bold=True)
p(c,'Use the merged implementation as-is. Focus on secure configuration, one repeatable synthetic scenario, human-review evidence and a backup demo path.',52,top+29,1084,9.8)
p(c,'Do not use real patient data. AI output remains an unverified draft; authorised staff retain the final clinical decision. Domain approval rules must be recorded before the competition demo.',52,top+57,1084,9.8)
p(c,'Stable run guide: GETTING_STARTED.md. Supabase is optional for local development; SQLite is the safe fallback. Hosted persistence requires the migration and fresh keys.',42,top+97,1106,8.4,color=MUTED)
p(c,'Technical reference: <link href="https://fastapi.tiangolo.com/tutorial/server-sent-events/" color="#0F8B8D">FastAPI SSE documentation</link>. PR #36 reverified after merging the latest main on 10 September 2026.',42,top+112,1106,8.4,color=MUTED)
footer(c,5);c.save();stream.seek(0)
writer.add_page(PdfReader(stream).pages[0])

# Page 6 records the confirmed roster and incorporates Ishaan Sama's separate
# tech-stack proposal without silently replacing the current FastAPI + SSE direction.
stream=BytesIO();c=canvas.Canvas(stream,pagesize=(W,H))
c.setFillColor(NAVY);c.setFont('Helvetica-Bold',23)
c.drawString(42,H-48,'5. Confirmed Roles, Delivered Components and Supabase')
p(c,'All role implementations are now on main. Ownership remains unchanged; the team now moves to integration and demo readiness.',42,58,1040,10.5,color=MUTED)
c.setStrokeColor(colors.HexColor('#D9E1E8'));c.line(42,H-78,W-42,H-78)
pill(c,'CURRENT v5',1048,59,100)

p(c,'Confirmed role ownership and delivered paths',42,96,1100,12.5,bold=True,color=NAVY)
end=table(['Role','Registered team member','Delivered on main'],[
 ('<b>Role 1</b>','<b>Soha Raees</b>','src/voice: AssemblyAI-compatible conversation, turn sanitisation, demo handoff and voice UI.'),
 ('<b>Role 2</b>','<b>Fazwan Zainuddin</b>','src/extraction: schema-first extraction, safe failures, demo adapter and OpenAI-compatible provider.'),
 ('<b>Role 3</b>','<b>Mozzam Shahid</b>','src/backend: FastAPI authentication, validation, SSE, tools, staff review and persistence handoff.'),
 ('<b>Role 4</b>','<b>Ishaan Sama</b>','src/data + migration: synthetic data, Supabase/SQLite persistence, RBAC, encryption and audit.'),
 ('<b>Role 5</b>','<b>Jonathan</b>','app/dashboard + components: live case list, gaps/conflicts, edits, review and approval workflow.'),
 ('<b>Demo</b>','<b>Mariam Habib</b>','Issue #11 remains open: demo script, rehearsal, fallback assets and presentation delivery.')
],[110,245,751],116,row_colours=ROWCOLS+[colors.HexColor('#F5F7FA')],size=9.3,pad=7)

p(c,'Ishaan Sama tech-stack input - implementation outcome',42,end+16,1100,12.5,bold=True,color=NAVY)
end=table(['Contribution','Current implementation','Owner / readiness'],[
 ('AssemblyAI voice layer','Role 1 includes the AssemblyAI-compatible agent, browser audio/captions, turn-taking configuration and secure token route.','Role 1 + Role 3; live use needs a fresh AssemblyAI key.'),
 ('Demo call transport','Browser voice UI is the MVP transport. Twilio is not required for the current competition path.','Role 1 + Role 5; local demo path verified.'),
 ('Schema-first extraction','StructuredCase remains schema-first with sources, gaps, conflicts and safe failure. OpenRouter/OpenAI is optional; demo fallback exists.','Role 2 + Role 3; tests pass.'),
 ('Distress indicator','Safety signals remain separate from final clinical triage. No autonomous diagnosis or final decision is permitted.','Roles 2/3/5; domain vocabulary still needs #6 sign-off.'),
 ('Mock patient data','Supabase/Postgres is the hosted store; SQLite is the local/test fallback. The Role 4 migration creates case/review/audit tables.','Role 4 + Role 3; confirm fresh-key access and migration.'),
 ('Brief and dashboard','FastAPI publishes SSE updates to the Next.js staff dashboard; review actions return through Role 3 and save through Role 4.','Roles 2/3/4/5; automated and local smoke tests pass.'),
 ('Privacy and scope','Synthetic data, RBAC, encryption, retention and audit controls are implemented. Secrets stay in an untracked local .env.','All roles; exposed keys must be rotated before live demo.')
],[205,603,298],end+37,row_colours=[colors.HexColor('#F7FAFC'),colors.HexColor('#EEF6F5')],size=8.35,pad=6)

top=end+15
rect(c,42,top,1106,49,PALE,8,colors.HexColor('#EDC88C'))
p(c,'REMAINING READINESS GATES',52,top+9,1085,10.2,color=AMBER,bold=True)
p(c,'Rotate exposed keys; configure a clean local .env; replace demo-only browser authentication before public hosting; verify Supabase and one approved save; close #6, #7 and #11; rehearse.',52,top+27,1084,9.2)
p(c,'Contribution source: Ishaan Sama, EmergencyVoice - Tech Stack Document (31 Aug 2026). Current evidence: latest main plus PR #36 verification on 10 Sep 2026.',42,top+63,1106,8.4,color=MUTED)
footer(c,6);c.save();stream.seek(0)
writer.add_page(PdfReader(stream).pages[0])

writer.add_metadata({
 '/Title':'AI Emergency Patient Intake - Team Workflow and Role Ownership',
 '/Author':'International Competition Team Fazwan',
 '/Subject':'Implementation Workflow v5 - updated 10 Sep 2026 - demo readiness and Supabase setup',
 '/Keywords':'team workflow, implementation status, demo readiness, Supabase, FastAPI, SSE, v5, security',
})
PREVIEW.parent.mkdir(parents=True,exist_ok=True)
with PREVIEW.open('wb') as f:writer.write(f)
result=PdfReader(PREVIEW)
assert len(result.pages)==6
full='\n'.join(q.extract_text() for q in result.pages)
assert 'Architecture Draft v1' not in full
assert 'Panduan ringkas' not in full and 'Bahasa Melayu' not in full
assert 'SSE UPDATE' in full and 'STAFF REVIEW API' in full
for name in ROLE_NAMES.values():
    assert name in full
assert 'EmergencyVoice - Tech Stack Document' in full
for label in ['1. Current Emergency Intake Flow','2. Proposed AI-Assisted Workflow by Role','3. Ownership and Handoff Contract']:
    assert label in full
published = PREVIEW.read_bytes()
CURRENT.write_bytes(published)
VERSIONED.write_bytes(published)
assert CURRENT.read_bytes() == VERSIONED.read_bytes()
print('Candidate:',PREVIEW)
print('Pages:',len(result.pages))
print('Last-page content bottom:',round(top+125,1))
print('Published current:',CURRENT)
print('Published versioned mirror:',VERSIONED)
