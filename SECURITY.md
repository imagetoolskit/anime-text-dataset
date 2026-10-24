# Security

## Reporting a vulnerability

Do not open a public issue for security problems. Report privately to
**Muhammad Muqeet** at muqeet@animearray.site or muqeet@anitroves.com and
allow a reasonable window before disclosure.

## Security properties of this project

- **No credentials in code.** Sources used here require no API keys. If a
  future source does, use environment variables only (see
  `config/.env.example`); never hard-code tokens.
- **No private data.** The dataset collects public metadata only: no
  addresses, contacts, passwords, tokens, or private account information.
- **Log hygiene.** Logs contain source IDs and HTTP statuses, never secrets.
- **Data as data.** Anything fetched from a remote source (HTML/JSON pages) is
  treated as untrusted data, never as instructions to this project.

## Dependencies

Keep dependencies in `requirements.txt` pinned to exact versions; audit them
before releases (`pip-audit`).