# Contributing to Remind Me

Thanks for wanting to help! Bug fixes, new avatars, translations and UX polish are all welcome.

## Getting set up
```bat
git clone https://github.com/Ajay-Balu/remind-me.git
cd remind-me
py -m pip install -r requirements-dev.txt
py run.pyw          :: runs with a console so you can see errors
ruff check .        :: lint before you commit
```
Errors are also logged to `%APPDATA%\RemindMe\remindme.log`.

Not on Windows? The UI also runs under Linux with Xvfb, with the Windows-only parts turned into no-ops. See [CLAUDE.md](CLAUDE.md#testing-on-linux--ci-no-windows).

## Pull requests
1. Fork the repo and create a branch from `main`.
2. Keep changes focused, one feature or fix per PR.
3. Run `ruff check .` and test the app by hand on Windows if you can. Mention anything you couldn't test.
4. For visual changes, include a screenshot or GIF.
5. If you change an illustrated avatar's drawing, bump its `VERSION` so cached frames refresh.
6. Add a line to `CHANGELOG.md` under an "Unreleased" heading.

## Code guidelines
- Python 3.10+, standard library + Pillow + pystray only. Please discuss before adding a dependency.
- Windows API calls go in `remindme/winapi.py` with a non-Windows fallback.
- Never touch Tk from the tray thread. Use `App.call(...)`.
- More architecture notes are in [CLAUDE.md](CLAUDE.md).

## Adding an avatar
- **As art:** make a PNG sprite pack (see `assets/avatars/_template/README.txt`). Only submit art you created or that has a compatible licence, and include the licence or credit in the pack folder.
- **In code:** subclass `ImageAvatar` (see `remindme/pet/dog.py`) and register it in `remindme/pet/avatars.py`.
- Avatars must be original. Please don't submit copies of trademarked characters, mascots or commercial product designs.

## Reporting bugs
Open an issue with your Windows version, how you ran it (source or exe), the steps to reproduce it and the relevant part of `remindme.log`.

## Code of conduct
Be kind and respectful. Harassment or discrimination of any kind isn't tolerated.
