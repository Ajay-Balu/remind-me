# Security Policy

Remind Me runs locally, has no network features and doesn't collect any data.
It stores its settings in `%APPDATA%\RemindMe` and, if you enable "Start with Windows",
adds one value under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

If you find a security issue (for example, a way to make the app run untrusted code
through a sprite pack or the config file), please **don't open a public issue**.
Use GitHub's "Report a vulnerability" (Security → Advisories) on this repository instead.
