# Design notes

## Principles

1. **Trust comes from sources.** Every answer shows numbered source chips that open the video at the cited second. Quotes that are not verbatim are flagged.
2. **Show what the system is doing.** A skill badge ("Q&A", "Ship 30 essay", "Artifact") tells the user which skill ran, and its tooltip says why. Status lines appear during slow steps ("Revising toward 1250...", "Building your artifact...").
3. **Familiar layout.** Left sidebar for chats, center column for the conversation, right panel for artifacts, as in ChatGPT and Claude.
4. **Errors are plain language.** A missing key, a rate limit, a database problem and a sleeping server each have a clear message instead of a crash.
5. **Safe by default.** HTML artifacts run in a sandboxed iframe with no access to the app or its data.

## Layout

| Area | Contents |
|---|---|
| Sidebar (dark) | "New chat" button, the user's chat list |
| Conversation | Empty state with three example prompts, messages, source chips |
| Input bar | Mode chips (Auto, Q&A, Essay, Artifact), text box, Send / Stop |
| Artifact panel | Title, Preview and Code tabs, Copy, Close |

## Visual language

- Slate neutrals with one accent, indigo. User messages are indigo bubbles, assistant messages sit on white cards.
- Headings in rendered Markdown are sized for reading long essays, and tables render with borders.
- Desktop first. The artifact panel takes about half the width when open.

## UX decisions

- **Auto mode by default** so users do not need to learn commands. The mode chips are an override, and they show the router is not magic.
- **Open as document** on essays moves a long answer to the side panel for reading.
- **Stop button** cancels a long generation, and the partial answer is still saved.
- **Previous chats reopen with their artifacts.**
- **Sample prompts** on the empty screen teach the three skills in one click.

## Known gaps

- Mobile layout is not designed. The two-column layout needs a stacked version.
- Artifacts do not stream live. The panel opens when the full artifact is ready.
- No keyboard shortcuts, dark mode or chat renaming and deletion.