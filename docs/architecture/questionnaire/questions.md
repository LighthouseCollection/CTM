# CTM architecture review questionnaire

39 unresolved scenarios. All choices are proposals; no answer is preselected. Use the HTML worksheet, or write Yes/No and clarification under these stable question IDs. Applicant-portal design and infrastructure/provider choices remain for later.

## Independent applications & case linking

### L01. If two matching applications already have different case numbers, should the first-created case number remain the shared case number?

Keep the other number as a permanent historical reference pointing to the retained case; preserve both submissions and payments.

- [ ] Yes
- [ ] No

Clarification: 

### L02. Should CTM check for an existing matching marriage before allocating a new case number at submission?

Use the confirmed exact marriage-date plus both-birth-dates rule. Recheck when submission commits so simultaneous filings cannot create duplicate shared cases.

- [ ] Yes
- [ ] No

Clarification: 

### L03. If the exact dates match more than one existing marriage record, should automatic linking pause for admin or secretary review?

This covers exceptional collisions and historical duplicates. No random choice between matching cases.

- [ ] Yes
- [ ] No

Clarification: 

### L04. If a spouse birth date is unknown, should automatic linking remain unavailable until admin or secretary verifies the case association?

The applicant can still submit using the approved Unknown allowances. This does not make a missing date match another missing date.

- [ ] Yes
- [ ] No

Clarification: 

### L05. Should later changes to marriage date or birth dates leave an established case link unchanged unless admin or secretary explicitly corrects the association?

Preserve both source answers and the association history; do not silently move a submitted application to another case.

- [ ] Yes
- [ ] No

Clarification: 

### L06. If applications were linked to the wrong case, may admin or secretary correct the association while preserving every original number, submission, payment and audit event?

This is a controlled correction, not deletion or automatic merging of two people. Describe any additional approval you require.

- [ ] Yes
- [ ] No

Clarification: 

### L07. When matching submissions have the same two birth dates, should ambiguous applicant-versus-spouse identity require staff review before activating access?

A marriage match identifies the shared case; it must not assign one applicant the other person’s submissions. This matters especially if both spouses share a birth date.

- [ ] Yes
- [ ] No

Clarification: 

## Adding the other party

### O01. Should adding an unregistered second party send an email asking them to register and verify that same email?

The confirmed pending case association activates after registration and verification; no separate Accept Invitation step.

- [ ] Yes
- [ ] No

Clarification: 

### O02. May admin or secretary correct or cancel a pending second-party email association before it activates?

Keep the original entry and changes in audit history. A cancelled or replaced address must not later activate that old association.

- [ ] Yes
- [ ] No

Clarification: 

### O03. Once an account is linked, should changing that account’s email keep its case connections unchanged?

The new address still requires verification under the confirmed account rules. This avoids treating an email change as a new person.

- [ ] Yes
- [ ] No

Clarification: 

### O04. After the second party is linked, should they complete their own regular application if they wish to file a petition?

Each actual filer pays USD 250; merely joining/responding does not itself incur a filing fee. Portal layout and detailed experience remain for later.

- [ ] Yes
- [ ] No

Clarification: 

## Application review & lifecycle

### I01. Should returning an incomplete application immediately send its correction instructions privately through the portal and email?

The same case number, no second fee, required reviewer explanation and preserved submissions are already confirmed.

- [ ] Yes
- [ ] No

Clarification: 

### I02. Should resubmission place the application back in the completeness-review queue and notify admin and secretary?

This does not allocate a case number or charge again.

- [ ] Yes
- [ ] No

Clarification: 

### I03. Should the first accepted application allow the shared case to reach the assignment agenda even if the other party’s application is still being completed or returned?

Keep the second application’s review state separate from the shared case’s assignment state.

- [ ] Yes
- [ ] No

Clarification: 

### I04. If a spouse already has a different open case, should adding/linking them to this case pause for admin or secretary review?

Always preserve the one-open-case-per-applicant rule. No override or silent closure of the other case.

- [ ] Yes
- [ ] No

Clarification: 

## Decrees & party entitlement

### D01. For Declaration of Nullity with permission to remarry granted, should both parties be entitled to the decree certificate?

They still need explicit admin/secretary release before seeing it. Answer No and explain if entitlement varies.

- [ ] Yes
- [ ] No

Clarification: 

### D02. For conditional permission to remarry, should the decision explicitly identify the entitled party or parties and state the conditions?

Do not infer certificate entitlement from the word conditional alone.

- [ ] Yes
- [ ] No

Clarification: 

### D03. Should a conditional decree be issuable and close the case while its stated conditions remain requirements for future remarriage?

This asks whether CTM needs to track fulfilment before issuance. It does not change the separate future marriage ecosystem.

- [ ] Yes
- [ ] No

Clarification: 

### D04. Should later appeal decrees use A2, A3 and so on for successive appeal proceedings that produce a decree?

A1 is already confirmed for the first appeal decree. Two applicants’ appeals heard together are not two numbering rounds.

- [ ] Yes
- [ ] No

Clarification: 

### D05. After a new appeal decree is issued, should the earlier decree stay accessible until admin or secretary explicitly changes its release access?

Appeal submission alone already leaves access unchanged. This asks specifically about the later new decree.

- [ ] Yes
- [ ] No

Clarification: 

### D06. Should signed decision notices, when required by the institution, use separate templates from decree certificates?

If notices never need a signature, choose No and say so. This does not add a decree to Petition Denied.

- [ ] Yes
- [ ] No

Clarification: 

### D07. Should a physical signature date be recorded separately from the later scan-upload and issuance timestamps?

The actual uploader must not be represented as the signer; no invented historical signature dates.

- [ ] Yes
- [ ] No

Clarification: 

## Appeal edge cases

### A01. If another case is open for an applicant, should appeal acceptance be blocked until that conflict is resolved by admin or secretary?

Reopening can never produce two open cases for the same person. Do not silently close the newer case or discard the appeal.

- [ ] Yes
- [ ] No

Clarification: 

### A02. If one applicant’s appeal reopens the case while the other has an unfinished appeal draft, should submission of that draft pause until the case is closed again?

Keep the existing draft; do not charge for a submission that cannot proceed. Clarify if it should instead become information in the reopened case.

- [ ] Yes
- [ ] No

Clarification: 

### A03. After council declines an appeal, should the applicant be able to file another appeal supported by new information, even if no new case closure occurred?

Repeat appeals after later closure are confirmed. This covers a decline that never reopened the case.

- [ ] Yes
- [ ] No

Clarification: 

### A04. After an applicant withdraws a pending appeal, may they file another appeal with a new USD 250 fee while the original case remains closed?

Preserve the withdrawn application/payment. This is a new filing, not restoring or refunding the old one.

- [ ] Yes
- [ ] No

Clarification: 

## Historical cases

### H01. May admin save historical entries as work in progress before publishing them as council-visible case records?

These are staff data-entry records, not applicant drafts. Choose No if each save should be council-visible immediately.

- [ ] Yes
- [ ] No

Clarification: 

### H02. Should admin explicitly confirm whether a historical case is open or closed when finalizing its entry?

No invented dates or decisions for missing historical details; known open cases still consume the open-case claim.

- [ ] Yes
- [ ] No

Clarification: 

### H03. Should an original historical decree number be preserved instead of replacing it with the new DCR format?

The historical case and applicant identifiers already retain original values where available.

- [ ] Yes
- [ ] No

Clarification: 

### H04. Should an uploaded historical signed decree require the same explicit release before the applicant can access it?

Linking a verified account to historical records must not automatically expose a certificate.

- [ ] Yes
- [ ] No

Clarification: 

### H05. May admin or secretary fix historical transcription mistakes after finalization, preserving the original entered value and every correction?

This is a proposed narrow data-entry correction exception, not permission to change a historical ruling or its signed document.

- [ ] Yes
- [ ] No

Clarification: 

## Messages & templates

### M01. May admin or secretary edit the English and Arabic system-message templates, preserving every version and the exact text previously sent?

Includes hearing updates, invitations, appeal notices and certificate availability. No retroactive changes to sent messages.

- [ ] Yes
- [ ] No

Clarification: 

### M02. Should a failed email delivery be visible to admin and secretary so they can correct the contact issue or retry it?

Keep the portal message and delivery history; a failed email must not undo a committed case action.

- [ ] Yes
- [ ] No

Clarification: 

### M03. Should the applicant’s assigned-member change notification go through both the portal and email?

Applicants seeing the assigned member name and receiving a change notification are confirmed; specify both channels here.

- [ ] Yes
- [ ] No

Clarification: 

## Testimony & audio

### T01. For testimony larger than 100 MB, should CTM support consecutive recording parts, each within the 100 MB limit?

One testimony event can have multiple ordered audio files and a continuous transcript timeline. No loss of previously recorded parts.

- [ ] Yes
- [ ] No

Clarification: 

### T02. When testimony is rescheduled, should the previous Confirm/Reject response remain in history and a fresh response be requested for the changed appointment?

The affected applicant already receives the updated private portal/email invitation.

- [ ] Yes
- [ ] No

Clarification: 

### T03. May admin or secretary correct AI speaker labels and map them to the actual applicant or council member, retaining the AI original and change history?

Timestamps and labels are already required. This is attribution correction, not voice-based identity proof.

- [ ] Yes
- [ ] No

Clarification: 

### T04. If AI transcription or translation fails, should testimony remain usable from its saved audio while admin or secretary can retry processing?

Failure must not erase the recording or fabricate a completed transcript.

- [ ] Yes
- [ ] No

Clarification: 

### T05. Should admin or secretary be able to review the AI transcript and translation before those generated texts appear to other council members?

Source audio remains council-only as agreed. Choose No for immediate council access clearly marked AI-generated.

- [ ] Yes
- [ ] No

Clarification: 

