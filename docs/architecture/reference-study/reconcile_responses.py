from pathlib import Path
import json
ROOT=Path(__file__).parent
app=json.loads((ROOT/'application-proposals.json').read_text(encoding='utf-8'))
templates=json.loads((ROOT/'template-proposals.json').read_text(encoding='utf-8'))
ar={'AF01':'reject','AF04':'reject','AF06':'reject','AF07':'other','AF08':'other','AF09':'other','AF10':'reject','AF12':'other','AF13':'other','AF14':'other','AF15':'reject','AF17':'other','AF18':'reject','AF19':'reject','AF21':'reject','AF24':'reject'}
an={
'AF04':'Keep CTM, but add for each prior marriage: spouse name and Ecclesiastical Marriage Permit. Do not adopt the proposed full history.',
'AF07':'Ask religious affiliation before the parties knew each other. If Coptic Orthodox, proceed; otherwise type the denomination.',
'AF08':'Interview questionnaire only, not application.','AF09':'Interview questionnaire only, not application.',
'AF12':'Interview questionnaire only, not application.','AF13':'Interview questionnaire only, not application.','AF14':'Interview questionnaire only, not application.',
'AF17':'Similar wording already discussed/decided; consolidate, do not add another duplicate prompt.',
'AF21':'Previously addressed; keep the confirmed CTM prior-application design.',
'AF23':'Blood relationship only (for example cousins); describe relationship if yes. Do not add adoption inquiry.'}
tr={'QT22':'reject','QT23':None,'QT26':'reject','QT27':'reject','QT28':'other','QT30':'reject'}
tn={'QT07':'Organize into explicit topics: Children, Money, Intimacy, etc.','QT23':'Proposed idea liked, wording too ambiguous; explicitly identify medical, psychological, etc. Revised wording remains for confirmation.','QT28':'Is there a specific intimate marital difficulty you wish to explain, including when it arose or became known?'}
special={
'AF01':'No new requested-outcome control in the application. Interview request/basis remains.',
'AF04':'Narrow override: spouse name + Ecclesiastical Marriage Permit per prior marriage, preserving existing CTM form; no full-history expansion.',
'AF05':'Accept known spouse prior-marriage information with Unknown allowed. No compulsory spouse account or automatic access to former cases.',
'AF07':'Replace proposed at-marriage affiliation with affiliation before the parties knew each other; Coptic Orthodox skips denomination text; otherwise typed denomination; existing Unknown spouse rule remains.',
'AF08':'Route to interview, not application.','AF09':'Route to interview, not application.','AF12':'Route to interview, not application.','AF13':'Route to interview, not application.','AF14':'Route to interview, not application.',
'AF17':'Merge specificity guidance with accepted AF02/AF16; no duplicated application question.',
'AF21':'No replacement label; existing multi-entry prior-application policy remains.',
'AF23':'Use only blood relationship (e.g. cousins), not adoption; factual answer not automatic canonical outcome.',
'QT07':'Category-based decision-to-marry discovery, including explicit Children, Money and Intimacy topics.',
'QT23':'Draft explicit medical/psychological/psychiatric help wording separately; not finalized just because topic was liked.',
'QT28':'Use user wording as a narrow intimate-difficulty question; no blanket intimate-history inventory.',
'QT31':'Superseded/enriched by direct priest testimony request: scoped link, identified subject, free-form writing or recording.',
'QT33':'Relevant non-confessional assistance only; preserve author and limits of knowledge.',
'QT35':'Author/date/authenticated submission record accepted; signature/link-authentication mechanics not yet finalized.',
'QT36':'Use common core plus selected accepted categories. Exclude rejected QT22/26/27/30 despite their appearance in the original routing proposal.'}
lines=['# Catholic-reference review decisions and category-based interview requirements','',
'Source: user returned both reference-review questionnaires and added a priest testimony workflow. All 60 response IDs are reconciled below. Clarifications override selected Accept/Reject choices. Documentation and template planning only; no prototype, application or database implementation.','',
'## Application review','', '| ID | Returned answer | Reconciled treatment |','|---|---|---|']
exports=[]
for rows,answers,notes,version in [(app,ar,an,'ctm-reference-application-review-v1'),(templates,tr,tn,'ctm-reference-template-review-v1')]:
    if rows is templates:lines+=['','## Interview question and template review','', '| ID | Returned answer | Reconciled treatment |','|---|---|---|']
    result=[]
    for p in rows:
        a=answers.get(p['id'],'accept')
        treatment=special.get(p['id'],('Accept the proposal within its stated scope: '+p['proposed']) if a=='accept' else 'Do not add/replace this proposal; preserve prior approved CTM policy.')
        lines.append(f"| {p['id']} | {a or 'undecided'} | {treatment} |")
        result.append({'id':p['id'],'proposal':p,'answer':a,'clarification':notes.get(p['id'],''),'reconciledTreatment':treatment})
    exports.append({'questionnaireVersion':version,'source':'User message; clarifications normalized for spelling, response values retained.','answers':result,'generalNotes':'Category-based interview/report assembly and link-based priest free-form testimony specified separately in decision register.'})
for name,result in zip(['application-returned-answers.json','template-returned-answers.json'],exports):
    (ROOT/name).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
lines+=['','## Applicant form boundary','',
'Application stays concise. Do not add the rejected outcome selector, full multi-ceremony form, temporary-separation repeat, attachment-explanation field, changed church labels or living/deceased screen. Keep required document/fee/identity rules already agreed. Adopt AF02/03/11/16/20/22 wording/guide changes and accepted AF05/23 scope. AF04 is a narrow addition, not its rejected broader proposal. AF08/09/12/13/14 move to the council interview questionnaire. AF17 is consolidated existing guidance, not another field. Questionnaire wording does not change source identity/case matching automatically.','',
'## Category-driven guided interview and assembled report','',
'Assigned member selects Common question family categories relevant to the case. Each category exposes detailed numbered prompts; the report is assembled from the selected categories, actual recorded answers, evidence references and separate member observations. Retain the required identity opening for every interview/new recording and the common request/basis context. Do not require every category for every case.','',
'Categories and question IDs are versioned. Preserve the selected category/question version and display order for that interview. Changes to selections must not silently delete existing answers, recordings or markers. Case-specific follow-ups stay attributable additions. Report assembly is deterministic organization of stored material, not AI inference into questionnaire answers or a council ruling. Manual answers, original audio, reviewed transcripts and findings remain separate. No case-export feature is added.','',
'Children, Money and Intimacy are explicit topics with detail, rather than vague “understanding marriage” text. Intimacy uses the user’s narrow prompt; medical/psychological help has revised draft wording awaiting confirmation. No separate generic communication category (QT22), civil/church chronology supplement (QT26), full prior-marriage interview supplement (QT27) or appeal-question block (QT30) is added. Existing appeals process and source facts are not removed by rejecting those templates.','',
'The [category question bank](../CTM-interview-category-bank.md) and [interactive planning preview](interview-category-planner.html) show a concrete structure. The structure is user-directed; detailed newly expanded wording is a review draft, not an automatically published institutional template. English review wording does not replace the approved bilingual versioning requirement.','',
'## Council-requested priest testimony','',
'An authorized case sender (assigned member, admin or secretary under existing correspondence rules) may ask a priest for testimony based on the priest’s knowledge of the marriage circumstances. Priest receives a link scoped to that requested report. This is a separate externally submitted report, not a council membership, applicant account or general witness-interview feature.','',
'The free-form report identifies the marriage/case and explicitly whom the report concerns: party names and subject party or both, as specified by the request. Priest author identity is a separate field. Display the report subject in the template header; do not rely on an email subject line alone. Provide a free-form writing area or audio capture/upload option. The content is not a forced multi-question witness form. Retain author, request, source, submission and timestamps.','',
'Recorded report uses previously agreed audio/transcription/translation behavior: original retained; original-language transcript, English/Arabic translation and both complete versions for mixed speech; timestamps/speaker labels, correction history and council-only access after the applicable review. The original AI output is never substituted for authored free-form testimony. Identity must be stated at the beginning of a new recording.','',
'Link authorizes only the intended report action and minimal case/subject context, not access to questionnaires, council notes or other submissions. Requested report and delivered message are linked into existing case correspondence. No priest directory, case browsing, publication to applicants or sacramental-confession content is introduced. Exact link verification/expiry, post-submission editing and AI-text reviewer for external priest reports remain to be decided; do not infer them from applicant interview review rules.','',
'## Proposed schema refinements','',
'- Versioned `interview_question_categories`, category/question membership and per-interview selection snapshots, with stable IDs/order and accepted proposal provenance. Reuse template version/answer/evidence/marker models.','- `interview_report_revisions`: interview/proceeding, exact selected template/answer versions, structured section references and separate observations, assembler actor/time. Report is a projection/snapshot, never another editable source of applicant facts.','- `priest_testimony_requests`: case/proceeding, request sender, intended priest, explicit subject party/marriage, minimal instructions, scope and issued/delivery events.','- `priest_testimony_submissions`: request, attributed priest author, written text and/or immutable audio versions, actual submitter/authentication evidence and submission time; council-private.','- Scoped external report access tokens/verification events and purpose-specific AI text review events. Reuse file/processing/correspondence/audit/outbox tables; no blanket external case access.','',
'## Remaining focused clarification','',
'Medical wording draft: “Have you or your spouse received medical, psychological or psychiatric treatment relevant to the issue discussed? If so, describe the treatment or professional help, when it occurred, what you know directly and how it relates to the marriage.” No blanket records authorization or diagnosis is inferred. User has not yet approved the revised exact wording.','',
'Priest report link security, its transcript reviewer and treatment of updates after submission require their own concrete decisions. These should not reopen already settled application and interview choices.']
(ROOT.parent/'CTM-reference-review-decisions.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Reconciled 24 application responses and 36 template responses, preserving all 60 source IDs.')
