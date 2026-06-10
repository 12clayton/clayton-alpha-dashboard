\---

name: industry-audit

description: Use when validating, auditing, or accepting changes to the industry research website in Global\_QDII\_Risk\_Monitor. Runs the correct compile and audit checks without expanding the task.

\---



\# Industry Audit Skill



Use this skill when the user asks to validate industry website changes, check if a fix worked, run audit, inspect warnings, or decide whether a change is safe to commit.



\## Scope



This skill applies to the industry research website:



\- `industry\_app.py`

\- `src/industry\_\*`

\- `scripts/audit\_industry\_\*`

\- industry radar

\- industry news

\- catalyst framework

\- Markdown / JSON export

\- V4 / V5 industry research modules



Do not use this skill to modify the main dashboard `app.py` unless the user explicitly asks.



\## Standard validation commands



Run the smallest relevant set of commands.



For general industry website validation:



```powershell

python -m compileall industry\_app.py src scripts



