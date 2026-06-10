\---

name: safe-git-commit

description: Use when committing, pushing, staging files, or checking git status in Global\_QDII\_Risk\_Monitor. Prevents accidental commits of unrelated files, app.py, data files, local scripts, or Codex config files.

\---



\# Safe Git Commit Skill



Use this skill whenever the user asks to commit, push, save a version, check git status, or decide which files should be staged.



\## Core rules



1\. Never use `git add .`.

2\. Always inspect the current state before staging:

&#x20;  - `git status --short`

&#x20;  - `git diff --name-only`

&#x20;  - `git diff --cached --name-only`

3\. Only stage files directly related to the current task.

4\. Before committing, show:

&#x20;  - staged files

&#x20;  - unstaged files

&#x20;  - untracked files

&#x20;  - proposed commit message

5\. Do not commit unless the staged files match the task.



\## Project boundary



This repository currently contains two lines of work:



\### Main dashboard / original investment dashboard

Typical files:

\- `app.py`

\- portfolio / holdings / auto-invest / private daily report logic



\### Industry research website

Typical files:

\- `industry\_app.py`

\- `src/industry\_\*`

\- `scripts/audit\_industry\_\*`

\- `docs/` only when the task is documentation-related



For industry website tasks, do not stage:

\- `app.py`

\- `data/`

\- `.agent/`

\- `.agents/` unless the task explicitly concerns skills

\- `AGENTS.md` unless the task explicitly concerns Codex project instructions

\- `docs/codex\_experience\_playbook.md`

\- `scripts/\*.bat`

\- local cache files

\- private scripts



For main dashboard tasks, do not stage:

\- `industry\_app.py`

\- `src/industry\_\*`

\- `scripts/audit\_industry\_\*`

unless the user explicitly says the task affects the industry website.



\## Commit flow



1\. Run `git status --short`.

2\. Identify the intended task.

3\. List candidate files to stage.

4\. Stage only those files.

5\. Run `git diff --cached --name-only`.

6\. Confirm no unrelated files are staged.

7\. Commit with a concise versioned message.

8\. Push only after commit succeeds.

9\. Run `git status` after push.



\## Red flags



Stop and ask the user before committing if staged files include:

\- `app.py` during an industry website task

\- `data/`

\- `.agent/`

\- `.agents/` outside a skill task

\- `AGENTS.md` outside an instruction task

\- unexpected untracked files

\- generated乱码 / accidental files

