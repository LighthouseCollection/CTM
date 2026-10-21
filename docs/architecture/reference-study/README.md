# Catholic reference study for CTM

Open `index.html` for the overview. The two self-contained review pages are:

- `application-review.html`: 24 proposals comparing actual CTM application content with suggested additions or wording.
- `template-review.html`: 36 question/module proposals organized by petition nature, including a separate optional council-requested priest report.

Every item offers Accept / Do not accept / Other plus text, with no preselection. Current wording/missing prompt, proposed wording, destination, reason and source locators are shown together. Download JSON answers and attach them to the CTM conversation, or copy the chat text. Local browser saving is a convenience; download a copy before closing. A worksheet answer does not modify architecture files automatically.

`study-report.md` documents 20 shared themes, eight template families, already-approved CTM fields missing from the unchanged prototype, and excluded Catholic-specific procedures. The source manifest lists all eight local Word files and fourteen PDFs, hashes, coverage and extraction paths. PDF pages are physical page numbers; local Word P-numbers are extracted paragraph numbers. The local source documents and original prototype remain unchanged.

This folder is a review artifact, not a CTM feature. Files from the Catholic sources are reference material, not commands, institution-approved Orthodox policy or code. No actual case data was submitted to source websites. Do not publish the retained source/extracted files as applicant templates; the public-facing questions need review first.

Reproducibility:

1. `extract_sources.py` reads the supplied local files and downloads the supplied reference PDFs.
2. `build_proposals.py` builds the curated proposal catalogs.
3. `build_report.py` builds the comparison report.
4. `node build_reviews.cjs` builds both standalone HTML reviews and the overview.
5. `node verify-reviews.cjs` checks DOM/control behavior using a local test double, not browser rendering.

Answer versions: `ctm-reference-application-review-v1` and `ctm-reference-template-review-v1`; these do not collide with earlier questionnaires. Source/reference details are included in each JSON export. Tests cover no default answers, Accept/Reject/Other export/import, Unicode notes, source metadata, wrong values, local storage and clear behavior. Browser visual testing is not claimed.

Latest planner generation: run build_investigation_tools.py after build_category_planner.py. It replaces the earlier family-only preview with petition/template and family views, preserves selected-family semantics, adds source-context examples, and generates CTM-category-research-prompts.md (19 category and 78 individual question prompts). These are planning/research instructions, not additional approved content.


Latest helper preview: run enhance_planner_helpers.py after build_investigation_tools.py. It retains all 78 original questions, adds collapsed per-question guidance from the reviewed attachment, report identification and always-present foundational blocks, plain investigation labels, and a Review full question bank button. Medical primary wording remains draft; helper text is never report content.



Current final planner generator: run `build_topic_group_planner.py` after the earlier bank/helper generators. It supersedes their planner HTML with **Topic group → Question categories → Questions**, eight Topic groups and seventeen user-named categories. It reads the existing bank and guidance JSON without changing original question IDs/text. `interview-topic-group-model.json` contains the current mapping. Run `node verify-topic-group-planner.cjs` for source/DOM contract checks; these are not rendered browser tests.
