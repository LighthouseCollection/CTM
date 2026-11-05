"""Fictitious, varied narrative text for the gated workflow demo seed.

Every paragraph is built from the case's own synthetic names, city and years, so
no two cases share an identical paragraph. The text is neutral demo prose: it
makes no church-law claim and imitates no official institutional wording.
"""

import random

CITIES = [
    "Pasadena", "Riverside", "Irvine", "Torrance", "Long Beach", "Glendale",
    "San Diego", "Ontario", "Fresno", "Bakersfield", "Santa Ana", "Pomona",
    "Burbank", "Corona", "Fullerton", "Downey", "Whittier", "Temecula",
    "Oxnard", "Ventura", "Sacramento", "Phoenix", "Las Vegas", "Henderson",
    "Tucson", "Mesa", "Chandler", "Modesto", "Stockton", "Visalia",
    "Lancaster", "Palmdale", "Escondido",
]
MONTHS = [
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
]
MET = [
    "We met in {met_year} at a friend's birthday dinner in {city}, where {spouse} and I sat at the same table and talked for most of the evening.",
    "{spouse} and I were introduced in {met_year} through a cousin who thought we would get along; our first conversation was at a coffee shop in {city}.",
    "I first met {spouse} in {met_year} when we both volunteered for a youth summer program in {city}, and we stayed in touch after it ended.",
    "We met in {met_year} at a community college in {city}; {spouse} was in my statistics class and we started studying together before exams.",
    "{spouse} and I met in {met_year} at a wedding reception in {city}. Our families already knew each other, and we began meeting regularly a few months later.",
    "In {met_year} I moved to {city} for work and met {spouse} through a small Bible study group that gathered on Thursday evenings.",
]
MARRIAGE = [
    "{spouse} and I were engaged for about a year and married in {married_year}. For the first years we rented a small apartment in {city}, and I remember that period as calm and hopeful.",
    "We married in {married_year} after a long engagement. In the early years {spouse} and I shared most decisions, saved for a home, and spent weekends with both families.",
    "Our wedding took place in {married_year}. We settled near {city}, and for a while our routine of work, church on Sundays and family dinners felt steady.",
    "We married in {married_year} and moved twice in the first five years because of my job. {spouse} supported those moves, and we were close during that time.",
    "After we married in {married_year}, {spouse} and I bought a modest house outside {city}. We hoped to raise a family there and were active in our parish.",
]
GROUND = {
    "infidelity": [
        "In {trouble_year} I learned that {spouse} had been in a relationship with another person for several months. When I raised it, {spouse} first denied it and later acknowledged it.",
        "Around {trouble_year} I found messages on a shared tablet showing that {spouse} was seeing someone outside our marriage. The relationship continued even after we discussed it openly.",
        "Starting in {trouble_year}, {spouse} often stayed out late with explanations that did not match. A mutual friend eventually told me about an ongoing relationship, which {spouse} then confirmed.",
    ],
    "abandonment": [
        "In {trouble_year} {spouse} accepted a job in another state and told me the move would be temporary. Over time calls became rare, and {spouse} stopped returning home on holidays.",
        "Beginning in {trouble_year}, {spouse} spent longer periods with relatives and finally moved out without telling me where. Since then contact has been limited to occasional short messages.",
        "In {trouble_year} {spouse} left our home after an argument and did not come back. I have tried to keep the door open, but {spouse} has not responded to most of my attempts to talk.",
    ],
    "abuse": [
        "From about {trouble_year}, arguments with {spouse} became frightening. There were incidents of shouting, broken household items and threats, and I began staying with my sister for my safety.",
        "Around {trouble_year} {spouse} started controlling my phone and money and became physically aggressive on several occasions. A neighbor once called for help after hearing what happened.",
        "After {trouble_year} the tension at home grew into repeated verbal and physical mistreatment. I kept a written record of the incidents and spoke with a counselor about them.",
    ],
    "faith": [
        "In {trouble_year} {spouse} told me that faith no longer had a place in our home. {spouse} stopped attending church and asked that our children not be raised in the Church.",
        "Around {trouble_year} {spouse} joined a different religious group and later asked me to leave the Church as well. Our disagreements about this became constant.",
        "From {trouble_year} onward {spouse} became openly hostile to my faith, mocked prayer at home and refused to have any religious practice in the household.",
    ],
    "addiction": [
        "In {trouble_year} I realized {spouse} was drinking heavily most evenings. Bills went unpaid, a car was damaged, and promises to stop did not last more than a few weeks.",
        "Around {trouble_year} {spouse} developed a gambling problem. Our savings were used without my knowledge, and debts appeared that I learned about from collection letters.",
        "Beginning in {trouble_year}, {spouse} struggled with substance use. There were two short treatment programs, but each time the pattern returned soon after.",
    ],
    "concealment": [
        "Only in {trouble_year} did I learn that {spouse} had concealed a previous civil marriage before our wedding. I found the documents while organizing our tax papers.",
        "In {trouble_year} I discovered that {spouse} had hidden a serious health condition and its expected effects on family life, which had been known before we married.",
        "In {trouble_year} I learned that {spouse} had concealed significant debts and a prior legal matter before our engagement, information I would have wanted to know before marrying.",
    ],
}
SEPARATION = [
    "We have lived apart since {sep_month} {sep_year}. I remained in {city} and {spouse} moved to {other_city}.",
    "Our separation began in {sep_month} {sep_year}, when {spouse} took a lease in {other_city}. We have not shared a home since.",
    "Since {sep_month} {sep_year} {spouse} and I have lived in separate homes, I in {city} and {spouse} in {other_city}.",
    "I moved out in {sep_month} {sep_year} and have since lived with my parents in {city}; {spouse} stayed in {other_city}.",
]
RECONCILIATION = [
    "Before filing, we met several times with our father of confession and attended six sessions with a licensed family counselor. {spouse} stopped attending after the third session.",
    "Our families tried to help {spouse} and me reconcile in {recon_year}, and we spent a weekend together to talk things through. It did not change the situation.",
    "I asked {spouse} more than once to meet with our priest together. We did meet twice in {recon_year}, but we could not agree on any next step.",
    "In {recon_year} {spouse} and I tried living together again for about two months. The same problems returned, and we separated again by the end of that year.",
    "I contacted {spouse} through a family friend in {recon_year} to propose counseling. {spouse} declined and asked me not to contact them again about it.",
]
CLOSING = [
    "I am filing this petition so the council can review our situation. I am ready to answer questions and provide any further documents that are needed.",
    "I understand the council will review the documents and may ask to meet with me. I will make myself available on the dates offered.",
    "I submit this statement in good faith and ask that the council consider it with the attached documents.",
]

NOTE_TEMPLATES = [
    "Intake review for {applicant} and {spouse}: petition statement and the five supporting documents are on file. Grounds stated: {grounds}. Separation reported since {sep_month} {sep_year}.",
    "Spoke with {applicant} by phone about the timeline. Clarified that the move to {other_city} happened in {sep_month} {sep_year}, not earlier as one document suggests. Will confirm with the marriage certificate dates.",
    "Reviewed the reconciliation history with {applicant}. Counseling and family meetings are described consistently in the statement and the interview. No contact details for {spouse} beyond the last known address in {other_city}.",
    "Interview completed. {applicant} answered calmly and in detail; account of events in {trouble_year} matches the written statement. Recommend that the council also hear from {spouse} if reachable.",
    "Checked that the parish letter and photographs are legible. Asked {applicant} to keep the original civil documents available for the hearing. Case looks ready to present.",
    "Follow-up: {applicant} sent the updated address for {spouse}. Prepared a short summary of the {grounds} grounds for the council file.",
]
SECRETARY_NOTES = [
    "Petition from {applicant} received and checked for completeness. All five required documents are present and readable. Waiting for a case manager to be assigned.",
    "Placed on the agenda for assignment. Note for the assigning member: applicant lives in {city}, spouse {spouse} reported in {other_city}; grounds stated as {grounds}.",
    "Applicant {applicant} called to ask about next steps. Explained that a council member will be assigned and will contact them directly.",
]
STAFF_MESSAGES = [
    "Dear {applicant}, thank you for submitting your petition. Your documents have been received and are being reviewed. We will contact you if anything else is needed.",
    "Dear {applicant}, could you confirm the month you and {spouse} began living apart? The statement mentions {sep_month} {sep_year}; we want to make sure the file is consistent.",
    "Dear {applicant}, your interview is scheduled. Please bring a photo ID and, if available, the original marriage certificate. Reply here if the time does not work for you.",
    "Dear {applicant}, your case is now on the council agenda. You do not need to do anything at this time; we will write to you after the session.",
    "Dear {applicant}, we received your updated document. Thank you for sending it so quickly.",
]
APPLICANT_MESSAGES = [
    "Thank you. Yes, we separated in {sep_month} {sep_year}. {spouse} moved to {other_city} that month.",
    "Thank you for the update. I will be available for the interview. Is it possible to bring a family member to wait outside?",
    "I found an additional letter from our counselor from {recon_year}. Should I upload it, or bring it to the interview?",
    "Thank you for letting me know. Please tell me if you need anything else from me before the session.",
]
CALL_OUTCOMES = [
    ("sent", "Reached applicant", "Confirmed contact details and explained the interview process. {applicant} asked about expected timing; told them it depends on the council schedule."),
    ("sent", "Left voicemail", "Left a short message asking {applicant} to call back about the separation date in {sep_year}."),
    ("received", "Applicant called", "{applicant} called to confirm receipt of the interview message and asked whether {spouse} would be contacted. Explained that the case manager will decide."),
    ("sent", "Reached applicant", "Discussed the reconciliation attempts in {recon_year}. {applicant} will upload the counselor's letter this week."),
]
OBSERVATIONS = [
    "{applicant} described meeting {spouse} in {met_year} and the marriage in {married_year} in a consistent way. The difficulties that started in {trouble_year} were explained with specific examples. Reconciliation attempts in {recon_year} are supported by the counselor's letter. Further clarification of {spouse}'s current address in {other_city} is recommended.",
    "The interview with {applicant} lasted about an hour. The account of the {grounds} ground matches the written statement, and the dates given ({trouble_year}, separation in {sep_month} {sep_year}) agree with the documents. {applicant} was cooperative and asked that {spouse} be treated fairly in the process.",
    "{applicant} answered all questions. The chronology from {married_year} to the separation in {sep_year} is clear. Two minor date differences between the statement and the parish letter were explained as typing errors. No new concerns arose during the interview.",
]
OUTCOMES = [
    (
        "{presenter} presented the case of {applicant} and {spouse}, married in {married_year} and living apart since {sep_year}. Members asked about the reconciliation attempts in {recon_year} and the documents supporting the {grounds} ground.",
        "Ask {spouse} for a written response if contact can be made, then return the case to the council with the response or a note that none was received.",
    ),
    (
        "Members reviewed the interview report and the statement from {applicant}. The account of events since {trouble_year} was found consistent across the file. One member asked for the original civil documents to be checked.",
        "Verify the civil documents, record the result in a case note, and schedule the case for decision at a later session.",
    ),
    (
        "{presenter} summarized the file for {applicant}. Discussion focused on the separation in {sep_month} {sep_year} and whether the move to {other_city} was intended to be permanent.",
        "Request a short follow-up interview with {applicant} about the separation timeline before the council deliberates.",
    ),
]
GROUND_LABELS = {
    "infidelity": "infidelity", "abandonment": "abandonment", "abuse": "abuse",
    "faith": "change of faith", "addiction": "addiction", "concealment": "concealment",
}


def case_story(index, applicant, spouse, grounds, married_year):
    """Deterministic facts and text for one fictitious case."""
    rng = random.Random(f"ctm-demo-story-{index}")
    city = CITIES[index % len(CITIES)]
    other_city = CITIES[(index * 7 + 3) % len(CITIES)]
    if other_city == city:
        other_city = CITIES[(index + 1) % len(CITIES)]
    trouble_year = min(married_year + 4 + index % 6, 2024)
    sep_year = min(trouble_year + 1, 2025)
    facts = {
        "applicant": applicant,
        "spouse": spouse,
        "city": city,
        "other_city": other_city,
        "met_year": married_year - 1 - index % 3,
        "married_year": married_year,
        "trouble_year": trouble_year,
        "sep_year": sep_year,
        "sep_month": MONTHS[(index * 5) % 12],
        "recon_year": min(sep_year + 1, 2026),
        "grounds": ", ".join(GROUND_LABELS.get(g, g) for g in grounds),
    }
    fill = lambda template: template.format(**facts)
    paragraphs = [
        fill(rng.choice(MET)),
        fill(rng.choice(MARRIAGE)),
        *[fill(rng.choice(GROUND[g])) for g in grounds],
        fill(rng.choice(SEPARATION)),
        fill(rng.choice(RECONCILIATION)),
        fill(rng.choice(CLOSING)) + f" — {applicant}, {city}",
    ]
    note_count = 2 + index % 3
    ordered = lambda pool, k: [pool[i] for i in sorted(rng.sample(range(len(pool)), k))]
    notes = [fill(text) for text in ordered(NOTE_TEMPLATES, note_count)]
    secretary_notes = [fill(text) for text in ordered(SECRETARY_NOTES, 1 + index % 2)]
    staff = ordered(STAFF_MESSAGES, 3 if index % 2 else 2)
    replies = ordered(APPLICANT_MESSAGES, 2)
    messages = []
    for position, body in enumerate(staff):
        messages.append(("staff", fill(body)))
        if position < len(replies):
            messages.append(("applicant", fill(replies[position])))
    calls = [
        (direction, outcome, fill(notes_text))
        for direction, outcome, notes_text in rng.sample(CALL_OUTCOMES, 1 + index % 2)
    ]
    internal, recommendation = rng.choice(OUTCOMES)
    return {
        "facts": facts,
        "statement": "\n\n".join(paragraphs),
        "notes": notes,
        "secretary_notes": secretary_notes,
        "messages": messages,
        "calls": calls,
        "observations": fill(rng.choice(OBSERVATIONS)),
        "outcome": (internal, recommendation),
    }
