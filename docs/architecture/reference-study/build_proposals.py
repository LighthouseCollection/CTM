"""Curated, source-linked review proposals. Never writes approved CTM policy."""
from pathlib import Path
import json
ROOT=Path(__file__).parent
manifest=json.loads((ROOT/'source-manifest.json').read_text(encoding='utf-8'))
sources={r['id']:r for r in manifest}
APP=[];QUEST=[]
def proposal(target,id,category,nature,destination,status,current,wording,reason,refs,action='Add / adapt'):
    target.append(dict(id=id,category=category,nature=nature,destination=destination,status=status,current=current,proposed=wording,reason=reason,sources=[dict(id=s,locator=l) for s,l in refs],action=action))
def a(*args,**kwargs):proposal(APP,*args,**kwargs)
def q(*args,**kwargs):proposal(QUEST,*args,**kwargs)

# The current-form statements below were checked against public-petition.html and the
# confirmed decision registers. Missing means no dedicated prompt, not unknowable from narrative.
a('AF01','Petition purpose','All initial petitions','Applicant: beginning of petition','Dedicated prompt missing',
 'Section 8 requests canonical grounds in a general Case Summary; no separate requested-outcome control.',
 'What are you asking the council to consider: divorce/dissolution, annulment/declaration of nullity, or clarification of the appropriate type? State the reason for your request.',
 'Establish purpose before the narrative. This is the applicant request, not council approval or an Orthodox eligibility determination.', [('L01','P056'),('L07','P006–013'),('R06','PDF p.7, petition; p.14, statement')])
a('AF02','Petition purpose','All initial petitions','Applicant: statement instructions','Wording replacement',
 'public-petition.html:419–424: “canonical grounds” and “Please provide a detailed account...”',
 'Explain what you are asking for and why. Give the important events in date order, say how you know them, and identify any supporting documents. Distinguish approximate dates from exact dates.',
 'Plain factual guidance is more useful than requiring applicants to know canonical terminology. Typed statement OR PDF/DOCX remains unchanged.', [('L07','P007–012'),('L06','P011–013'),('R05','PDF p.1, introduction')],action='Replace wording')
a('AF03','Petition purpose','All initial petitions','Applicant: statement instructions','Optional narrative organization',
 'One unrestricted Case Summary textarea; no category prompts within it.',
 'Offer these optional narrative headings: request and reasons; relevant facts before marriage; events during marriage; separation and reconciliation efforts; supporting evidence; new or missing information.',
 'Use a writing guide, not a mandatory long Catholic questionnaire. Keep a single statement/upload acceptable.', [('L02','P004–018'),('R02','PDF p.5, seven narrative headings')])
a('AF04','Marriage records','Prior-marriage factual supplement','Applicant: optional repeatable marriage-history block','Dedicated repeatable history missing',
 'Section 7 “Previously Applied for Ecclesiastical Marriage Permit?” records prior applications, not each prior marriage.',
 'Were you previously married to someone else? If yes, for each prior marriage provide the spouse name, ceremony date/place, how it ended and the relevant civil or church decision reference, if known.',
 'A prior marriage and a prior tribunal application are different records. Do not automatically retrieve old case answers or require another open case.', [('L08','P002–034'),('L01','P130–158'),('R08','PDF p.2, q.15')])
a('AF05','Marriage records','Prior-marriage factual supplement','Applicant: other-party history, only if known','Dedicated history missing',
 'Spouse section has identity and current church details, but no prior-marriage repeat.',
 'To your knowledge, was your spouse previously married? If yes, provide the known details of each prior marriage. Unknown or unavailable details may be stated as such.',
 'Mirror relevant factual history without making absent-spouse information a submission blocker or asserting it is verified.', [('L08','P029–034'),('R03','PDF p.7, q.19d')])
a('AF06','Marriage records','Civil/church chronology supplement','Applicant: marriage section','Current ambiguity',
 'public-petition.html:306–323 combines “married outside the Coptic Orthodox Church” with one outside date and one church marriage date.',
 'Did you have more than one ceremony with this spouse? Record each ceremony separately: civil or church, date, place, officiant and certificate reference. Identify which record relates to this petition.',
 'Separate civil and church facts. Do not import Catholic convalidation, dispense with required certificates or change the confirmed matching-date rule.', [('L01','P230–244'),('L03','P007–018'),('R09','PDF pp.1–3, civil/church timeline')])
a('AF07','Marriage records','All petitions where religious history is relevant','Applicant: small optional church-history field','Current-vs-historical distinction missing',
 'public-petition.html:180–192,264–267 collects denomination/parish now; no separate denomination-at-marriage field.',
 'What was each party’s religious affiliation at the time of the church marriage? Record a later change separately, if relevant. Use Unknown for spouse details not known.',
 'Avoid treating current denomination as proof of faith at marriage. No baptismal certificate requirement is reintroduced.', [('L05','P026'),('R04','PDF p.3, religious status at marriage')])
a('AF08','Chronology','All petitions','Applicant: optional short relationship timeline','Dedicated timeline missing',
 'No meeting, courtship or engagement controls in the current petition.',
 'If relevant to your request, give when you first met, began the relationship and became engaged. Approximate dates are acceptable for these background events.',
 'Keep detailed discovery in the interview; avoid forcing exact dates for memories or deriving extra ID matches from these dates.', [('L01','P036–039'),('R06','PDF p.10, chronology')])
a('AF09','Chronology','Marriage breakdown / divorce','Applicant: short narrative prompt','Missing distinction',
 'public-petition.html:347 has Date of Separation; no separate first-serious-problem prompt.',
 'When did the difficulties relevant to this petition first become apparent? State whether this was before or after the church marriage, and explain briefly.',
 'Distinguishes onset, discovery and final separation rather than assuming all are the same date.', [('L01','P048'),('L07','P159–165'),('R05','PDF p.4, married life')])
a('AF10','Chronology','Marriage breakdown / divorce','Applicant: optional separation entries','Single date only',
 'Current separation area has one date, while temporary separations can be described only in the general summary.',
 'Were there earlier periods of separation before the final separation? For each relevant period record approximate dates, reason and whether you resumed living together.',
 'A repeatable factual timeline supports later review without creating new cases or requiring a detailed biography.', [('L02','P015'),('L01','P328–332'),('R13','PDF p.3, temporary separations')])
a('AF11','Chronology','All new petitions requiring final civil decree','Applicant: existing civil-divorce question','Wording replacement only',
 'public-petition.html:353 “Civil Divorce Filed?”; confirmed CTM policy already requires finalized civil decree before submission.',
 'Has a final civil divorce decree been issued? Provide its date, court and case number, and upload the final decree.',
 'Align wording with the already-approved final-decree requirement; do not introduce extra civil process statuses.', [('R08','PDF p.2, q.14'),('L05','P061–062')],action='Replace wording')
a('AF12','Conditional factual prompts','Misrepresentation / concealment before marriage','Applicant: only when this ground selected','Ground approved; factual subprompt missing',
 'The approved grounds include concealment; prototype only has a general Case Summary.',
 'What important fact do you say was misrepresented or not disclosed before marriage? What were you told, when did you discover the difference, and what supports your account?',
 'Ask for an allegation and its basis, not a presumed finding that the spouse lied.', [('L01','P283–302'),('R03','PDF p.8, q.29'),('R10','PDF p.10, J')])
a('AF13','Conditional factual prompts','Possible annulment inquiry; not a new automatic ground','Applicant: short optional screen or move to interview via Other','Not a dedicated question',
 'No explicit prompt about pressure at the decision to marry.',
 'Did pressure, threats or circumstances affect your freedom to decide to marry? If this is relevant to your request, explain who or what was involved and when.',
 'A neutral factual screen only. Whether this affects an Orthodox decision is for the institution; no imported Catholic ground.', [('L02','P012'),('R04','PDF p.7, q.27–29')])
a('AF14','Conditional factual prompts','Annulment-related factual discovery','Applicant: optional short prompt or interview-only via Other','No dedicated prompt',
 'General summary can contain this, but there is no direct question.',
 'Before the marriage, was there an important agreement, promise or condition that you say was not disclosed or later proved different? Explain the fact and its importance to your decision.',
 'Capture a concrete factual concern without importing a Catholic consent classification or diagnosing incapacity.', [('L07','P078'),('R03','PDF pp.9–10, q.32'),('R05','PDF p.3, q.16')])
a('AF15','Evidence presentation','All petitions','Applicant: attachment explanation next to each relevant item','Evidence explanation missing',
 'Upload zones provide document categories; no general field explains which fact an evidence item supports.',
 'For additional evidence, briefly state what it shows and which part of your statement it relates to.',
 'Keep correct-location attachments and the confirmed filename convention. This adds evidence meaning, not manual file acceptance.', [('L06','P012'),('L07','P151'),('R06','PDF p.3, supporting reports')])
a('AF16','Evidence presentation','All petitions','Applicant: narrative/source cue','No explicit distinction',
 'The general Case Summary does not distinguish personal knowledge from information supplied by another person.',
 'When describing an event, say whether you personally experienced it, saw a document, or learned it from another person. If you do not know, say so.',
 'Improve factual attribution without requiring witness accounts or making uncertain spouse details mandatory.', [('L06','P011–013'),('R14','PDF pp.6–7, q.19–25')])
a('AF17','Evidence presentation','All petitions','Applicant: information instructions','Optional help wording',
 'General instruction: “Please provide a detailed account...”',
 'Give specific events and examples relevant to your request. A concise, factual account is more useful than general labels about someone’s character.',
 'Adopts the samples’ specificity while omitting blame-based or diagnostic labels; not a new legal declaration.', [('L07','P007–012'),('L06','P013')],action='Replace help wording')
a('AF18','Question labels','All petitions','Applicant: existing church fields','Wording clarification',
 '“Denomination”, “Diocese”, “Name of Bishop of the Diocese”, “Father of Confession”.',
 'Keep current church membership together and label it “Current church membership”. Label any accepted historical field “At the time of marriage” separately.',
 'Prevents historical/current answers being confused. Existing spouse parish/confessor additions are already approved, not new questions.', [('R02','PDF p.3'),('L01','P025–026')],action='Replace section help')
a('AF19','Question labels','All petitions','Applicant: marriage label','Wording clarification',
 'public-petition.html:316 “Date of Church Marriage”.',
 'Date of the church marriage concerned in this petition.',
 'Clarifies which event is being dated when civil and church ceremonies differ; retain exact-date matching rule.', [('L03','P007–018'),('R09','PDF p.1, ceremony distinction')],action='Replace label')
a('AF20','Question labels','All petitions','Applicant: reconciliation question','Wording clarification',
 'public-petition.html:382 “Clergy Counseling / Reconciliation Attempted?”',
 'Were any attempts at reconciliation made with the help of a priest? If yes, provide the priest’s name.',
 'Keeps the confirmed priest-name-only application requirement. Detailed counseling questions belong in a separate optional interview module.', [('L02','P015'),('R06','PDF p.16, q.21')],action='Replace wording')
a('AF21','Question labels','All petitions','Applicant: prior application label','Wording clarification',
 'public-petition.html:393 “Previously Applied for Ecclesiastical Marriage Permit?”',
 'Have you previously submitted a church application concerning this marriage? List each application, its date, council or diocese, and outcome.',
 'Avoids confusing a prior case/application with the separate prior-marriages proposal. Retain multiple prior applications already agreed.', [('R08','PDF p.2, q.15'),('R04','PDF p.8, prior tribunal')],action='Replace wording')
a('AF22','Instructions','All petitions','Applicant: introductory instructions','Proposed explanatory wording',
 'No separately verified CTM no-guarantee statement is assumed in this comparison.',
 'Submitting a petition does not guarantee a particular decision or completion date. The council will consider the information and may request further details.',
 'Useful expectation-setting; do not copy Catholic timing promises, witness quotas, fees or future-marriage prohibitions as CTM rules.', [('R01','PDF p.3, policy'),('R02','PDF p.1, directions')])
a('AF23','Institution-review facts','Possible annulment factual inquiry','Applicant: optional screen, or interview via Other','No dedicated relationship-of-parties question',
 'The current application does not ask whether the spouses are related by blood or adoption.',
 'To your knowledge, are you and your spouse related by blood or adoption? If yes, describe the relationship; if you do not know, say Unknown.',
 'Offer the factual question for Orthodox institutional review. Do not import Catholic degrees of kinship, dispensation rules or an automatic invalidity decision.', [('R04','PDF p.6, q.17–20'),('L04','P048–051')])
a('AF24','Institution-review facts','All petitions where spouse availability is relevant','Applicant: spouse details, optional screen','No dedicated living/deceased/unknown field',
 'The existing application allows an absent spouse but has no specific living/deceased/unknown question.',
 'To your knowledge, is your spouse living, deceased, or is this unknown? If deceased, provide the date if known.',
 'Do not infer a death-certificate requirement, automatic case closure or a new petition type; those would require separate decisions.', [('R10','PDF p.3, spouse living'),('R11','PDF p.4, spouse living')])

# Question/template review: each decision selects a factual module or a focused wording change.
q('QT01','Common core','All petition interviews','CORE / opening','Preserve existing confirmed opening',
 'OPEN-01/02 in draft v2 already establishes full name and spouse name at every interview/recording.',
 'Keep the identity opening as a reusable block, separate from all substantive questions; repeat it for each interview and newly started recording.',
 'Retain the user-directed opening. No Catholic oath or notarization imported.', [('L06','P014–032'),('R14','PDF p.2, identification')],action='Organize existing content')
q('QT02','Common core','All petition interviews','CORE / requested relief','Draft SEEK-01',
 '“What are you asking the council to grant in this case...”',
 'What outcome are you seeking, and which specific facts do you want the council to consider in support of it?',
 'Puts request before discovery and separates applicant claim from council decision. Keep type options in a staff-guided field.', [('L07','P006–013'),('R06','PDF p.7, petition')],action='Replace wording')
q('QT03','Common core','All petition interviews','CORE / chronology','Draft TIME-01–03',
 'General first-difficulties / what-happened-next prompts.',
 'For each important event, record when it occurred, when you learned about it, and whether the date is exact or approximate.',
 'Occurrence and discovery dates can differ, especially concealment. One event record, not repeated copies of one question.', [('L07','P085–086,159–175'),('L02','P009,014–015')],action='Refine existing questions')
q('QT04','Common core','All petition interviews','CORE / factual knowledge','Draft FACT-02',
 '“What did you personally see, hear or experience, and what did you learn from another source?”',
 'Describe what you personally know. Identify any information you learned from someone else and how you learned it.',
 'Clearer source attribution; do not turn the source into a required witness or share the other applicant’s private submission.', [('L06','P011–013')],action='Replace wording')
q('QT05','Common core','All petition interviews','CORE / evidence','Draft EVID-01–04',
 'Existing evidence questions ask connection and provenance, but as separate broad prompts.',
 'For each disputed fact, identify the supporting item, its date/source if known, what it shows, and any limitations or conflicting information.',
 'Tie evidence to a fact rather than collecting unrelated documents. Keep unknowns and allegations distinct.', [('L06','P012'),('L07','P151')],action='Refine existing questions')
q('QT06','Common core','All petition interviews','CORE / closing','Draft CLOSE-01/02',
 'Two general closing questions.',
 'What relevant fact has not yet been covered, and is anything you said today in need of clarification?',
 'Combine duplicate catch-all prompts into one closing question without a new signature.', [('L07','P087,129,176,215'),('R14','PDF p.12, q.50')],action='Merge equivalent questions')
q('QT07','Before marriage','Possible annulment factual inquiry','NUL / decision to marry','Draft begins events without a detailed decision block',
 'Draft SEEK/TIME has general grounds/sequence prompts; no focused courtship decision module.',
 'How did you decide to marry, what did each of you understand you were committing to, and what had you discussed before the wedding?',
 'Factual exploration of that time; no assumption that Catholic nullity criteria determine an Orthodox outcome.', [('L02','P007–012'),('R05','PDF pp.2–3, courtship')])
q('QT08','Before marriage','Possible annulment factual inquiry','NUL / pressure','Draft generic FACT block',
 'Pressure is only mentioned in broad follow-up examples.',
 'Was there pressure affecting the decision to marry? Identify its source, what happened, when, and how it affected the decision.',
 'Avoid yes/no-only screening and avoid treating ordinary family involvement as proven coercion.', [('L07','P062–063,110–111'),('L02','P012')])
q('QT09','Before marriage','Possible annulment factual inquiry','NUL / disclosed doubts','No dedicated focused block',
 'Draft timeline does not specifically ask about doubts discussed before the wedding.',
 'Did you have serious reservations before the wedding? What were they, were they discussed, and what happened next?',
 'Relevant stated facts, not automatic invalidity or a universal requirement to produce witnesses.', [('L07','P066,096–098'),('R14','PDF p.4, q.8')])
q('QT10','Before marriage','Possible annulment factual inquiry','NUL / wedding-day events','No dedicated wedding-day factual block',
 'Draft chronology covers events generally.',
 'Did a specific event at or immediately before the ceremony affect your ability or willingness to proceed? Describe the event and what you remember.',
 'A conditional event question, not a medical diagnosis, broad sexual history or imported canonical test.', [('L07','P103–118'),('R05','PDF p.3, wedding')])
q('QT11','Before marriage','Misrepresentation / concealment','CONCEALMENT / before marriage','Draft pre-marriage follow-up is general',
 'FACT follow-up asks what was represented/not disclosed and discovered later.',
 'What fact was represented or withheld, what did you believe before marriage, when did you learn the difference, and what evidence supports that sequence?',
 'Use a separate claim/evidence block for each alleged concealment; never label it established deception automatically.', [('L01','P283–302'),('R03','PDF p.8, q.29')],action='Refine existing follow-up')
q('QT12','Before marriage','Possible annulment factual inquiry','NUL / pre-marriage agreement','Broad grounds prompt only',
 'Draft no dedicated agreement question.',
 'Was there a specific agreement, promise or condition important to your decision to marry? What was agreed, by whom, when and how was it understood?',
 'Neutral facts only; not wholesale import of Catholic simulation, permanence or procreation checkboxes.', [('L07','P078'),('R03','PDF pp.9–10, q.32')])
q('QT13','Divorce grounds','Infidelity','DIV / infidelity module','Draft general per-ground questions',
 'FACT-01–05 are shared but do not specify infidelity timing/source.',
 'Describe the alleged unfaithfulness, when it occurred, when you learned of it, your source of knowledge and the supporting evidence.',
 'Avoid assuming guilt or requiring identifying details unrelated to the council inquiry.', [('L07','P138–140'),('R14','PDF p.6, q.19–20')])
q('QT14','Divorce grounds','Desertion / abandonment','DIV / abandonment module','Draft short abandonment follow-up',
 'General absence/contact description.',
 'When did the separation begin, what contact or support continued, what efforts were made to communicate or reconcile, and which facts about the absence do you know directly?',
 'Distinguish absence from known intention; do not require the absent spouse’s account or address.', [('L02','P015'),('L07','P166–169')],action='Refine existing follow-up')
q('QT15','Divorce grounds','Abuse','DIV / abuse module','Draft general event questions',
 'No dedicated incident structure.',
 'Describe the relevant incident or pattern, dates or periods, what you experienced directly, and any existing reports or evidence you wish to provide.',
 'Prefer specific acts to character labels. Do not import foreign reporting procedures, demand unnecessary detail or reopen rejected child testimony.', [('L07','P047,151'),('R14','PDF pp.8–9, q.33–34')])
q('QT16','Divorce grounds','Leaving or changing the faith','DIV / faith-change module','Draft general event questions',
 'Current denomination fields do not explain the alleged change and chronology.',
 'What change in religious affiliation or practice is relevant to your request, when did it occur, how do you know, and how did it affect married life?',
 'Claim and chronology only; avoid equating occasional attendance with a formal finding of leaving the faith.', [('L01','P025–026,210–214'),('R14','PDF p.9, q.39')])
q('QT17','Divorce grounds','Addiction','DIV / addiction module','Draft general event questions',
 'No structured onset/discovery/course of alleged addiction.',
 'Describe the behavior you believe is relevant, when it began or became known, its effect on married life, and any help sought that you can factually describe.',
 'Do not diagnose the spouse from a checkbox or require universal medical-record release.', [('L07','P048–049'),('R14','PDF p.9, q.35–37')])
q('QT18','Divorce grounds','All selected grounds','DIV / repeatable factual blocks','Draft per-ground repeat block exists',
 'One shared FACT block repeatable by ground.',
 'Use one factual block for each selected ground, with event date, discovery date, knowledge source and evidence links; show only the relevant approved follow-up prompts.',
 'Organize without duplicating the same fact across six questionnaires or creating new grounds.', [('L01','P118–129,283–302'),('L07','P130–176')],action='Organize existing content')
q('QT19','Context only when relevant','Any petition','CONTEXT / relevant upbringing','No broad biography required',
 'Draft does not require childhood, parents or sibling histories.',
 'Is there a specific earlier experience that directly helps explain a fact relevant to this petition? Describe only that connection.',
 'Adapt common family-background theme into a conditional interview follow-up, not a compulsory lifelong biography.', [('L02','P016–018'),('R05','PDF pp.1–2, family background')])
q('QT20','Context only when relevant','Any petition','CONTEXT / pre-marriage knowledge','No dedicated premarital problem comparison',
 'Draft general events only.',
 'Were the problems described already evident before marriage, or did they arise later? What did each party know at the time?',
 'A frequently repeated temporal distinction. Keep absence of knowledge separate from proof of concealment.', [('L02','P009,014'),('L07','P165'),('R06','PDF p.16, courtship vs married life')])
q('QT21','Context only when relevant','Any petition','CONTEXT / decision-making and responsibilities','No detailed routine-life block',
 'Draft factual chronology does not explore financial/domestic conflict specifically.',
 'If relevant, give a concrete example of how an important financial, household or parenting decision was made and how the disagreement affected the marriage.',
 'Conditional factual example, not a universal inventory of private spending or a civil custody determination.', [('L07','P149–150,156'),('R05','PDF p.4, household responsibilities')])
q('QT22','Context only when relevant','Any petition','CONTEXT / communication','No dedicated communication follow-up',
 'Draft events may not show how issues were raised and addressed.',
 'For a relevant disagreement, what was communicated, how did the other party respond, and what action followed?',
 'Concrete sequence is more useful than judging general communication quality.', [('L07','P152'),('R13','PDF p.7, q.28')])
q('QT23','Context only when relevant','Any petition','CONTEXT / treatment, only relevant facts','No mandatory psychological biography',
 'Draft does not request blanket medical history or release.',
 'Where directly relevant to the stated issue, describe any professional help actually sought, its dates if known, and the facts you are authorized and able to provide.',
 'Keep medical/counseling material conditional and separate from clergy-name-only application field; no automatic third-party contact or records release.', [('L01','P303–327'),('L07','P148,167')])
q('QT24','Separation and reconciliation','Divorce / any relevant petition','SEPARATION / temporary periods','Draft timeline general',
 'No standardized repeated separation/reunion block.',
 'For each relevant temporary separation: when, why, for how long and what led to resuming life together? Then record final separation separately.',
 'Merge repeated source variations into one repeatable block; do not require all dates to be exact.', [('L02','P015'),('L07','P166'),('R05','PDF p.4, separation')])
q('QT25','Separation and reconciliation','Any relevant petition','RECONCILIATION / efforts and outcomes','Draft CONTEXT-01',
 '“What attempts at reconciliation were made, when, and what happened?”',
 'Identify each relevant reconciliation attempt, who participated, approximate date and outcome. Separate what you observed from what you were told.',
 'Retain application priest-name-only requirement; this deeper block is council interview content.', [('L02','P015'),('L07','P167–174')],action='Refine existing wording')
q('QT26','Multiple ceremonies and prior marriages','Civil/church chronology supplement','CEREMONIES / before and after each event','Draft APP-02 general marriage confirmation',
 'No separate interview chronology for two ceremonies.',
 'Identify the civil and church ceremonies separately. What was known or occurring before each ceremony, between them and after the church marriage?',
 'Borrow the useful time separation, not the Catholic convalidation process or its legal effects.', [('L03','P007–018'),('R09','PDF pp.1–3')])
q('QT27','Multiple ceremonies and prior marriages','Prior-marriage factual supplement','HISTORY / earlier unions','No dedicated repeatable prior-marriage interview',
 'Earlier version has no prior-marriage supplement distinct from previous applications.',
 'For each relevant earlier marriage, identify the spouse, dates, ceremony type, how it ended and any existing church/civil decision reference you know.',
 'Document history only; no imported ligamen decision, renewed fee, automatic record-prefill or second open case.', [('L08','P002–034'),('R05','PDF p.2, prior marriages')])
q('QT28','Sensitive or doctrine-dependent','Only if institution approves relevance','Conditional private interview; not application-wide','Not in draft; do not assume required',
 'No required inquiry about ability to consummate or intimate marital difficulties.',
 'Only if directly relevant to the petition and the council asks: is there a specific intimate marital difficulty you wish to explain, including when it arose or became known?',
 'Optional approval of a narrow interview topic, not adoption of Catholic consummation definitions, proof thresholds or a mandatory sexual-history survey.', [('L07','P122–125,153–155')])
q('QT29','Sensitive or doctrine-dependent','Only if institution approves relevance','Conditional private interview; not new ground','Not a new approved ground',
 'CTM already collects children; no blanket questions about intentions regarding children before marriage.',
 'If relevant, what did you and your spouse actually discuss or agree about having children before marriage, and what later changed or became known?',
 'User may reject or narrow this topic. Do not import Catholic procreation exclusions, contraception rules or a new nullity ground.', [('L07','P059–060,137,141'),('L01','P269–282')])
q('QT30','Appeal supplement','Accepted/pending appeal, within approved scope','APPEAL / new information','Appeal form and section already approved',
 'Appeal asks for reason and new information/evidence; interviewer can otherwise repeat original discovery.',
 'Which earlier decision or finding are you challenging, what information is new, when did it become available and which earlier point does it affect?',
 'Use an appeal-only question block, not another full biography. Original proceedings remain read-only and no new deadline is introduced.', [('L06','P012'),('L07','P175')],action='Adapt factual-source structure; CTM appeal policy')
q('QT31','Priest report requested by council','Optional report; not an applicant interview','PRIEST / author and knowledge','New user-requested report concept; not approved form content',
 'Application currently records reconciliation priest names; no standardized priest-report template. Prior general priest/witness interview feature was rejected.',
 'Report author: name and parish; which party or parties you know; length and nature of contact; which periods of the relationship you know directly.',
 'Separate a specifically requested priest report from mandatory witness lists, interviews, logins or case access.', [('R02','PDF p.4, minister comments q.1'),('R14','PDF p.2, q.1–2')])
q('QT32','Priest report requested by council','Optional priest report','PRIEST / observed facts','No current report prompts',
 'No direct-knowledge structure for requested pastoral reports.',
 'Describe relevant facts you personally observed, with dates if known. Label information told to you by a party separately from your direct observations.',
 'The witness samples contribute a source-of-knowledge structure, not a right to view parties’ case material.', [('L06','P011–013'),('R14','PDF pp.6–7, q.19–25')])
q('QT33','Priest report requested by council','Optional priest report','PRIEST / reconciliation','No current report prompts',
 'Applicant reconciliation field asks priest name only.',
 'Describe relevant non-confessional reconciliation assistance you provided, approximate dates and observed outcome. State any limits on what you can report.',
 'Do not request sacramental confession content or imply a blanket authorization to release pastoral/private information.', [('R02','PDF p.4, minister comments'),('R06','PDF p.22, sponsor questions')])
q('QT34','Priest report requested by council','Optional priest report','PRIEST / opinion versus fact','No current report prompts',
 'The Catholic samples sometimes ask clergy to assess sincerity or case viability.',
 'If you offer an observation or recommendation, identify it as your opinion and state the facts on which it is based; do not make the council decision for it.',
 'Prefer evidence-grounded observations to a broad character/sincerity score or copied canonical conclusion.', [('R02','PDF p.4, q.3–5'),('R06','PDF p.22, q.1–3')])
q('QT35','Priest report requested by council','Optional priest report','PRIEST / report authentication','No current report signature workflow',
 'No separate priest report author/date attestation is implemented.',
 'At the end of a requested report, record the author, date and signature or authenticated submission method, preserving the exact submitted version.',
 'Approval chooses the data requirement only. Do not copy Catholic oath/notary/parish-seal rules or create a priest portal without a separate decision.', [('R02','PDF p.4, signature'),('R14','PDF p.12, signature area')])
q('QT36','Template organization','All petition interviews','Routing and reuse','One draft template with common questions and informal ground prompts',
 'Current draft INT-APPLICANT revision 2 is a single document.',
 'Use one common factual core plus only the relevant approved modules: annulment inquiry, selected divorce grounds, multiple ceremonies, prior marriages or appeal; keep a requested priest report as a separate template.',
 'Avoid copying the same questions into every template. Council controls the process/type; applicant selection is not a decree. No Catholic process categories are imported.', [('L02','P004–018'),('L03','P007–018'),('L07','P006–018')],action='Organize/deduplicate; review first')

for name,data in [('application-proposals',APP),('template-proposals',QUEST)]:
    ids=[x['id'] for x in data]
    assert len(ids)==len(set(ids))
    for x in data:
        for ref in x['sources']: assert ref['id'] in sources
    (ROOT/f'{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'source-catalog.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Curated {len(APP)} application proposals and {len(QUEST)} question/template proposals; all source IDs validated.')
