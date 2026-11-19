# Changelog

All notable changes to this project are listed here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.1] - 2026-11-19
### Fixed
- The app kept running in the background while the screen was locked or the laptop lid was closed. It now goes quiet when the screen is locked, the display turns off (lid closed), the PC goes to sleep or the screensaver is running. In that state there are no reminders, no voice and no mouse nudge, keep-awake is released so Windows can sleep, and the pet's animation stops.
- After you unlock or resume, it waits about 20 seconds before showing any reminders that came due, and the eye, posture and break timers restart.

## [1.0.0] - 2026-11-16
First public release.

### Added
- Water, eye-rest (20-20-20), posture and break reminders with Done / Snooze, break countdown and pause.
- Away detection: reminders wait while you're away, and being away long enough counts as a break.
- Desktop pet with three original illustrated avatars: Buddy (Golden Retriever), Mochi (Persian cat) and Bolt (robot).
- Pet behaviours: walk, nap, sleep while you're away, angry on click, laugh on wiggle, drag & drop, follow mouse, reactions to reminders.
- Speech bubbles with reminder buttons, plus spoken reminders using Windows voices (choose voice, speed and volume).
- Gravity mode: the pet lives on the taskbar and falls back down when dropped. It also keeps a taskbar garden: it digs, plants and waters, and the plants grow into flowers.
- PNG sprite-pack support for custom avatars.
- Corner toast notifications (light/dark, configurable position).
- Optional idle mouse nudge / keep-awake, hidden behind the ⚙ icon in Settings.
- Start with Windows, single-instance guard, PyInstaller build script.
