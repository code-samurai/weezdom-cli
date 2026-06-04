# Security

## Credential storage

`weezdom` stores your personal API key in plain text at `~/.weezdom/config.yaml`. The file is created with `0600` permissions (owner read/write only) and the parent directory with `0700` permissions. No other user on the same machine can read your key.

If you need stronger protection (e.g. on a shared machine), store the key via your OS keychain and set it only for the duration of a session:

```bash
weezdom config set api_key $(keyring get weezdom api_key)
```

## API key hygiene

- **Never pass your API key as a CLI argument** — use `weezdom auth login` which prompts with hidden input, not `weezdom config set api_key <key>` which can leak the value to shell history and process listings.
- **Revoke unused keys** via `weezdom auth logout` or the Weezdom Settings page.
- All requests are sent over HTTPS. The `api_url` config value is validated to require `https://`.

## Reporting a vulnerability

Please email **security@weezdom.ai** with a description of the issue. Do not open a public GitHub issue for security vulnerabilities.
