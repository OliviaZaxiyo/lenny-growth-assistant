# Product Requirements: Lenny Growth Assistant

_Status: version 1 drafted after the first working prototype, then updated as decisions changed (for example, dropping Ollama and adding the quote checker)._

## Problem

Lenny's Podcast holds hundreds of hours of product and growth advice. It is hard to search, and general chatbots mix it with unsourced opinions. People want answers they can trust, with proof of where each idea came from.

## Users

- Product managers and founders looking for practical advice.
- Writers who want to turn that advice into publishable content.

## Goals

1. Answer questions strictly from the transcripts, with citations that lead to the exact moment in the video.
2. Turn the same knowledge into essays in the Ship 30 for 30 style.
3. Produce documents and pages the user can see rendered inside the app.
4. Keep each chat's history, persistently.

## Non-goals

- Login and accounts, billing, mobile layout.
- Answering from outside knowledge.
- Training or fine-tuning a model.

## Requirements

| # | Requirement | Acceptance check |
|---|---|---|
| 1 | Start a new chat session with its own context | New Chat creates a session. Reopening shows its history |
| 2 | Grounded Q&A | Each claim has a citation. Questions with no match say so and make no model call |
| 3 | Ship 30 for 30 essay skill | About 1,250 words (the system revises once if outside 1,000 to 1,500), hook, numbered sections, bold mini-headlines, takeaway and TL;DR |
| 4 | Artifact generation and viewer | HTML renders in a sandboxed frame, Markdown renders as a document, Code tab and Copy work |
| 5 | Skill routing | Auto mode picks the skill by rules. A mode chip overrides it |
| 6 | Switchable LLM | Model set by environment variable with a fallback list. A mock mode exists |
| 7 | Robustness | Clear messages for a missing key, rate limits, timeouts and database failures |

## Success measures

- Spot checks of answers against the transcripts find no invented numbers or quotes.
- A cited link opens near the cited sentence.
- Essay length lands between 1,000 and 1,500 words.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Model adds facts not in the excerpts | Strict skill instructions, plus a code check that strips quotation marks from non-verbatim quotes |
| Free model limits and downtime | A list of fallback models, clear errors, and a mock mode for development |
| Messy source data (ads, duplicates, wrong links) | Sponsor filter, duplicate removal, known limitations documented |
| Keyword search misses paraphrases | Documented. Embeddings are the next step |