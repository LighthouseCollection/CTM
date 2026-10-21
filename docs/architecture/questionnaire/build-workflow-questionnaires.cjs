const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const root=__dirname;
const specs=[
{slug:'applicant-portal',title:'Applicant portal workflow',version:'ctm-applicant-portal-review-v1',intro:'Decide what applicants can do inside their portal. Yes / No / Other; describe your preferred alternative in the text area.',baseline:'Already confirmed: verified accounts, isolated applicant data, private drafts, original/history preservation, case messages and notices, testimony Confirm/Reject, applicant-only appeal supplements, and explicit decree release. These remain the baseline. The future marriage portal is outside this review.',sections:[
 ['home','Portal home & case navigation','What the applicant sees first.',[
  ['P01','Should the portal home show the applicant’s current case, unfinished draft and any pending appeal together?','Show only that applicant’s permitted records; a pending appeal may relate to the same case.'],
  ['P02','Should closed cases appear in a separate past-cases list?','The list would show reference/status and permitted messages, appeals and released certificates, not unlock original closed questionnaire/evidence.'],
  ['P03','Should each case have an applicant-facing timeline of key events?','For example submitted, returned, accepted, assigned, hearing update, decision, appeal and closure. Exclude internal notes, votes and deliberations.'],
  ['P04','Should the home page prioritize actions the applicant needs to take?','For example complete a draft, address returned items, respond to an invitation or read a new request.'],
  ['P05','Should an applicant see a clear “case is closed” explanation before the appeal option?','Explain that an appeal is a new-information submission, not ordinary editing of the original case.']
 ]],
 ['applications','Applications & corrections','Turn confirmed application rules into portal behavior.',[
  ['P06','Should a draft show a section checklist of missing required answers and documents?','The USD 250 fee remains disclosed before starting and payment stays at the completed-application end.'],
  ['P07','Should the applicant see a full review of their answers and attachments before signing and paying?','This reviews only their own submission; neither spouse’s answers overwrite the other’s.'],
  ['P08','Should returned applications open directly to the reviewer’s correction instructions and relevant form areas?','Keep original answers/history; do not add another filing fee or require a new signature for corrections.'],
  ['P09','Should an applicant’s post-submission correction to one field become an explicit Save action for that field or section?','Use Other to prefer automatic saving. No reason or re-signing is required, and every committed change is retained.'],
  ['P10','Should draft-expiry warnings also appear inside the portal?','The existing 180-day inactivity expiry and seven-day email warning remain; this asks only about an on-screen warning.']
 ]],
 ['requests','Requests for information','How council requests are presented to the applicant.',[
  ['P11','Should a council request for information appear as a separate actionable item with an applicant response area?','The current message history remains authoritative; this would link responses to the request without creating a private chat feature.'],
  ['P12','Should the applicant be able to add documents directly when responding to a request while the case is open?','Uploads stay inside the portal with existing ownership, limits and history; no email attachment submissions.'],
  ['P13','Should council mark a request resolved after reviewing the response?','If No, the exchange can remain ordinary recorded correspondence with no separate request status.'],
  ['P14','Should applicants be able to send a new case message from the portal, in addition to replying to existing case emails?','This would be recorded case correspondence, not live chat. The sender cannot contact the other applicant or expose their own private data to them.'],
  ['P15','Should portal replies and email replies appear in one private conversation history for that applicant?','Use Other if you want portal read-only correspondence and email-only replies. Staff sees the authorized case communication record.']
 ]],
 ['files','Documents & fees','Convenience within the approved access boundaries.',[
  ['P16','Should the document area group the applicant’s latest files by document category?','Applicants still cannot browse older attachment versions or the other party’s files.'],
  ['P17','Should a replacement upload clearly show which existing document it will replace?','Preserve the original in council-only version history; ordinary replacement is available only in the permitted open proceeding.'],
  ['P18','Should the portal show the applicant’s own payment/waiver status and receipt for each filing?','Do not show the other party’s payments or internal waiver administration; no applicant waiver-request option.'],
  ['P19','Should applicants be able to download their individual payment receipt?','This is a receipt, not a case-record export. Use Other if the provider receipt alone is sufficient.']
 ]],
 ['hearings','Appointments & notifications','Applicant visibility without council-session access.',[
  ['P20','Should upcoming testimony invitations appear in a dedicated appointments area?','Date, time, instructions and Confirm/Reject are already agreed; no applicant rescheduling and no private council agenda access.'],
  ['P21','Should the portal show a map/address or remote attendance link supplied by staff for testimony?','Only for that applicant’s own appointment. CTM is not required to host video calls merely by storing a link.'],
  ['P22','Should the applicant receive an automatic reminder one day before their testimony appointment?','Use Other to specify a different interval, channels or no reminders. Initial/change invitations already use portal/email.'],
  ['P23','Should notifications distinguish unread from read and allow the applicant to mark them read?','This affects the applicant’s inbox state only, not proof of legal service or changes to case records.']
 ]],
 ['appeals','Appeals & certificates','Portal actions after a decision.',[
  ['P24','Should the appeal page display the applicant’s appeal statement, additions, fee status and council Accept/Decline result together?','Only their own appeal information; the other applicant’s appeal evidence remains private.'],
  ['P25','Should adding appeal information display a chronological list of the applicant’s prior supplements?','These are retained additions, not edits to the originally submitted appeal statement.'],
  ['P26','Should withdrawal require a short confirmation screen before taking effect?','No approval or withdrawal reason is added. The screen explains the applicable case/appeal effect and nonrefundable fee.'],
  ['P27','Should a decree notice show that the certificate is not yet available until staff releases it?','No download link or certificate preview before explicit release; the detailed handover process remains a separate discussion.'],
  ['P28','Should a released certificate display its decree ID, language and release date next to View / Download?','Access remains exact-recipient/current-released-version only; earlier certificate versions stay hidden.']
 ]],
 ['profile','Profile & preferences','No new authentication policy.',[
  ['P29','Should applicants manage their notification language and verified email change inside an account settings page?','English/Arabic preference and verified email changes are already approved; this asks where those actions live.'],
  ['P30','Should updating account contact information leave submitted case answers unchanged until the applicant explicitly corrects the permitted case fields?','Keep account data and signed submission assertions distinct; no retroactive rewrite of past applications.']
 ]]
]},
{slug:'case-interview',title:'Assigned member interview workflow',version:'ctm-case-interview-review-v1',intro:'Design how the assigned case owner interviews people, gathers information using templates, records audio and obtains transcripts. Choose Yes / No / Other and explain alternatives in the text area.',baseline:'Requested scope: template-based interviewing with in-application recording and automatic transcription. Prototype basis: admin-case-intake.html (person interviewed, interviewer, method, date/time, location, duration, notes and attachments). Existing council testimony is a separate event: do not silently apply its permissions or AI-provider approval to every private interview. Original audio, versions and actual authorship must be preserved.',sections:[
 ['scope','Interview scope & participants','Who can be interviewed and by whom.',[
  ['C01','Should this interview workflow be separate from applicant testimony given during a council session?','Both link to the case/proceeding, but a case-owner interview is not automatically a council hearing or agenda item.'],
  ['C02','Should only the assigned council member conduct and author these case-investigation interviews?','Use Other to name additional permitted interviewers. Prototype selection of any council member is not yet an approved permission.'],
  ['C03','May admin or secretary enter or upload an interview record on the assigned member’s behalf?','Preserve the actual interviewer separately from the person entering the data. This does not authorize applicant appeal supplements on their behalf.'],
  ['C04','Should the interviewee list include either applicant, their priest or Father of Confession, and adult witnesses?','These types appear in the prototype. No child interviews or child accounts are proposed.'],
  ['C05','Should a witness or priest be recorded as a case-linked contact without creating a login account?','Store only the identity/contact details needed for the interview and preserve their relationship to the case.'],
  ['C06','Should both applicants always be interviewed separately?','Use Other if the assigned member may sometimes conduct a joint interview; existing council testimony still never places both applicants together.']
 ]],
 ['templates','Interview templates','Reusable questions without rewriting history.',[
  ['C07','Should admin or secretary create and version the interview templates?','Each interview retains the exact template version used; publishing changes must not rewrite completed interviews.'],
  ['C08','Should templates vary by interviewee type, such as applicant, spouse, priest or witness?','Use Other to prefer one common template or describe a simpler structure.'],
  ['C09','Should interview templates support English and Arabic versions of the same questions?','Keep original answers in the language spoken/entered rather than replacing them with translations.'],
  ['C10','Should the assigned member be able to add case-specific follow-up questions within an interview?','Keep the published template unchanged and record which questions were added for this case.'],
  ['C11','Should the template allow both structured fields and rich-text answers?','For example dates or Yes/No plus detailed narrative. Use Other to prefer narrative-only interview notes.'],
  ['C12','Should an interview show the selected applicant’s submitted answers beside the template for reference?','The interviewer may compare assertions but must not overwrite them through the interview record. Other party information remains separately attributed.']
 ]],
 ['process','Conducting & saving the interview','Template-led information gathering.',[
  ['C13','Should the interview preserve the prototype metadata: person, actual interviewer, method, date/time, location and duration?','Methods currently shown are in person, phone and virtual. Other may refine the list or fields.'],
  ['C14','Should the assigned member be able to save an unfinished interview and resume later?','This is an investigation-record draft, separate from the no-draft Send action for a council-hearing update.'],
  ['C15','Should each completed interview be an individual entry in a chronological case-interview log?','Allow multiple interviews of the same person without overwriting earlier interviews.'],
  ['C16','Should evidence discussed during an interview be linked to specific questions or notes?','Reuse retained file versions. Do not duplicate source files or make the interviewee the owner of someone else’s evidence.'],
  ['C17','Should the assigned member have a separate internal observations/recommendations area alongside the interviewee’s answers?','Do not blend council conclusions into the interviewee’s recorded statements.']
 ]],
 ['recording','Audio recording','Recording inside the template workflow.',[
  ['C18','Should recording be optional for ordinary case-owner interviews?','Recording capability is requested, but mandatory versus optional is undecided. Council-session applicant testimony remains mandatory audio recording.'],
  ['C19','Should the interviewer record that the interviewee was informed about recording before audio capture starts?','This asks for a workflow record; exact institutional wording/policy remains to be supplied, not invented here.'],
  ['C20','Should an interview support both microphone recording in CTM and uploading an existing audio file?','Open-source recorder requirement is already noted. Original bytes and the actual recorder/uploader remain recorded.'],
  ['C21','Should interview recording support pause/resume and recovery of captured portions after an interruption?','Recovery must preserve the actual timeline and gaps, without inventing missing audio.'],
  ['C22','Should the no-fixed-duration/file-size-cap rule for council testimony also apply to these investigation interview recordings?','This extends the testimony exception to interview recordings. Ordinary applicant audio attachments would retain their existing limit.'],
  ['C23','Should the interviewer be able to mark the current template question while recording so transcript segments can link to it?','Markers guide navigation; they do not establish that every spoken statement is an answer to that question.']
 ]],
 ['transcription','Transcription & translation','Keep generated text separate from reviewed facts.',[
  ['C24','Should saving an interview recording automatically queue transcription through the approved-for-interviews AI API?','Testimony AI processing is already requested; this question explicitly extends external audio processing to case-owner interviews. Provider selection comes later.'],
  ['C25','Should interview transcripts use the same language behavior as testimony: original transcript, English/Arabic translation, and all three versions for mixed speech?','Include timestamps and speaker labels; preserve the source recording and original AI output.'],
  ['C26','Should AI suggest which transcript passages answer each template question, for the assigned member to review?','Suggestions never become verified interview answers automatically and must link back to timestamped source audio.'],
  ['C27','Should the assigned member review and correct generated interview text before other council members can read it?','Use Other if admin/secretary should review instead or also. Every correction retains author/time and earlier versions.'],
  ['C28','Should manually typed interview answers remain separate from the AI transcript even after review?','This avoids presenting edited summaries as verbatim testimony; both can reference the original audio.']
 ]],
 ['access','Access, history & case use','Who sees working and completed interview material.',[
  ['C29','Should unfinished interview records be visible only to the assigned member, admin and secretary?','Use Other if all council should see them immediately or if drafts should be author-only. Applicant drafts remain governed separately.'],
  ['C30','Should completed interviews, audio and reviewed transcripts be visible to all authorized council members?','No applicant access is inferred. Use Other to specify a narrower audience.'],
  ['C31','Should interview records, recordings and transcripts remain council-only, with any applicant-facing request sent through normal case messages?','This keeps internal investigation material separate from the applicant’s own form history.'],
  ['C32','Should the original interviewer be the only person able to revise their completed interview narrative while the case is open?','Use Other to allow admin/secretary corrections or the newly assigned member. Preserve every version; closure freezes substantive source records.'],
  ['C33','After reassignment, should the new assigned member add follow-up interviews rather than rewrite the earlier interviewer’s narrative?','Earlier authorship and recordings remain intact; they may be read under the approved council scope.'],
  ['C34','Should the assigned member choose reviewed interview findings for the case-hearing briefing instead of automatically sharing the entire transcript?','Council source material remains accessible under its permission rules. No automatic decree content or applicant disclosure is implied.']
 ]]
]}
];

let engine=fs.readFileSync(path.join(root,'questionnaire.js'),'utf8');
engine=engine.slice(engine.indexOf('const questions ='));
engine=engine.replace("value==='yes'||value==='no'||value===null", "value==='yes'||value==='no'||value==='other'||value===null");
engine=engine.replace("['yes','no']", "['yes','no','other']");
engine=engine.replace("value==='yes'?'Yes':'No'", "value==='yes'?'Yes':value==='no'?'No':'Other'");
engine=engine.replace("()=>changed(id,'answer',value)", "()=>{changed(id,'answer',value);if(value==='other')document.getElementById(`note-${id}`).focus();}");
engine=engine.replace("'Clarification / preferred alternative'", "'Other / clarification'");
engine=engine.replace("'Optional — explain a No, qualify a Yes, or leave a question for discussion.'", "'For Other, describe your preferred workflow here. You can also clarify Yes or No.'");
engine=engine.replace("'CTM architecture questionnaire'", 'REVIEW_TITLE');
engine=engine.replace('clarifications qualify Yes/No choices.', 'clarifications qualify Yes/No/Other choices.');
engine=engine.replace('CTM-architecture-answers-${', 'CTM-${REVIEW_SLUG}-answers-${');
const css=fs.readFileSync(path.join(root,'questionnaire.css'),'utf8')+'\n.choices{flex-wrap:wrap}.baseline{padding:16px 0;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}';
const baseHtml=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const spec of specs){
 const js=`'use strict';\nconst VERSION=${JSON.stringify(spec.version)};\nconst STORAGE_KEY=VERSION;\nconst REVIEW_TITLE=${JSON.stringify(spec.title)};\nconst REVIEW_SLUG=${JSON.stringify(spec.slug)};\nconst sections=${JSON.stringify(spec.sections,null,2)};\n${engine}`;
 new vm.Script(js);
 const ctx=vm.createContext({setTimeout,clearTimeout});
 vm.runInContext(js.split('try{const stored=')[0],ctx);
 const run=code=>vm.runInContext(code,ctx);
 const count=run('questions.length');
 assert.equal(run('new Set(questions.map(q=>q.id)).size'),count);
 assert(run('payload().answers.every(a=>a.answer===null)'));
 run('state.answers[questions[0].id]={answer:"other",clarification:"Custom workflow — العربية <script>text</script>"};');
 ctx.exported=JSON.parse(run('JSON.stringify(payload())'));
 run('state=normalize(exported)');
 assert.equal(run('state.answers[questions[0].id].answer'),'other');
 assert.match(run('chatText()'),/OTHER/);
 assert.throws(()=>run('normalize({questionnaireVersion:"wrong",answers:[]})'));
 const opposite=spec===specs[0]?specs[1]:specs[0];
 ctx.wrong={...ctx.exported,questionnaireVersion:opposite.version};
 assert.throws(()=>run('normalize(wrong)'));
 const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 let html=baseHtml
  .replace('<title>CTM · Architecture decisions</title>',`<title>CTM · ${escape(spec.title)}</title>`)
  .replace('<link rel="stylesheet" href="questionnaire.css">',()=>`<style>\n${css}\n</style>`)
  .replace('<script src="questionnaire.js" defer></script>','')
  .replace('CTM / Architecture review / 20 October 2026',`CTM / ${escape(spec.title)} / Decision worksheet`)
  .replace('<h1>The remaining decisions.</h1>',`<h1>${escape(spec.title)}.</h1>`)
  .replace(/<p class="intro">[\s\S]*?<\/p>/,()=>`<p class="intro">${escape(spec.intro)}</p><p class="baseline">${escape(spec.baseline)}</p>`)
  .replace('applicant-portal design, infrastructure and provider selection are reserved for later.', 'these worksheet answers will be reviewed before they become architecture requirements. No CTM feature is being built here.')
  .replace('For a No answer, use the clarification box to describe your preferred rule.', 'For Other, describe your preferred workflow in its text area. Clarifications may also qualify Yes or No.')
  .replace('Enable it or use the companion questions.md file.',`Enable it or use the companion ${spec.slug}-questions.md file.`)
  .replace('</body>',()=>`<script>\n${js}\n</script>\n</body>`);
 assert(!/(?:src|href)="https?:/i.test(html));
 fs.writeFileSync(path.join(root,`${spec.slug}-questionnaire.html`),html);
 fs.writeFileSync(path.join(root,`${spec.slug}-questions.json`),JSON.stringify({version:spec.version,title:spec.title,baseline:spec.baseline,sections:spec.sections},null,2));
 let md=`# ${spec.title}\n\n${spec.baseline}\n\n${count} questions. Each response: Yes / No / Other, plus text. No preselected answers.\n\n`;
 for(const [,title,description,rows]of spec.sections){md+=`## ${title}\n\n${description}\n\n`;for(const[id,q,context]of rows)md+=`### ${id}. ${q}\n\n${context}\n\n- [ ] Yes\n- [ ] No\n- [ ] Other\n\nOther / clarification:\n\n`;}
 fs.writeFileSync(path.join(root,`${spec.slug}-questions.md`),md);
 console.log(`PASS: ${spec.slug}: ${count} unique unanswered questions; Other + Unicode JSON round-trip; copy text; wrong-worksheet import rejected; standalone HTML generated.`);
}
