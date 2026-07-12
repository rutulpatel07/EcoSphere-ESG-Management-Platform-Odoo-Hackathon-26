# CLAUDE.md — standing rules for this repo
1. NEVER run git add, git commit, git push, git merge, or any git write command. Ever.
   When work is done, STOP and say "Ready for human review and commit."
2. Only create/edit files inside YOUR OWNER ZONE (stated in each prompt). Never touch
   files outside it, even to "fix" something — report the issue instead.
3. Do not add new dependencies to requirements.txt or package.json — they are frozen.
   If a dependency is missing, STOP and report.
4. Follow docs/CONTRACT.md (API shapes) and backend/db/schema.sql exactly. Do not
   rename fields, routes, or tables.
5. No third-party API calls anywhere. No Firebase/Supabase/Mongo. Local Postgres only.