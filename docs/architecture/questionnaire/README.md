# CTM architecture decision worksheet

Open `CTM-architecture-questionnaire.html` directly in your browser. It is a single local file, requires no installation or server, and sends no data over the network. `index.html` is the equivalent editable multi-file version.

- 39 remaining substantive scenarios, grouped into eight sections.
- Every question has Yes / No and optional clarification. No answers are preselected.
- A clarification may be entered without an answer; unanswered items stay unresolved.
- Progress saves locally when browser storage permits. Download a copy before closing.
- **Download answers** exports JSON. Attach that file to the existing CTM conversation.
- **Copy for chat** prepares readable text to paste into the conversation, with a manual-copy fallback.
- **Load saved answers** restores a JSON export; replacement requires confirmation.
- **Print / Save as PDF** provides a paper alternative. `questions.md` is another editable text alternative.

No automatic messaging to an assistant occurs. Answers are not applied to the architecture until reviewed in the conversation; clarifications take precedence over a bare Yes/No. The questions are proposals, not new requirements. Applicant-portal design and operational/provider decisions remain deferred. Existing confirmed decisions remain unchanged.

`verify.cjs` checks the question data and transfer logic using Node built-ins and regenerates the standalone HTML and Markdown companion. It does not perform visual browser testing.

## Additional workflow questionnaires

- [Applicant portal workflow](applicant-portal-questionnaire.html): 30 questions, with its own saved progress and export version `ctm-applicant-portal-review-v1`.
- [Assigned member interview workflow](case-interview-questionnaire.html): 34 questions, including template-led information gathering, microphone/audio upload, automatic transcription, translation, review and visibility. Export version `ctm-case-interview-review-v1`.

Both are self-contained local HTML files with Yes / No / Other and an Other / clarification textarea. Choosing Other focuses that textarea. Download the answer JSON or copy the answer text back to the CTM conversation. They do not modify the original architecture questionnaire, its saved answers or confirmed policy. Each also has a Markdown question list and JSON question specification. Other may be selected with its text still unfinished; exported clarifications are preserved and incomplete answers can be discussed later.

Regenerate with `node build-workflow-questionnaires.cjs`; check basic DOM/control behavior with `node verify-workflows.cjs`. These checks do not claim browser visual testing.
