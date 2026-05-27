import os
import sqlite3
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from config import KNOWN_DEVICES

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "office.db")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_presence():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p1.mac, p1.name, p1.event, p1.timestamp
        FROM presence_log p1
        INNER JOIN (
            SELECT mac, MAX(timestamp) as max_ts
            FROM presence_log
            GROUP BY mac
        ) p2 ON p1.mac = p2.mac AND p1.timestamp = p2.max_ts
    """)
    rows = cursor.fetchall()
    conn.close()
    return {row["mac"]: dict(row) for row in rows}


def format_iso_timestamp(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts_str


@bot.event
async def on_ready():
    print(f"[Discord Bot] Logged in as {bot.user.name}")
    if not report_scheduler.is_running():
        report_scheduler.start()


@bot.command(name="status")
async def cmd_status(ctx):
    presence = get_current_presence()
    online_members = [
        name for mac, name in KNOWN_DEVICES.items()
        if presence.get(mac) and presence[mac]["event"] == "online"
    ]
    if online_members:
        await ctx.send(f"**Aktualnie w biurze ({len(online_members)}):** {', '.join(online_members)}")
    else:
        await ctx.send("**Aktualnie w biurze (0):** Brak wykrytych urządzeń.")


@bot.command(name="today")
async def cmd_today(ctx):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT name
        FROM presence_log
        WHERE event = 'online' AND timestamp LIKE ?
    """, (f"{today_str}%",))
    rows = cursor.fetchall()
    conn.close()
    present_today = [row["name"] for row in rows]
    if present_today:
        await ctx.send(f"**Obecni dzisiaj ({len(present_today)}):** {', '.join(present_today)}")
    else:
        await ctx.send("**Obecni dzisiaj (0):** Nikt jeszcze nie pojawił się w biurze.")


@bot.command(name="history")
async def cmd_history(ctx, *, arg: str = None):
    if not arg:
        await ctx.send("Podaj imię pracownika lub adres MAC. Przykład: `!history Ivan-PC`")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    if ":" in arg:
        cursor.execute("""
            SELECT name, event, timestamp
            FROM presence_log
            WHERE mac = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (arg.lower(),))
    else:
        cursor.execute("""
            SELECT name, event, timestamp
            FROM presence_log
            WHERE name LIKE ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (f"%{arg}%",))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await ctx.send(f"Brak wpisów w historii dla: {arg}")
        return

    lines = []
    for r in rows:
        event_icon = "[+] ONLINE" if r["event"] == "online" else "[-] OFFLINE"
        ts = format_iso_timestamp(r["timestamp"])
        lines.append(f"`{ts}` - **{r['name']}** -> {event_icon}")

    await ctx.send(f"**Ostatnie 10 zdarzeń dla {arg}:**\n" + "\n".join(lines))


@bot.command(name="stats")
async def cmd_stats(ctx):
    conn = get_db_connection()
    cursor = conn.cursor()
    stats_list = []
    for mac, name in KNOWN_DEVICES.items():
        cursor.execute(
            "SELECT COUNT(*) as count FROM presence_log WHERE mac = ? AND event = 'online'",
            (mac,)
        )
        online_count = cursor.fetchone()["count"]
        cursor.execute(
            "SELECT timestamp FROM presence_log WHERE mac = ? ORDER BY timestamp DESC LIMIT 1",
            (mac,)
        )
        last_row = cursor.fetchone()
        last_seen = format_iso_timestamp(last_row["timestamp"]) if last_row else "Nigdy"
        stats_list.append(f"**{name}**: wejścia: `{online_count}`, ostatnio: `{last_seen}`")
    conn.close()
    await ctx.send("**Statystyki obecności:**\n" + "\n".join(stats_list))


@bot.command(name="missing")
async def cmd_missing(ctx):
    presence = get_current_presence()
    missing_members = [
        name for mac, name in KNOWN_DEVICES.items()
        if not presence.get(mac) or presence[mac]["event"] == "offline"
    ]
    if missing_members:
        await ctx.send(f"**Nieobecni w biurze ({len(missing_members)}):** {', '.join(missing_members)}")
    else:
        await ctx.send("**Wszyscy są w biurze.**")


last_sent_reports = {"morning": None, "evening": None}


@tasks.loop(seconds=30)
async def report_scheduler():
    if not CHANNEL_ID:
        return
    try:
        channel = await bot.fetch_channel(int(CHANNEL_ID))
    except Exception as e:
        print(f"[Discord Bot] channel error: {e}")
        return

    now = datetime.now()
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    if time_str == "08:00" and last_sent_reports["morning"] != date_str:
        last_sent_reports["morning"] = date_str
        presence = get_current_presence()
        online = [name for mac, name in KNOWN_DEVICES.items()
                  if presence.get(mac) and presence[mac]["event"] == "online"]
        await channel.send(
            f"[RAPORT] **Poranny raport obecności (08:00)**\nAktualnie obecni: {', '.join(online) or 'Brak'}"
        )

    elif time_str == "17:00" and last_sent_reports["evening"] != date_str:
        last_sent_reports["evening"] = date_str
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT name
            FROM presence_log
            WHERE event = 'online' AND timestamp LIKE ?
        """, (f"{today_str}%",))
        rows = cursor.fetchall()
        conn.close()
        present = [row["name"] for row in rows]
        await channel.send(
            f"[RAPORT] **Wieczorne podsumowanie dnia (17:00)**\nOsoby obecne dzisiaj: {', '.join(present) or 'Brak'}"
        )


if __name__ == "__main__":
    if not TOKEN:
        print("[Error] DISCORD_TOKEN not set in .env")
    else:
        bot.run(TOKEN)
