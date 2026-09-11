# Security and Privacy

This prototype concerns emergency-intake information and must be developed using synthetic data unless a formally approved protected-data environment is available.

Never commit:

- patient or caller identifiers;
- real recordings or transcripts;
- access tokens, API keys or credentials;
- production exports, logs or databases.

If sensitive information is committed, stop sharing the repository, notify the repository owner privately, rotate exposed credentials, and remove the data from Git history before normal work resumes.

## Team credential handling

- Share variable names and setup status in Discord, never secret values.
- Prefer a separate vendor key for each team member. Revoke one person's key when access changes instead of replacing the whole team's key.
- Put shared deployment values directly into the hosting provider's encrypted environment-variable or secret store. For local development, use an access-controlled team vault such as 1Password or Bitwarden.
- Do not send credentials by Discord, email, issue, pull-request comment, document or screenshot.
- Treat every `NEXT_PUBLIC_*` value as public. A Supabase publishable key may be public when Row Level Security is correct, but a Supabase secret key, service token, staff token or provider API key must remain server-side.
- The current static `NEXT_PUBLIC_ARIA_STAFF_TOKEN` flow is for a local synthetic demo only. Replace it with real server-side sign-in/session handling before any internet-facing deployment.

If a credential has appeared in Git history, deletion alone is not sufficient: revoke or rotate it first, update the authorised secret stores, verify the application, and only then resume sharing or deployment.

AI output must be treated as unverified decision support. Final clinical review and triage remain human responsibilities.

