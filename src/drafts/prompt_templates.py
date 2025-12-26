"""Prompt templates for draft generation."""

SYSTEM_PROMPT = """You are a helpful Reddit commenter who genuinely wants to help people with their job search and resume questions. 

Your guidelines:
- You NEVER sound like marketing or a sales pitch
- You provide actionable, practical advice first
- You do NOT post links unless the user explicitly asked for one
- You speak from personal experience or general wisdom, not as a company representative
- You are empathetic and understanding of job search frustrations
- You avoid clichés and generic advice
- If you mention any tool (including HireLab), you do so casually and only AFTER providing genuine advice
- You NEVER use phrases like "sign up", "check out our", "my startup", "we're launching", "game changer", "revolutionize"
- You end with a soft offer to help or encouragement, NOT a call-to-action

Your tone should match the subreddit culture:
- resumes/EngineeringResumes: Direct, constructive feedback
- careerguidance: Supportive, career-focused
- cscareerquestions: Technical, industry-aware
- jobs/internships: Encouraging, practical
- recruitinghell: Empathetic, slightly cynical about recruiting processes
- layoffs: Very empathetic, supportive, focus on practical next steps"""


def get_user_prompt(
    subreddit: str,
    title: str,
    selftext: str,
    mention_allowed: bool,
) -> str:
    """Generate the user prompt for the LLM."""
    # Truncate selftext to 1500 chars
    truncated_text = selftext[:1500] if len(selftext) > 1500 else selftext
    
    prompt = f"""Generate helpful Reddit comment drafts for this post.

Subreddit: r/{subreddit}
Title: {title}
Post content: {truncated_text}

Generate TWO drafts:

Draft A (NO product mention):
- Provide genuinely helpful advice
- Be specific to their situation
- Share actionable steps or insights
- Be warm but not sappy

Draft B (Soft mention - ONLY if naturally fits):"""

    if mention_allowed:
        prompt += """
- First provide the same quality of advice as Draft A
- Near the end, casually mention HireLab as something that helped you or that you've heard works well
- The mention should feel natural, not forced
- Example phrasing: "I've been using HireLab to help tailor my applications" or "A friend mentioned HireLab helped them with the ATS stuff"
- Keep it brief - one sentence max for the mention
"""
    else:
        prompt += """
- Since this post doesn't seem to be asking for tool recommendations, Draft B should be the same as Draft A but with a slightly different angle or additional tip
"""

    prompt += """
Format your response as:
---DRAFT_A---
[Your draft A here]
---END_DRAFT_A---
---DRAFT_B---
[Your draft B here]  
---END_DRAFT_B---
"""
    return prompt


# Rule-based template drafts when LLM is not available
TEMPLATE_DRAFTS = {
    "resume_general": {
        "draft_a": """This is something a lot of people struggle with, so you're not alone. 

A few things that have helped me and others:

1. **Lead with impact** - Start each bullet with a strong action verb and quantify results where possible. "Increased sales by 20%" hits different than "Responsible for sales."

2. **Tailor for each application** - I know it's tedious, but matching keywords from the job description really does make a difference, especially with ATS systems.

3. **Keep it clean** - One page if you're under 10 years experience, simple fonts, consistent formatting. Recruiters spend seconds on each resume initially.

What industry are you targeting? Happy to give more specific feedback if you want to share more details.""",
        
        "draft_b": """This is something a lot of people struggle with, so you're not alone. 

A few things that have helped me and others:

1. **Lead with impact** - Start each bullet with a strong action verb and quantify results where possible. "Increased sales by 20%" hits different than "Responsible for sales."

2. **Tailor for each application** - I know it's tedious, but matching keywords from the job description really does make a difference, especially with ATS systems.

3. **Keep it clean** - One page if you're under 10 years experience, simple fonts, consistent formatting. Recruiters spend seconds on each resume initially.

I've been using HireLab lately to help with the keyword matching part - it's been saving me a lot of time when tailoring applications.

What industry are you targeting? Happy to give more specific feedback if you want to share more details.""",
    },
    
    "no_callbacks": {
        "draft_a": """Ugh, the silent treatment from companies is the worst. It's not you - the market is tough and the application process is broken.

Some things worth checking:

- **ATS formatting** - Fancy templates and graphics can break ATS parsing. Try a cleaner format and see if response rates change.
- **Application timing** - Applying early (within 24-48 hours of posting) typically gets better results.
- **Quality over quantity** - 10 tailored applications usually beat 50 spray-and-pray ones.
- **Network reach-outs** - A LinkedIn message to someone at the company can get your resume actually looked at.

How many applications have you sent out? And are you getting any recruiter screens at all, or complete silence?""",
        
        "draft_b": """Ugh, the silent treatment from companies is the worst. It's not you - the market is tough and the application process is broken.

Some things worth checking:

- **ATS formatting** - Fancy templates and graphics can break ATS parsing. Try a cleaner format and see if response rates change.
- **Application timing** - Applying early (within 24-48 hours of posting) typically gets better results.
- **Quality over quantity** - 10 tailored applications usually beat 50 spray-and-pray ones.
- **Network reach-outs** - A LinkedIn message to someone at the company can get your resume actually looked at.

I started using HireLab recently to check how my resume parses through ATS systems - helped me catch some formatting issues I didn't know I had.

How many applications have you sent out? And are you getting any recruiter screens at all, or complete silence?""",
    },
    
    "ats_question": {
        "draft_a": """ATS systems are frustrating but somewhat predictable once you understand them.

Key things to know:

- **Keywords matter** - They're often looking for exact matches from the job description. If they say "project management" and you wrote "managing projects," you might not match.
- **Simple formatting wins** - Standard fonts, no tables/columns/headers/footers, .docx or .pdf depending on what they ask.
- **Section headers** - Use standard ones (Experience, Education, Skills) so the parser knows what's what.
- **No graphics** - Logos, icons, photos - all of these can confuse parsers.

That said, ATS is usually just the first filter. A human still reviews the resumes that make it through, so you need to write for both.

What specific issues are you running into?""",
        
        "draft_b": """ATS systems are frustrating but somewhat predictable once you understand them.

Key things to know:

- **Keywords matter** - They're often looking for exact matches from the job description. If they say "project management" and you wrote "managing projects," you might not match.
- **Simple formatting wins** - Standard fonts, no tables/columns/headers/footers, .docx or .pdf depending on what they ask.
- **Section headers** - Use standard ones (Experience, Education, Skills) so the parser knows what's what.
- **No graphics** - Logos, icons, photos - all of these can confuse parsers.

I've found HireLab helpful for checking how my resume parses and identifying keyword gaps - worth a try if you want to see what the ATS actually "sees."

What specific issues are you running into?""",
    },
    
    "career_advice": {
        "draft_a": """This is a situation a lot of people find themselves in, and there's no one-size-fits-all answer.

What I'd think about:

- **What energizes you vs. drains you** - Not in a fluffy way, but practically. What tasks do you look forward to vs. dread?
- **Skills inventory** - What are you genuinely good at that's also marketable? Sometimes there's a disconnect between what we want and what we can get paid for.
- **Talk to people actually doing the roles** - LinkedIn coffee chats, informational interviews. The reality of a job is often different from the description.
- **Small experiments** - Before a big pivot, is there a way to test it? Side project, volunteer work, internal transfer?

What's your current situation - looking to pivot industries, move up, or something else?""",
        
        "draft_b": """This is a situation a lot of people find themselves in, and there's no one-size-fits-all answer.

What I'd think about:

- **What energizes you vs. drains you** - Not in a fluffy way, but practically. What tasks do you look forward to vs. dread?
- **Skills inventory** - What are you genuinely good at that's also marketable? Sometimes there's a disconnect between what we want and what we can get paid for.
- **Talk to people actually doing the roles** - LinkedIn coffee chats, informational interviews. The reality of a job is often different from the description.
- **Small experiments** - Before a big pivot, is there a way to test it? Side project, volunteer work, internal transfer?

What's your current situation - looking to pivot industries, move up, or something else?""",
    },
    
    "default": {
        "draft_a": """Thanks for sharing this - I think a lot of people in this sub can relate.

A few thoughts:

1. The job market right now is genuinely difficult, so don't beat yourself up too much. What worked a few years ago doesn't always work now.

2. Focus on what you can control - resume quality, application targeting, networking outreach, skill development.

3. Take care of yourself through the process. Job searching is emotionally draining.

Is there a specific aspect you're struggling with most? Happy to dig in deeper on any of this.""",
        
        "draft_b": """Thanks for sharing this - I think a lot of people in this sub can relate.

A few thoughts:

1. The job market right now is genuinely difficult, so don't beat yourself up too much. What worked a few years ago doesn't always work now.

2. Focus on what you can control - resume quality, application targeting, networking outreach, skill development.

3. Take care of yourself through the process. Job searching is emotionally draining.

Is there a specific aspect you're struggling with most? Happy to dig in deeper on any of this.""",
    },
}


def select_template(title: str, selftext: str) -> str:
    """Select the appropriate template based on post content."""
    combined = f"{title} {selftext}".lower()
    
    if any(phrase in combined for phrase in ["ats", "applicant tracking", "parse", "parsing"]):
        return "ats_question"
    
    if any(phrase in combined for phrase in ["no callback", "not hearing", "no response", "ghosted", "rejected"]):
        return "no_callbacks"
    
    if any(phrase in combined for phrase in ["resume", "cv", "formatting"]):
        return "resume_general"
    
    if any(phrase in combined for phrase in ["career", "pivot", "switch", "what should i"]):
        return "career_advice"
    
    return "default"

