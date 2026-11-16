# Project Rules

## Prompt Logging
Every time you receive a new instruction or prompt, append it to prompts.txt in the project root with a timestamp (ISO 8601) and a brief summary of what you did in response. Create the file if it doesn't exist. Keep this log updated throughout all sessions.

## Engineering Rules
- Keep AI outputs structured, validated, and explainable.
- Never merge requests or change a product decision without explicit human approval.
- Keep prioritisation scoring deterministic and separate from LLM-generated analysis.
- Add or update tests for meaningful behaviour changes.
- Never commit API keys, credentials, or customer secrets.
