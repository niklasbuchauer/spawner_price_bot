import os
import sqlite3
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0") or 0)
DB_PATH = Path(os.getenv("DB_PATH", "spawner_prices.sqlite3"))

SPAWNERS = ["Skeleton", "Creeper", "Iron", "Blaze", "Piglin", "Cow"]
SIDES = ["buy", "sell"]

DEFAULTS = {
    "Skeleton": {"buy": ("10m", True), "sell": ("13.8m", True)},
    "Creeper": {"buy": ("4.1m", True), "sell": ("", False)},
    "Iron": {"buy": ("13.5m", True), "sell": ("", False)},
    "Blaze": {"buy": ("4m", True), "sell": ("", False)},
    "Piglin": {"buy": ("3.5m", True), "sell": ("", False)},
    "Cow": {"buy": ("4m", True), "sell": ("", False)},
}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            spawner TEXT NOT NULL,
            side TEXT NOT NULL,
            price TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (spawner, side)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    for spawner, sides in DEFAULTS.items():
        for side, (price, enabled) in sides.items():
            conn.execute(
                "INSERT OR IGNORE INTO prices (spawner, side, price, enabled) VALUES (?, ?, ?, ?)",
                (spawner, side, price, int(enabled))
            )
    conn.commit()
    return conn

def get_price(spawner, side):
    with db() as conn:
        row = conn.execute(
            "SELECT price, enabled FROM prices WHERE spawner=? AND side=?",
            (spawner, side)
        ).fetchone()
    return row[0], bool(row[1])

def set_price(spawner, side, price):
    with db() as conn:
        conn.execute(
            "UPDATE prices SET price=?, enabled=1 WHERE spawner=? AND side=?",
            (price, spawner, side)
        )
        conn.commit()

def set_enabled(spawner, side, enabled):
    with db() as conn:
        conn.execute(
            "UPDATE prices SET enabled=? WHERE spawner=? AND side=?",
            (int(enabled), spawner, side)
        )
        conn.commit()

def get_setting(key):
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_setting(key, value):
    with db() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value))
        )
        conn.commit()

def authorized(interaction: discord.Interaction) -> bool:
    member = interaction.user
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    if ADMIN_ROLE_ID:
        return any(role.id == ADMIN_ROLE_ID for role in member.roles)
    return False

def admin_only():
    async def predicate(interaction: discord.Interaction):
        if not authorized(interaction):
            raise app_commands.CheckFailure(
                "Nur Server-Manager oder Mitglieder mit der eingerichteten Preis-Manager-Rolle dürfen Preise ändern."
            )
        return True
    return app_commands.check(predicate)

def build_board() -> discord.Embed:
    embed = discord.Embed(
        title="Spawner-Markt",
        description="Aktuelle Spawner-Preise des Clans. Preise werden automatisch aktualisiert.",
        color=discord.Color.blurple()
    )
    for spawner in SPAWNERS:
        buy_price, buy_enabled = get_price(spawner, "buy")
        sell_price, sell_enabled = get_price(spawner, "sell")
        buy_text = buy_price if buy_enabled and buy_price else "Kein Ankauf"
        sell_text = sell_price if sell_enabled and sell_price else "Kein Verkauf"
        embed.add_field(
            name=spawner,
            value=f"**Kauf:** {buy_text}\n**Verkauf:** {sell_text}",
            inline=True
        )
    embed.set_footer(text="Bei Fragen zu einem Preis wende dich an die Clan-Leitung.")
    return embed

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def update_board():
    channel_id = get_setting("board_channel_id")
    message_id = get_setting("board_message_id")
    if not channel_id or not message_id:
        return False
    try:
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            channel = await bot.fetch_channel(int(channel_id))
        message = await channel.fetch_message(int(message_id))
        await message.edit(embed=build_board())
        return True
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
        print(f"Preistafel konnte nicht aktualisiert werden: {exc}")
        return False

@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()
        print(f"Angemeldet als {bot.user}. Slash-Befehle synchronisiert.")
    except Exception as exc:
        print(f"Synchronisierung der Befehle fehlgeschlagen: {exc}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        message = str(error) or "Du darfst diesen Befehl nicht verwenden."
    elif isinstance(error, app_commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
        message = "Ich habe keine Berechtigung für diesen Kanal. Erlaube mir dort Kanäle sehen, Nachrichten senden und Links einbetten."
    else:
        print(f"Befehl fehlgeschlagen: {error!r}")
        message = "Der Befehl ist fehlgeschlagen. Prüfe, ob ich auf den ausgewählten Kanal zugreifen kann."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="setup_board", description="Erstellt oder verschiebt die dauerhafte Spawner-Preistafel")
@admin_only()
@app_commands.describe(channel="Der Kanal für die Spawner-Preistafel")
async def setup_board(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    try:
        message = await channel.send(embed=build_board())
    except discord.Forbidden:
        await interaction.followup.send(
            "Ich kann in diesem Kanal nicht posten. Erlaube mir Kanäle sehen, Nachrichten senden und Links einbetten, dann versuche es erneut.",
            ephemeral=True
        )
        return
    except discord.HTTPException as exc:
        print(f"Spawner-Preistafel konnte nicht erstellt werden: {exc}")
        await interaction.followup.send(
            "Discord hat die Nachricht abgelehnt. Prüfe meine Kanalberechtigungen und versuche es erneut.",
            ephemeral=True
        )
        return
    set_setting("board_channel_id", channel.id)
    set_setting("board_message_id", message.id)
    await interaction.followup.send(
        f"Preistafel in {channel.mention} erstellt. Künftige Änderungen aktualisieren diese Nachricht automatisch.",
        ephemeral=True
    )

@bot.tree.command(name="price", description="Ändert den Kauf- oder Verkaufspreis eines Spawners")
@admin_only()
@app_commands.describe(
    spawner="Welcher Spawner",
    side="Kauf- oder Verkaufspreis",
    price="Preis, zum Beispiel 13.8m oder 450k"
)
@app_commands.choices(
    spawner=[app_commands.Choice(name=s, value=s) for s in SPAWNERS],
    side=[app_commands.Choice(name="Kaufen", value="buy"), app_commands.Choice(name="Verkaufen", value="sell")]
)
async def price(
    interaction: discord.Interaction,
    spawner: app_commands.Choice[str],
    side: app_commands.Choice[str],
    price: str
):
    price = price.strip()
    if not price or len(price) > 30 or "\n" in price:
        await interaction.response.send_message("Gib einen kurzen, gültigen Preis ein, zum Beispiel `13.8m`, `450k` oder `2,000,000`.", ephemeral=True)
        return
    set_price(spawner.value, side.value, price)
    updated = await update_board()
    suffix = "Die Preistafel wurde automatisch aktualisiert." if updated else "Preis gespeichert. Erstelle die Tafel zuerst mit `/setup_board`."
    await interaction.response.send_message(
        f"{spawner.value}: {side} auf **{price}** gesetzt. {suffix}",
        ephemeral=True
    )

@bot.tree.command(name="availability", description="Aktiviert oder deaktiviert Kauf/Verkauf eines Spawners")
@admin_only()
@app_commands.describe(
    spawner="Welcher Spawner",
    side="Kauf oder Verkauf",
    enabled="Legt fest, ob der Clan diesen Spawner kauft/verkauft"
)
@app_commands.choices(
    spawner=[app_commands.Choice(name=s, value=s) for s in SPAWNERS],
    side=[app_commands.Choice(name="Kaufen", value="buy"), app_commands.Choice(name="Verkaufen", value="sell")]
)
async def availability(
    interaction: discord.Interaction,
    spawner: app_commands.Choice[str],
    side: app_commands.Choice[str],
    enabled: bool
):
    set_enabled(spawner.value, side.value, enabled)
    updated = await update_board()
    state = "aktiviert" if enabled else "deaktiviert"
    suffix = "Die Preistafel wurde automatisch aktualisiert." if updated else "Gespeichert. Erstelle die Tafel mit `/setup_board`."
    await interaction.response.send_message(
        f"{spawner.value}: {side.value} ist jetzt **{state}**. {suffix}",
        ephemeral=True
    )

@bot.tree.command(name="prices", description="Zeigt die aktuellen Spawner-Preise")
async def prices(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_board(), ephemeral=True)

@bot.tree.command(name="refresh_board", description="Aktualisiert die bestehende Spawner-Preistafel")
@admin_only()
async def refresh_board(interaction: discord.Interaction):
    updated = await update_board()
    if updated:
        await interaction.response.send_message("Preistafel aktualisiert.", ephemeral=True)
    else:
        await interaction.response.send_message(
            "Ich konnte die gespeicherte Preistafel nicht finden. Führe `/setup_board` erneut aus und wähle den Kanal aus.",
            ephemeral=True
        )

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")

bot.run(TOKEN)
