# Minecraft Clan Spawner Price Bot

A small Python Discord bot that maintains one editable spawner price board. Prices and enabled/disabled states are stored in a local SQLite database, so they survive bot restarts.

## Commands

- `/setup_board channel:#spawner-prices` — creates the board and remembers that message.
- `/price` — choose a spawner, Buy/Sell, and enter a price like `13.8m`, `450k`, or `2,000,000`. Setting a price also enables that side.
- `/availability` — independently enable or disable buying/selling for a spawner.
- `/prices` — show the current board privately.
- `/refresh_board` — manually refresh the saved board.

Initial defaults match the example: Skeleton buy 10m / sell 13.8m; Creeper buy 4.1m; Iron buy 13.5m; Blaze buy 4m; Piglin buy 3.5m; Cow buy 4m. All other sides start disabled.

## 1. Create the Discord application

1. Open the Discord Developer Portal: https://discord.com/developers/applications
2. Click **New Application**, give it a name, then open **Bot** and create/reset its bot token.
3. Copy the token somewhere private. Never paste it into chat or commit it to GitHub.
4. Open **OAuth2 → URL Generator**. Select `bot` and `applications.commands`.
5. Under bot permissions, select **View Channels**, **Send Messages**, **Embed Links**, and **Read Message History**.
6. Open the generated URL and add the bot to your server.

## 2. Get your server ID

In Discord, enable **User Settings → Advanced → Developer Mode**. Right-click your server icon/name and choose **Copy Server ID**.

## 3. Install and configure (Windows)

Install Python 3.10 or newer from https://www.python.org/downloads/ and enable the option to add Python to PATH during installation.

1. Extract this folder.
2. Copy `.env.example` and name the copy `.env`.
3. Open `.env` in Notepad and set `DISCORD_TOKEN` and `GUILD_ID`.
4. Optional: set `ADMIN_ROLE_ID` to the ID of the clan role allowed to edit prices. If it remains `0`, only members with **Manage Server** or **Administrator** can change prices.
5. Open Command Prompt in this folder and run:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py bot.py
```

Keep that window open while the bot should be online.

## 4. Create the board

In your Discord server, run `/setup_board` and select `#spawner-prices` (or whichever channel you want). The bot creates one message and remembers its ID. Future commands edit that message rather than posting new ones.

## 5. Change prices

Example: `/price` → Skeleton → Sell → `15m`

To stop selling Cow: `/availability` → Cow → Sell → `False`.

To start selling Cow later, set a sell price with `/price` (which automatically enables selling), or use `/availability` to enable it again. If you enable a side without setting a price, it may display the previous saved price; set the price first if that is not desired.

## Hosting

- **Easiest for testing:** run it on your own PC. The bot goes offline when the PC sleeps or the program closes.
- **Always online:** deploy it to a small Python-capable host or VPS. Keep the `.env` token secret and persist the `spawner_prices.sqlite3` file. Do not use ephemeral storage unless you back up the database.

## Notes

- Slash commands may take a short moment to appear after the bot starts.
- `GUILD_ID` is for your own server and helps commands sync quickly during setup.
- The bot only handles the Discord price board. It does not connect to Minecraft or verify in-game prices.
