'use strict';
// Review proposals only. No answer is preselected or applied to CTM automatically.
const VERSION = 'ctm-architecture-review-2026-10-20-v1';
const STORAGE_KEY = VERSION;
const sections = [
 ['linking','Independent applications & case linking','Resolve how two separate filings become one shared case.',[
  ['L01','If two matching applications already have different case numbers, should the first-created case number remain the shared case number?','Keep the other number as a permanent historical reference pointing to the retained case; preserve both submissions and payments.'],
  ['L02','Should CTM check for an existing matching marriage before allocating a new case number at submission?','Use the confirmed exact marriage-date plus both-birth-dates rule. Recheck when submission commits so simultaneous filings cannot create duplicate shared cases.'],
  ['L03','If the exact dates match more than one existing marriage record, should automatic linking pause for admin or secretary review?','This covers exceptional collisions and historical duplicates. No random choice between matching cases.'],
  ['L04','If a spouse birth date is unknown, should automatic linking remain unavailable until admin or secretary verifies the case association?','The applicant can still submit using the approved Unknown allowances. This does not make a missing date match another missing date.'],
  ['L05','Should later changes to marriage date or birth dates leave an established case link unchanged unless admin or secretary explicitly corrects the association?','Preserve both source answers and the association history; do not silently move a submitted application to another case.'],
  ['L06','If applications were linked to the wrong case, may admin or secretary correct the association while preserving every original number, submission, payment and audit event?','This is a controlled correction, not deletion or automatic merging of two people. Describe any additional approval you require.'],
  ['L07','When matching submissions have the same two birth dates, should ambiguous applicant-versus-spouse identity require staff review before activating access?','A marriage match identifies the shared case; it must not assign one applicant the other person’s submissions. This matters especially if both spouses share a birth date.']
 ]],
 ['onboarding','Adding the other party','Keep registration simple without exposing either applicant’s information.',[
  ['O01','Should adding an unregistered second party send an email asking them to register and verify that same email?','The confirmed pending case association activates after registration and verification; no separate Accept Invitation step.'],
  ['O02','May admin or secretary correct or cancel a pending second-party email association before it activates?','Keep the original entry and changes in audit history. A cancelled or replaced address must not later activate that old association.'],
  ['O03','Once an account is linked, should changing that account’s email keep its case connections unchanged?','The new address still requires verification under the confirmed account rules. This avoids treating an email change as a new person.'],
  ['O04','After the second party is linked, should they complete their own regular application if they wish to file a petition?','Each actual filer pays USD 250; merely joining/responding does not itself incur a filing fee. Portal layout and detailed experience remain for later.']
 ]],
 ['intake','Application review & lifecycle','Only remaining data consequences; no new review steps.',[
  ['I01','Should returning an incomplete application immediately send its correction instructions privately through the portal and email?','The same case number, no second fee, required reviewer explanation and preserved submissions are already confirmed.'],
  ['I02','Should resubmission place the application back in the completeness-review queue and notify admin and secretary?','This does not allocate a case number or charge again.'],
  ['I03','Should the first accepted application allow the shared case to reach the assignment agenda even if the other party’s application is still being completed or returned?','Keep the second application’s review state separate from the shared case’s assignment state.'],
  ['I04','If a spouse already has a different open case, should adding/linking them to this case pause for admin or secretary review?','Always preserve the one-open-case-per-applicant rule. No override or silent closure of the other case.']
 ]],
 ['decrees','Decrees & party entitlement','Clarify recipient rules and later numbering; signing/release rules are already settled.',[
  ['D01','For Declaration of Nullity with permission to remarry granted, should both parties be entitled to the decree certificate?','They still need explicit admin/secretary release before seeing it. Answer No and explain if entitlement varies.'],
  ['D02','For conditional permission to remarry, should the decision explicitly identify the entitled party or parties and state the conditions?','Do not infer certificate entitlement from the word conditional alone.'],
  ['D03','Should a conditional decree be issuable and close the case while its stated conditions remain requirements for future remarriage?','This asks whether CTM needs to track fulfilment before issuance. It does not change the separate future marriage ecosystem.'],
  ['D04','Should later appeal decrees use A2, A3 and so on for successive appeal proceedings that produce a decree?','A1 is already confirmed for the first appeal decree. Two applicants’ appeals heard together are not two numbering rounds.'],
  ['D05','After a new appeal decree is issued, should the earlier decree stay accessible until admin or secretary explicitly changes its release access?','Appeal submission alone already leaves access unchanged. This asks specifically about the later new decree.'],
  ['D06','Should signed decision notices, when required by the institution, use separate templates from decree certificates?','If notices never need a signature, choose No and say so. This does not add a decree to Petition Denied.'],
  ['D07','Should a physical signature date be recorded separately from the later scan-upload and issuance timestamps?','The actual uploader must not be represented as the signer; no invented historical signature dates.']
 ]],
 ['appeals','Appeal edge cases','The approved appeals workflow stays intact.',[
  ['A01','If another case is open for an applicant, should appeal acceptance be blocked until that conflict is resolved by admin or secretary?','Reopening can never produce two open cases for the same person. Do not silently close the newer case or discard the appeal.'],
  ['A02','If one applicant’s appeal reopens the case while the other has an unfinished appeal draft, should submission of that draft pause until the case is closed again?','Keep the existing draft; do not charge for a submission that cannot proceed. Clarify if it should instead become information in the reopened case.'],
  ['A03','After council declines an appeal, should the applicant be able to file another appeal supported by new information, even if no new case closure occurred?','Repeat appeals after later closure are confirmed. This covers a decline that never reopened the case.'],
  ['A04','After an applicant withdraws a pending appeal, may they file another appeal with a new USD 250 fee while the original case remains closed?','Preserve the withdrawn application/payment. This is a new filing, not restoring or refunding the old one.']
 ]],
 ['historical','Historical cases','Apply the approved missing-data and fee exemptions.',[
  ['H01','May admin save historical entries as work in progress before publishing them as council-visible case records?','These are staff data-entry records, not applicant drafts. Choose No if each save should be council-visible immediately.'],
  ['H02','Should admin explicitly confirm whether a historical case is open or closed when finalizing its entry?','No invented dates or decisions for missing historical details; known open cases still consume the open-case claim.'],
  ['H03','Should an original historical decree number be preserved instead of replacing it with the new DCR format?','The historical case and applicant identifiers already retain original values where available.'],
  ['H04','Should an uploaded historical signed decree require the same explicit release before the applicant can access it?','Linking a verified account to historical records must not automatically expose a certificate.'],
  ['H05','May admin or secretary fix historical transcription mistakes after finalization, preserving the original entered value and every correction?','This is a proposed narrow data-entry correction exception, not permission to change a historical ruling or its signed document.']
 ]],
 ['messages','Messages & templates','Use the existing case communication record.',[
  ['M01','May admin or secretary edit the English and Arabic system-message templates, preserving every version and the exact text previously sent?','Includes hearing updates, invitations, appeal notices and certificate availability. No retroactive changes to sent messages.'],
  ['M02','Should a failed email delivery be visible to admin and secretary so they can correct the contact issue or retry it?','Keep the portal message and delivery history; a failed email must not undo a committed case action.'],
  ['M03','Should the applicant’s assigned-member change notification go through both the portal and email?','Applicants seeing the assigned member name and receiving a change notification are confirmed; specify both channels here.']
 ]],
 ['testimony','Testimony & audio','Keep the original recording and council-only transcripts.',[
  ['T01','For testimony larger than 100 MB, should CTM support consecutive recording parts, each within the 100 MB limit?','One testimony event can have multiple ordered audio files and a continuous transcript timeline. No loss of previously recorded parts.'],
  ['T02','When testimony is rescheduled, should the previous Confirm/Reject response remain in history and a fresh response be requested for the changed appointment?','The affected applicant already receives the updated private portal/email invitation.'],
  ['T03','May admin or secretary correct AI speaker labels and map them to the actual applicant or council member, retaining the AI original and change history?','Timestamps and labels are already required. This is attribution correction, not voice-based identity proof.'],
  ['T04','If AI transcription or translation fails, should testimony remain usable from its saved audio while admin or secretary can retry processing?','Failure must not erase the recording or fabricate a completed transcript.'],
  ['T05','Should admin or secretary be able to review the AI transcript and translation before those generated texts appear to other council members?','Source audio remains council-only as agreed. Choose No for immediate council access clearly marked AI-generated.']
 ]]
];
const questions = sections.flatMap(([sectionId, section, , rows]) => rows.map(([id,question,context]) => ({id,sectionId,section,question,context})));
const byId = new Map(questions.map(q => [q.id,q]));
let state = {answers:{},generalNotes:''};
let storageAvailable = true;
let saveTimer;
const el = id => document.getElementById(id);
function textNode(tag,text,className){const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;}
function validAnswer(value){return value==='yes'||value==='no'||value===null;}
function normalize(input){
 if(!input||input.questionnaireVersion!==VERSION||!Array.isArray(input.answers))throw new Error('Choose an answer file exported by this version of the CTM questionnaire.');
 const next={answers:{},generalNotes:typeof input.generalNotes==='string'?input.generalNotes:''};
 const seen=new Set();
 for(const row of input.answers){
  if(!row||!byId.has(row.id)||seen.has(row.id)||!validAnswer(row.answer)||typeof row.clarification!=='string')throw new Error('The answer file contains an invalid or duplicate question response.');
  seen.add(row.id);next.answers[row.id]={answer:row.answer,clarification:row.clarification};
 }
 return next;
}
function payload(){return {questionnaireVersion:VERSION,exportedAt:new Date().toISOString(),purpose:'Proposed CTM architecture decisions for review; not applied automatically',answers:questions.map(q=>({...q,answer:state.answers[q.id]?.answer??null,clarification:state.answers[q.id]?.clarification??''})),generalNotes:state.generalNotes};}
function save(){
 try{localStorage.setItem(STORAGE_KEY,JSON.stringify(payload()));storageAvailable=true;}catch{storageAvailable=false;}
 el('save-status').textContent=storageAvailable?'Progress saved in this browser':'Browser saving unavailable — download a copy';
}
function update(){
 const answered=questions.filter(q=>state.answers[q.id]?.answer).length;
 el('count').textContent=`${answered} of ${questions.length} answered`;
 el('progress').max=questions.length;el('progress').value=answered;
 for(const q of questions)document.getElementById(`question-${q.id}`).hidden=el('unanswered').checked&&Boolean(state.answers[q.id]?.answer);
 for(const [sid,,,rows] of sections){
  const n=rows.filter(([id])=>state.answers[id]?.answer).length;
  el(`nav-${sid}`).textContent=`${sections.find(s=>s[0]===sid)[1]} · ${n}/${rows.length}`;
 }
}
function changed(id,key,value){state.answers[id]??={answer:null,clarification:''};state.answers[id][key]=value;update();clearTimeout(saveTimer);saveTimer=setTimeout(save,250);}
function render(){
 el('sections').replaceChildren();el('questions').replaceChildren();
 for(const [sid,title,description,rows] of sections){
  const link=textNode('a',title);link.href=`#section-${sid}`;link.id=`nav-${sid}`;el('sections').append(link);
  const section=document.createElement('section');section.id=`section-${sid}`;section.className='question-section';
  const heading=document.createElement('div');heading.className='section-head';heading.append(textNode('h2',title),textNode('p',description));section.append(heading);
  for(const [id,question,context] of rows){
   const field=document.createElement('fieldset');field.id=`question-${id}`;
   const legend=document.createElement('legend');legend.append(textNode('span',id,'qid'),document.createTextNode(question));field.append(legend);
   const detail=textNode('p',context,'detail');detail.id=`context-${id}`;field.append(detail);field.setAttribute('aria-describedby',detail.id);
   const choices=document.createElement('div');choices.className='choices';
   for(const value of ['yes','no']){const label=document.createElement('label');label.className='choice';const radio=document.createElement('input');radio.type='radio';radio.name=id;radio.value=value;radio.checked=state.answers[id]?.answer===value;radio.addEventListener('change',()=>changed(id,'answer',value));label.append(radio,document.createTextNode(value==='yes'?'Yes':'No'));choices.append(label);}
   const clear=textNode('button','Leave unanswered','clear-answer');clear.type='button';clear.setAttribute('aria-label',`Clear answer ${id}`);clear.addEventListener('click',()=>{field.querySelectorAll('input').forEach(r=>r.checked=false);changed(id,'answer',null);});choices.append(clear);field.append(choices);
   const label=textNode('label','Clarification / preferred alternative','note-label');label.htmlFor=`note-${id}`;
   const note=document.createElement('textarea');note.id=label.htmlFor;note.rows=2;note.value=state.answers[id]?.clarification??'';note.placeholder='Optional — explain a No, qualify a Yes, or leave a question for discussion.';note.addEventListener('input',()=>changed(id,'clarification',note.value));field.append(label,note);section.append(field);
  }
  el('questions').append(section);
 }
 el('general-notes').value=state.generalNotes;update();
}
function chatText(){
 const lines=['CTM architecture questionnaire',`Version: ${VERSION}`,'Answers are for reconciliation; clarifications qualify Yes/No choices.',''];
 for(const q of questions){const a=state.answers[q.id];if(!a?.answer&&!a?.clarification)continue;lines.push(`${q.id} — ${a.answer?a.answer.toUpperCase():'UNDECIDED'}`,q.question);if(a.clarification)lines.push(`Clarification: ${a.clarification}`);lines.push('');}
 if(state.generalNotes)lines.push('GENERAL NOTES',state.generalNotes);
 lines.push(`Answered: ${questions.filter(q=>state.answers[q.id]?.answer).length}/${questions.length}. Unanswered questions remain unresolved.`);return lines.join('\n');
}
try{const stored=localStorage.getItem(STORAGE_KEY);if(stored)state=normalize(JSON.parse(stored));}catch{storageAvailable=false;}
render();
el('save-status').textContent=storageAvailable?'Ready — changes save locally':'Browser saving unavailable — download a copy';
el('unanswered').addEventListener('change',update);
el('general-notes').addEventListener('input',()=>{state.generalNotes=el('general-notes').value;clearTimeout(saveTimer);saveTimer=setTimeout(save,250);});
el('download').addEventListener('click',()=>{
 save();const blob=new Blob([JSON.stringify(payload(),null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`CTM-architecture-answers-${new Date().toISOString().replace(/[:.]/g,'-')}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);el('action-status').textContent='Answer download requested. Attach the JSON file to our conversation when ready.';
});
el('copy').addEventListener('click',async()=>{
 const value=chatText();el('transfer-text').value=value;
 try{await navigator.clipboard.writeText(value);el('action-status').textContent='Copied. Paste the answers into our conversation.';}
 catch{el('transfer-text').focus();el('transfer-text').select();el('action-status').textContent='Automatic copying is unavailable. The answer text is selected below; press Ctrl+C (or Command+C) and paste it into our conversation.';}
});
el('import').addEventListener('click',()=>el('import-file').click());
el('import-file').addEventListener('change',async()=>{
 const file=el('import-file').files[0];if(!file)return;
 try{if(file.size>5_000_000)throw new Error('Please choose an exported answer JSON file smaller than 5 MB.');const next=normalize(JSON.parse(await file.text()));if((Object.keys(state.answers).length||state.generalNotes)&&!window.confirm('Replace this worksheet’s current answers with the saved file?'))return;state=next;render();save();el('action-status').textContent='Saved answers loaded. You can continue editing.';}
 catch(error){el('action-status').textContent=`Answers were not changed. ${error.message}`;}
 finally{el('import-file').value='';}
});
el('reset').addEventListener('click',()=>{if(!window.confirm('Clear all answers and notes in this browser? Download a copy first if you want to keep them.'))return;clearTimeout(saveTimer);state={answers:{},generalNotes:''};el('transfer-text').value='';render();save();el('action-status').textContent='Worksheet cleared.';});
el('print').addEventListener('click',()=>{el('unanswered').checked=false;update();window.print();});
window.addEventListener('pagehide',save);
