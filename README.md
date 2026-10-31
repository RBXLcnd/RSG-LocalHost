# RSG LocalHost

Desktop app to host and join Roblox Studio Team Test sessions over the internet through a tunnel, with an optional **24/7 auto-cycle** and live server status in Discord.

UI redesigned with the RSG identity. Based on the original work by **s0m3thing_matters** — the logic in `app/core` is unchanged from the original.

## Download

Get the latest `RSG LocalHost.exe` from the [Releases](../../releases/latest) page and run it. No installation or Python needed.

Windows may show a "Windows protected your PC" warning because the app is not code-signed. Click **More info → Run anyway**. The exe is built by GitHub Actions straight from this source; the SHA-256 of every build is in the release notes and you can check it on VirusTotal.

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
