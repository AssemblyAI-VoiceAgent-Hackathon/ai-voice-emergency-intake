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
OUT = ROOT / 'output/pdf/AI_Emergency_Intake_Team_Workflow_Roles_v4.pdf'
PREVIEW = ROOT / 'tmp/pdfs/workflow-v4-candidate.pdf'
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
    c.drawRightString(W-42,24,f'Architecture Draft v4  |  3 Sep 2026  |  Page {page}')

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
        edits['A shared architecture proposal before implementation begins']='Role 1 reassignment and confirmed team update | v4 | 3 Sep 2026'
        edits['Decision gate: the team reviews and agrees on this structure before role-level implementation starts.']='Team review: confirmed owners are named throughout. See page 6 for Ishaan Sama\'s technical contribution and open decisions.'
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
        p(c,'3 SEP UPDATE - ROLE 1 REASSIGNED AND TEAM ROSTER CONFIRMED',68,644,1047,12,color=WHITE,bold=True)
        p(c,'<b>Confirmed:</b> Soha Raees (Role 1), Fazwan Zainuddin (Role 2), Mozzam Shahid (Role 3), Ishaan Sama (Role 4) and Jonathan (Role 5).',68,665,1047,11,color=WHITE)
        p(c,'<b>Added:</b> Ishaan Sama\'s EmergencyVoice tech-stack contribution is mapped to the team workflow on page 6. <b>Retained:</b> FastAPI + SSE and human-owned clinical decisions.',68,699,1047,10.5,color=WHITE)
        # Small notes in the existing cards; no changes to card order or role colours.
        pill(c,'v2: SSE publisher',506,493,145)
        pill(c,'v2: SSE receiver',944,493,145)
        for x,name,col in zip([55,270,485,700,915],ROLE_NAMES.values(),[BLUE,TEAL,ORANGE,PURPLE,GREEN]):
            p(c,name,x+12,538,179,9.1,11,color=col,bold=True,align=1)
    elif i==2:
        pill(c,'UNCHANGED FROM v1',42,89,153)
    elif i==3:
        rect(c,42,85,1106,17,PALE,4)
        p(c,'UPDATED IN v2: step 9 publishes SSE updates to step 11; staff review returns through an API. Lane order and step numbers are unchanged.',49,89,1088,8.4,9,color=AMBER,bold=True)
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
        p(c,'Highlighted notes clarify the SSE handoff. Role 1 is reassigned to Soha Raees in v4; the table structure is unchanged.',166,169,970,9,color=MUTED)
        # The original table grid is retained. Only four cells gain revised text.
        p(c,'<font color="#945511"><b>UPDATED v2</b></font><br/>Response text to Role 1; tool requests and structured extraction to Role 3. The backend owns the SSE event wrapper.',445,350,218,9,12)
        p(c,'<font color="#945511"><b>UPDATED v2</b></font><br/>FastAPI; authentication; validation; tool execution; workflow orchestration; SSE publishing and reconnection; staff-review APIs.',175,450,250,9,12)
        p(c,'<font color="#945511"><b>UPDATED v2</b></font><br/>Queries and approved saves to Role 4; live SSE updates to Role 5; actual tool results to Role 2.',445,450,218,9,12)
        p(c,'<font color="#945511"><b>UPDATED v2</b></font><br/>SSE updates with the draft, missing information, conflicts and tool status from Role 3; confirmed review/save responses.',680,645,218,9,12)
        for top,name in [(304,ROLE_NAMES[1]),(404,ROLE_NAMES[2]),(504,ROLE_NAMES[3]),(604,ROLE_NAMES[4]),(704,ROLE_NAMES[5])]:
            p(c,name,50,top,112,8.5,10,bold=True)
    footer(c,i)
    c.save();stream.seek(0)
    page.merge_page(PdfReader(stream).pages[0])
    writer.add_page(page)

# One continuation page: same dimensions, typography, headings, margins and role colours.
stream=BytesIO();c=canvas.Canvas(stream,pagesize=(W,H))
c.setFillColor(NAVY);c.setFont('Helvetica-Bold',23)
c.drawString(42,H-48,'4. Team Status and Next Actions')
p(c,'3 September update - Role 1 reassigned to Soha Raees; next actions and the shared synthetic-case target remain unchanged.',42,58,1040,10.5,color=MUTED)
c.setStrokeColor(colors.HexColor('#D9E1E8'));c.line(42,H-78,W-42,H-78)
pill(c,'NEW IN v2',1056,33,92)
rect(c,42,94,1106,49,colors.HexColor('#EAF0FF'),8,colors.HexColor('#ADC4FF'))
p(c,'<b>Current direction:</b> FastAPI + SSE. <b>Example received:</b> EXTRACTION_UPDATE JSON. <b>Implementation status:</b> each owner to confirm; no completion is assumed.',50,104,1088,10.3)
p(c,'The shared payload is an example, not yet the final contract. SSE specifies live delivery; it does not decide which database we use.',50,123,1088,10.1)

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

p(c,'What changed from the version already shared?',42,157,1100,12.5,bold=True,color=NAVY)
end=table(['Reference in v1','Earlier wording / position','v2 update'],[
 ('Page 3: step 9 to step 11','LIVE EVENT; transport not named on the diagram.','SSE UPDATE: FastAPI sends live draft updates to the staff dashboard.'),
 ('Page 3: review return path','STAFF APPROVAL.','STAFF REVIEW API: staff edits/approval return to Role 3; approved records are saved via Role 4.'),
 ('Page 4: handoffs; page 5 added','Generic live case events; no dated next-action sheet.','SSE sender/receiver responsibilities clarified; shared data decisions and next deliverables listed below.')
],[221,363,522],177,size=9.3,pad=7)

p(c,'Next deliverable from each owner',42,end+15,1100,12.5,bold=True,color=NAVY)
end=table(['Same role / owner','Next action','Evidence to share with the team'],[
 ('<b>Role 1 - Soha Raees</b>','Provide transcript turns and session references; connect the follow-up response from Role 2.','One synthetic spoken exchange becomes text, followed by one question and answer.'),
 ('<b>Role 2 - Fazwan Zainuddin</b>','Align extraction fields with the sample; retain source labels; prepare the prompt and expected outputs.','Examples for sufficient, missing and conflicting information; output ready for Role 3 validation.'),
 ('<b>Role 3 - Mozzam Shahid</b>','Confirm intake/review interfaces and authentication; publish the agreed sample through SSE.','One sample update reaches Role 5; reconnect works; review and save confirmation are returned.'),
 ('<b>Role 4 - Ishaan Sama</b>','Confirm database, identifiers, authorised retrieval and approved-record/audit storage.','One synthetic lookup, one not-found result and one saved approved record without duplicate writes.'),
 ('<b>Role 5 - Jonathan</b>','Display SSE draft updates; show gaps/conflicts; send staff edits and approval back to Role 3.','One live update without refresh; staff corrections survive later updates; save status is visible.'),
 ('<b>Demo - Mariam Habib</b>','Coordinate a script and joint test once owners report readiness; use synthetic data only.','One complete intake-to-review-to-save demonstration; any simulated component is labelled.')
],[173,460,473],end+36,row_colours=ROWCOLS+[colors.HexColor('#F5F7FA')],size=9.5,pad=8)

top=end+17
rect(c,42,top,1106,86,PALE,8,colors.HexColor('#EDC88C'))
p(c,'TEAM CONFIRMATION BEFORE INTEGRATION',52,top+10,1085,10.5,color=AMBER,bold=True)
p(c,'<b>Roles 2 / 3 / 5:</b> agree field/event names, full-state vs partial updates, versions, unknown/source handling and review protection. <b>Roles 3 / 4 / 5:</b> confirm database, authentication and reconnect/save behaviour.',52,top+29,1084,9.8)
p(c,'<b>Everyone:</b> reply with agree / requested changes, what is ready, next deliverable, blocker and target test date. First target: one shared synthetic case reaches the dashboard, is reviewed by staff and is saved successfully.',52,top+57,1084,9.8)
p(c,'Scope: same workflow and owners as the previously shared PDF. AI prepares a draft; authorised staff retain the final clinical decision. Clinical approval rules require domain review.',42,top+97,1106,8.4,color=MUTED)
p(c,'Technical reference: <link href="https://fastapi.tiangolo.com/tutorial/server-sent-events/" color="#0F8B8D">FastAPI SSE documentation</link>. Based on the 30 Aug workflow and the 31 Aug team update. Full implementation readiness is for owners to confirm.',42,top+112,1106,8.4,color=MUTED)
footer(c,5);c.save();stream.seek(0)
writer.add_page(PdfReader(stream).pages[0])

# Page 6 records the confirmed roster and incorporates Ishaan Sama's separate
# tech-stack proposal without silently replacing the current FastAPI + SSE direction.
stream=BytesIO();c=canvas.Canvas(stream,pagesize=(W,H))
c.setFillColor(NAVY);c.setFont('Helvetica-Bold',23)
c.drawString(42,H-48,'5. Confirmed Team Roles and Ishaan Sama Contribution')
p(c,'Current team names are listed below. Role 1 was reassigned to Soha Raees on 3 September 2026.',42,58,1040,10.5,color=MUTED)
c.setStrokeColor(colors.HexColor('#D9E1E8'));c.line(42,H-78,W-42,H-78)
pill(c,'UPDATED IN v4',1048,59,100)

p(c,'Confirmed role ownership',42,96,1100,12.5,bold=True,color=NAVY)
end=table(['Role','Registered team member','Primary ownership'],[
 ('<b>Role 1</b>','<b>Soha Raees</b>','Real-time voice, transcript turns, turn-taking, interruption handling and spoken response.'),
 ('<b>Role 2</b>','<b>Fazwan Zainuddin</b>','Agent prompt, structured extraction, source/confidence, gaps, conflicts and safety guardrails.'),
 ('<b>Role 3</b>','<b>Mozzam Shahid</b>','FastAPI backend, authentication, validation, orchestration, SSE and review APIs.'),
 ('<b>Role 4</b>','<b>Ishaan Sama</b>','Synthetic patient data, authorised retrieval, persistence, audit, privacy and retention.'),
 ('<b>Role 5</b>','<b>Jonathan</b>','Staff dashboard, live updates, human review, corrections and approval interface.'),
 ('<b>Demo</b>','<b>Mariam Habib</b>','Team coordination, synthetic demo script, rehearsal and presentation flow.')
],[110,245,751],116,row_colours=ROWCOLS+[colors.HexColor('#F5F7FA')],size=9.3,pad=7)

p(c,'Ishaan Sama tech-stack input - incorporated into team planning',42,end+16,1100,12.5,bold=True,color=NAVY)
end=table(['Contribution','How it is incorporated','Owner / status'],[
 ('AssemblyAI voice layer','Voice Agent API with STT, VAD/turn-taking, sentiment, disfluency, word timestamps and tool calling is the proposed real-time signal source.','Role 1 + Role 3; model/API choice to confirm.'),
 ('Demo call transport','Use browser/WebRTC for the fastest demo; keep Twilio as an optional realism upgrade if time and cost permit.','Role 1 + Role 3; open decision.'),
 ('Schema-first extraction','Use JSON-Schema tool calling; represent missing data as nullable/unknown and never force or guess a clinical value.','Role 2 + Role 3; aligned with current contract.'),
 ('Distress indicator','Combine sentiment, disfluency and pacing into an auditable HIGH/MEDIUM/LOW signal, kept separate from clinical severity and final triage.','Roles 2/3/5; formula requires agreement.'),
 ('Mock patient data','Use synthetic records, server-side filtered lookup and an explicit retention/audit policy. SQLite is sufficient for MVP; Postgres remains an option.','Role 4 + Role 3; DB choice open.'),
 ('Brief and dashboard','Generate a fixed structured brief, publish through the current FastAPI + SSE path and require visible human review. LeMUR is a candidate, not an automatic dependency.','Roles 2/3/5; FastAPI + SSE retained.'),
 ('Privacy and scope','Apply PII redaction to retained transcripts, use synthetic data, state what is deleted/retained and prohibit autonomous diagnosis or triage scoring.','All roles; mandatory safety constraint.')
],[205,603,298],end+37,row_colours=[colors.HexColor('#F7FAFC'),colors.HexColor('#EEF6F5')],size=8.35,pad=6)

top=end+15
rect(c,42,top,1106,49,PALE,8,colors.HexColor('#EDC88C'))
p(c,'DECISIONS TO CLOSE EARLY',52,top+9,1085,10.2,color=AMBER,bold=True)
p(c,'Universal-3 Pro/API availability; browser-only vs Twilio; SQLite vs Postgres; LeMUR vs current LLM path; exact distress-signal formula; raw-audio and transcript retention.',52,top+27,1084,9.2)
p(c,'Contribution source: Ishaan Sama, EmergencyVoice - Tech Stack Document (31 Aug 2026). Team direction remains FastAPI + SSE unless the owners agree a documented change.',42,top+63,1106,8.4,color=MUTED)
footer(c,6);c.save();stream.seek(0)
writer.add_page(PdfReader(stream).pages[0])

writer.add_metadata({
 '/Title':'AI Emergency Patient Intake - Team Workflow and Role Ownership',
 '/Author':'International Competition Team Fazwan',
 '/Subject':'Architecture Draft v4 - 3 Sep 2026 - Role 1 reassigned to Soha Raees',
 '/Keywords':'team workflow, confirmed role ownership, Soha Raees, Ishaan Sama, FastAPI, SSE, v4, team review',
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
print('Candidate:',PREVIEW)
print('Pages:',len(result.pages))
print('Last-page content bottom:',round(top+125,1))
print('Stable destination after visual QA:',OUT)
