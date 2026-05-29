---
name: inbox-triage
description: Use this skill whenever the user asks to triage, sort, prioritize, organize, or summarize their inbox, emails, mail, or messages. Triggers include phrases like "triage my inbox", "what's important in my inbox", "summarize my emails", "draft replies", or "clean up my mail". Do not use for checking specific email content or listing individual emails.
---

# inbox-triage

## Overview

Use this skill to turn a noisy inbox into a focused action queue.
The goal is to automatically sort incoming messages, prioritize what matters, and draft high-quality replies so the user saves time every day.

For each triage run, produce:

1. A prioritized inbox summary (what needs attention now vs later).
2. A categorized message list (action required, waiting, FYI, newsletters, spam/noise).
3. Draft replies for messages that can be handled immediately.
4. Suggested follow-ups and reminders for messages that should not be replied to yet.

## Instructions

### Step 1: Pull and normalize inbox data

- Fetch recent messages with minimal fields first (id, subject, sender, received time).
- Retrieve body preview or full body only when needed for classification or drafting.
- Group by thread/conversation when available so duplicates are not processed as separate work.

### Step 2: Classify each message

Assign each message to exactly one category:

- Action Required: user must do something.
- Waiting/Delegated: user is blocked on someone else.
- FYI/Reference: no reply needed now.
- Newsletter/Automated: informational bulk traffic.
- Noise/Spam: irrelevant or unsolicited.

### Step 3: Priority scoring

Compute a priority label `P0`, `P1`, `P2`, or `P3`:

- `P0` Urgent-Critical: executive/customer escalation, outage, hard deadline today, repeated follow-up from key stakeholder.
- `P1` High: direct ask with near-term deadline, decision request, important partner/customer communication.
- `P2` Medium: useful but not urgent, can be batched later today/this week.
- `P3` Low: newsletters, low-value updates, and non-actionable noise.

Use these signals:

- Sender importance (manager, exec, customer, direct team).
- Deadline language (today, EOD, urgent, ASAP).
- Business impact (revenue, incident, blocker, contractual risk).
- Thread momentum (number of follow-ups, unanswered age).
- Explicit asks vs informational content.

If uncertain between two priorities, choose the higher one.

### Step 4: Decide next action

For each message, choose one action:

- Draft Reply Now.
- Defer (schedule for later triage block).
- Archive/Read Later.
- Mark as Waiting (with reminder date suggestion).

Favor speed:

- Auto-draft straightforward replies.
- Batch similar items (status updates, scheduling, acknowledgments).
- Skip drafting for noise unless user asked for unsubscribe/cleanup.

### Step 5: Draft responses

Generate concise, ready-to-send drafts with this structure:

1. One-line acknowledgment.
2. Direct answer or current status.
3. Clear next step with owner and date when possible.
4. Optional short closing.

Draft style rules:

- Match sender context: professional, friendly, and brief.
- Prefer short paragraphs or bullets for scanability.
- Ask at most one clarifying question when required.
- Include concrete dates instead of vague promises.
- Avoid over-apologizing or unnecessary filler.

## Draft Templates

### Acknowledgment + ETA

Subject: Re: {{original_subject}}

Hi {{name}},

Thanks for this. I am on it and will send you an update by {{specific_time}}.

Best,
{{user_name}}

### Quick answer + next step

Subject: Re: {{original_subject}}

Hi {{name}},

Yes, {{direct_answer}}.

Next step: {{action}}. I will complete this by {{specific_date}}.

Best,
{{user_name}}

### Need clarification

Subject: Re: {{original_subject}}

Hi {{name}},

Thanks for the note. To make sure I handle this correctly, could you confirm {{single_question}}?

Once I have that, I can proceed right away.

Best,
{{user_name}}

### Delegation / reroute

Subject: Re: {{original_subject}}

Hi {{name}},

Thanks. {{owner_name}} is the best person for this piece, and I have looped them in.

I will track this and follow up by {{specific_date}} if needed.

Best,
{{user_name}}

## Output Format For Each Run

Always return results in exactly the following five sections, in this exact order, using these exact Markdown headings. Do not add, rename, reorder, or omit sections. If a section has no items, still render the heading and write `_None_` underneath.

### 1. `## Triage Summary`

A concise, scannable overview rendered BEFORE any detail. Use exactly this structure:

- One sentence stating total messages reviewed and the time window (e.g., "Reviewed 24 messages from the last 24 hours.").
- A single-line counts row in this exact format:
  `Counts: P0=<n> | P1=<n> | P2=<n> | P3=<n> | Drafts=<n> | Waiting=<n>`
- A bulleted list titled `Top actions:` containing at most 3 bullets. Each bullet must be one line and follow this format:
  `- [P<0-1>] <sender> — <subject> → <recommended_action>`
- A one-line closing titled `Headline:` summarizing what most needs the user's attention today (max 20 words).

Keep the entire Triage Summary under 10 lines. No drafts, no reasoning, no tables in this section.

### 2. `## Priority Queue`

A single Markdown table sorted by priority ascending (P0 first), then by received time descending. Columns must be exactly:

| Priority | From | Subject | Category | Action | Reason |
|----------|------|---------|----------|--------|--------|

- `Reason` must be max 12 words.
- `Action` must be one of: `Draft Reply Now`, `Defer`, `Archive/Read Later`, `Mark as Waiting`.

### 3. `## Category Summary`

A bulleted list with one bullet per category, in this fixed order, even if empty:

- `Action Required (<n>):` comma-separated subjects, or `_None_`.
- `Waiting/Delegated (<n>):` …
- `FYI/Reference (<n>):` …
- `Newsletter/Automated (<n>):` …
- `Noise/Spam (<n>):` …

### 4. `## Drafts Ready`

For each draft, render a fenced block using this exact schema (no extra fields, no prose between blocks):

```
message_id: <id>
from: <name <email>>
subject: <Re: original subject>
priority: <P0|P1|P2>
draft: |
  <multi-line draft body, preserving line breaks>
```

### 5. `## Deferred / Waiting`

A single Markdown table with these exact columns:

| Priority | From | Subject | Next Step | Follow-up Date |
|----------|------|---------|-----------|----------------|

Formatting rules that apply to every section:

- Use ISO dates (`YYYY-MM-DD`) everywhere.
- Never invent senders, subjects, IDs, or dates. If a field is unknown, write `unknown`.
- Do not add introductions, conclusions, or commentary outside the five sections above.

## Quality Bar

Before finishing:

- Confirm every `P0/P1` message has a recommended action.
- Confirm drafts contain no fabricated facts.
- Confirm deadlines and owners are explicit where applicable.
- Confirm low-priority items are safe to defer.

This skill optimizes for fast, trustworthy inbox handling while keeping the user in control of final sends.

## Work IQ Mail MCP Server Alignment

Use this section when the agent is connected to `mcp_MailTools` (Work IQ Mail).

### Supported tools to use

- `mcp_MailTools_graph_mail_searchMessages`: Primary discovery tool for inbox triage candidates.
- `mcp_MailTools_graph_mail_getMessage`: Fetch message details for selected IDs.
- `mcp_MailTools_graph_mail_createMessage`: Create draft replies/new messages.
- `mcp_MailTools_graph_mail_updateMessage`: Update draft subject/body/categories/importance.
- `mcp_MailTools_graph_mail_sendDraft`: Send a specific draft by ID only after user confirmation.
- `mcp_MailTools_graph_mail_sendMail`: Direct send only when explicitly requested.
- `mcp_MailTools_graph_mail_reply` and `mcp_MailTools_graph_mail_replyAll`: Immediate send actions; use only with explicit user instruction.
- `mcp_MailTools_graph_mail_deleteMessage`: Optional cleanup/archive workflows when requested.
- `mcp_MailTools_graph_mail_listSent`: Verify sent history or avoid duplicate responses.

### Tool-level behavior rules

- Discovery pass:
1. Call `mcp_MailTools_graph_mail_searchMessages` with small pages using `requests[].from` and `requests[].size`.
2. Search first by urgency/business terms and recent messages, then broaden if needed.
- Detail pass:
1. Call `mcp_MailTools_graph_mail_getMessage` only for shortlisted IDs.
2. Use `select` to limit fields and reduce payload.
3. Use `preferHtml` only when needed for formatting-sensitive messages.
- Draft pass:
1. Build drafts via `mcp_MailTools_graph_mail_createMessage` using `subject`, `toRecipients`, and `body`.
2. If edits are needed, patch drafts with `mcp_MailTools_graph_mail_updateMessage`.
3. Set `body.contentType` to `"HTML"` only when HTML formatting is required.
- Send pass:
1. Preferred: send drafts with `mcp_MailTools_graph_mail_sendDraft` after approval.
2. Use `sendMail`/`reply`/`replyAll` only when the user explicitly says to send now.

### Work IQ-safe triage policy

- Because `reply` and `replyAll` are send operations, do not use them during draft-only triage.
- For draft-only triage, simulate a reply by drafting a new message with `subject: Re: <original subject>` and correct recipients.
- Do not delete messages unless the user asks for cleanup.
- Use `If-Match` with `updateMessage` or `deleteMessage` when ETag is available for safer concurrency.

### Suggested Work IQ search request shape

Use `mcp_MailTools_graph_mail_searchMessages` with a compact request like:

```json
{
	"requests": [
		{
			"entityTypes": ["message"],
			"query": { "queryString": "(urgent OR asap OR today OR blocker)" },
			"from": 0,
			"size": 10
		}
	]
}
```

Then paginate with increasing `from` while keeping `size` small.

### Priority-to-tool action mapping

- `P0`: detail fetch immediately with `getMessage`, create draft, surface for immediate user approval to send.
- `P1`: create draft in same run; batch send approval at end.
- `P2`: draft optional; defer when no direct ask.
- `P3`: no draft by default; optionally categorize/clean up if user requests.

### Final confirmation gate

Before any send tool is called, present:

1. Recipient list
2. Final subject
3. Final body preview
4. Send mode (`sendDraft`, `sendMail`, `reply`, or `replyAll`)

Require explicit confirmation from the user to proceed.
