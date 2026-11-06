# RSG LocalHost

Desktop app to host and join Roblox Studio Team Test sessions over the internet through a tunnel, with an optional **24/7 auto-cycle** and live server status in Discord.

UI redesigned with the RSG identity. Based on the original work by **s0m3thing_matters** — the logic in `app/core` is unchanged from the original.

## Download

Get the latest `RSG-LocalHost-Setup.exe` from the [Releases](../../releases/latest) page and run it. It installs for your user only (no admin needed) and you do not need Python.

Windows may show a "Windows protected your PC" warning because the app is not code-signed. Click **More info → Run anyway**. The installer is built by GitHub Actions straight from this source; the SHA-256 of every build is in the release notes and you can check it on VirusTotal.

## Your data and updates

Settings, profiles, session history, theme, language and the Discord sign-in are stored in `%APPDATA%\RSG LocalHost`, not next to the program. To update, just run the new installer; nothing is lost. Data saved by an older version next to the exe is moved over automatically the first time the new version runs from the same folder. The uninstaller asks before deleting this folder.

The Discord key is stored encrypted with Windows (DPAPI), so only your Windows account can read it. If you copy the data folder to another account or computer, you just sign in to Discord again.

**Backup:** Settings > Backup exports your profiles, tunnels, 24/7 options, theme and language to a `.json` file and imports it again (for example on another PC). The Discord key and the Studio path are never included.

**Look:** Settings > Appearance switches between dark and light mode and lets you pick the accent color (seven presets or any custom color). Background themes work in both modes.

**Invite links:** the invite message has an `rsg://join/host:port` link. Opening it (or pasting it into the Join tunnel field) loads the address into the Join page; you still press Join. The installer registers the protocol for your Windows user, and the app re-registers it on start. Note: Discord does not make custom links like this clickable, so people can copy the link (or just the host:port) and paste it into the app.

## Language

The app is in English. Click the language button in the top right (EN / PT / BR / ES) and pick English, Português, Português (Brasil) or Español to switch the whole interface. The choice is remembered. Console logs stay in English so they are easy to share when asking for help.

## Requirements

- Windows 10 or later
- Roblox Studio installed (the app finds it automatically)
- A tunnel (UDP) for remote play. Not needed for local testing.

## Hosting a server

1. In **Create session**, sign in with Discord: run `/host-login` in the RSG Discord server, the bot sends you a private key, paste it into *Sign in with Discord*.
2. Fill in your **User ID**, **Tunnel address** (`hostname:port`) and **Port** (default `55555`, same as in your tunnel settings).
3. Optional: turn on **24/7 auto-cycle**, pick online/pause hours and a map rotation, choose a **Server name** (3–24 characters).
4. Click **Launch server**. When the status reads **SERVER IS LIVE**, share your tunnel address with players.

Tunnel setup: **Port** `55555`, **Protocol** `UDP`.

`/server-status` in Discord lists all servers. `/host-logout` revokes your key.

## Joining a server

Click **Join**, enter the host's tunnel address (`hostname:port`) and connect. Studio opens as a client.

## Run from source

```
pip install -r requirements.txt
python main.py
```

Build the exe locally with `build.bat`.

## Releasing a new version

1. Bump `__version__` in `app/__init__.py` and add an entry in `app/core/changelog.py`.
2. Commit, then `git tag v2.3.0 && git push origin v2.3.0`.
3. GitHub Actions builds the exe and publishes the release.

## License and credits

Licensed under **CC BY-NC 4.0** (see `LICENSE.md`): free to use and share with attribution, **no commercial use**.

- Original app and logic: **s0m3thing_matters** — https://discord.gg/H3K2xeU96A
- UI redesign and 24/7 / Discord status additions: RSG

Not affiliated with or endorsed by Roblox Corporation.
