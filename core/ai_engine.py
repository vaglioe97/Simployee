import anthropic
import streamlit as st
import json

client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

def generate_weekly_tasks(job_path, week_number):
    prompt = f"""You are a simulation engine for a job training platform called Simployee.

The user has been hired as a {job_path['title']} at {job_path['company']}, 
a company in the {job_path['industry']} industry.

Their manager is {job_path['manager']} ({job_path['manager_title']}).

Key responsibilities:
{chr(10).join(f"- {r}" for r in job_path['responsibilities'])}

Required stack: {', '.join(job_path['stack'])}

Company database schema (always reference exact table/column names in SQL tasks):
{job_path.get('schema', 'No schema provided.')}

Generate 3 realistic work tasks for Week {week_number} of their simulated job.
Each task should feel like a real ticket a junior analyst would receive at work.

Rules:
- Tasks must be practical and doable (the user will actually attempt them)
- Increase complexity gradually based on the week number
- Tasks must relate to the company context (retail, sales, inventory, customers)
- When tasks involve SQL, always mention the exact table and column names from the schema above
- Week 1-4: Basic tasks (data cleaning, simple queries, basic reports)
- Week 5-12: Intermediate tasks (analysis, visualization, Python scripts)
- Week 13-24: Advanced tasks (dashboards, automation, insights presentations)

Respond ONLY with a valid JSON array. No explanation, no markdown, no extra text.
Format:
[
  {{
    "title": "Short task title",
    "description": "2-3 sentences describing the task with business context, as if written by the manager in Slack. If the task involves SQL, mention the exact table and columns to use.",
    "deliverable": "Exactly what the user must submit (e.g. SQL query, Python script, Excel file, written analysis)"
  }},
  {{
    "title": "...",
    "description": "...",
    "deliverable": "..."
  }},
  {{
    "title": "...",
    "description": "...",
    "deliverable": "..."
  }}
]"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    print("=== RAW RESPONSE ===")
    print(repr(raw))
    print("====================")

    # Strip markdown if Claude wrapped it
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    tasks = json.loads(raw)
    return tasks


def evaluate_submission(task, submission_text, job_path, file_content=None, file_name=None):
    
    # Build the submission context
    if file_content and submission_text.strip():
        submission_context = f"""
The analyst submitted both a file and a written comment.

File uploaded: {file_name}
File content (first 3000 chars):
{file_content[:3000]}

Written comment:
{submission_text}
"""
    elif file_content:
        submission_context = f"""
The analyst submitted a file only.

File uploaded: {file_name}
File content (first 3000 chars):
{file_content[:3000]}
"""
    elif submission_text.strip():
        submission_context = f"""
The analyst submitted a written response only (no file attached).

Written response:
{submission_text}
"""
    else:
        submission_context = "The analyst submitted nothing meaningful."

    prompt = f"""You are Sophie Chen, a {job_path['manager_title']} at {job_path['company']}.
You are reviewing work submitted by your junior analyst.

Task assigned:
Title: {task['title']}
Description: {task['description']}
Expected deliverable: {task['deliverable']}

What was submitted:
{submission_context}

Instructions for your response:
- Write exactly like a real manager messaging their junior on Slack — direct, human, no corporate speak
- NEVER start with "Great job!" or "Excellent work!" or any generic praise opener
- If the deliverable was supposed to be a file (Excel, CSV, script) and they only sent text, call it out directly and ask for the actual file. Example tone: "Hey, I appreciate the explanation but I actually need the file itself here, not just a description of what you did."
- If they submitted a file but it's missing something, point it out specifically
- If the work is genuinely good, acknowledge it but still give one concrete improvement tip
- If the work has real errors or problems, be honest about it — don't sugarcoat
- Keep it 150-250 words
- Sound like a real person, not an AI. No bullet point lists in your response.
- End with either a follow-up question or a next step, like a real manager would"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text.strip()