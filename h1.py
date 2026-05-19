import discord
from discord.ext import commands
import requests
import ipaddress

# =========================
# Configuration
# =========================

BOT_TOKEN = "MTUwNjE5NzgzMDA3NzkxMTA4MQ.GgbOH8.hLM4IdYYzxP98l8QF3vTONNfdTP73aUZoWI-Oc"
PREFIX = "."

# =========================
# Discord Setup
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# =========================
# Utility Functions
# =========================

def validate_ip(ip):
    """Validate IPv4/IPv6 address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def check_idrac_response(response):
    """Analyze IDRAC HTTP response."""

    if response.status_code == 200:
        try:
            data = response.json()

            if data.get("success") is True:
                return (
                    "RESPONDING",
                    data.get("message", "Authentication endpoint responded."),
                )

            elif data.get("event") == "auth":
                return (
                    "RESPONDING",
                    "Authentication endpoint returned valid event response.",
                )

            else:
                return (
                    "UNKNOWN RESPONSE",
                    f"HTTP 200 OK returned. Message: {data.get('message', 'Unknown')}",
                )

        except requests.exceptions.JSONDecodeError:

            text = response.text.lower()

            if "idrac" in text:
                return (
                    "RESPONDING",
                    "IDRAC web interface detected.",
                )

            return (
                "UNKNOWN RESPONSE",
                "HTTP 200 OK but no recognizable IDRAC indicators found.",
            )

    elif response.status_code == 401:
        return (
            "SECURE",
            "Authentication required (401 Unauthorized).",
        )

    elif response.status_code == 403:
        return (
            "SECURE",
            "Access denied (403 Forbidden).",
        )

    elif response.status_code == 404:
        return (
            "NOT FOUND",
            "Endpoint does not exist.",
        )

    elif response.status_code == 503:
        return (
            "UNAVAILABLE",
            "Service unavailable.",
        )

    return (
        "UNKNOWN",
        f"HTTP Status Code: {response.status_code}",
    )


def make_request(ip):
    """Try HTTPS first, then HTTP."""

    urls = [
        f"https://{ip}/event/auth/",
        f"http://{ip}/event/auth/",
    ]

    for url in urls:
        try:
            response = requests.get(
                url,
                timeout=10,
                verify=False,
            )
            return response, url

        except requests.exceptions.RequestException:
            continue

    return None, None


# Disable HTTPS warnings
requests.packages.urllib3.disable_warnings()

# =========================
# Events
# =========================

@bot.event
async def on_ready():

    print("===================================")
    print(f"Logged in as: {bot.user}")
    print("===================================")

    await bot.change_presence(
        activity=discord.Game(
            name=f"{PREFIX}help_menu | iDRAC Scanner"
        )
    )


# =========================
# Commands
# =========================

@bot.command(name="help_menu")
async def help_menu(ctx):

    embed = discord.Embed(
        title="🛠️ iDRAC Scanner Bot",
        description="Available commands",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name=f"{PREFIX}scan <ip>",
        value="Scan an iDRAC endpoint and analyze the response.",
        inline=False,
    )

    embed.add_field(
        name=f"{PREFIX}authcheck <ip>",
        value="Check authentication endpoint behavior.",
        inline=False,
    )

    embed.add_field(
        name=f"{PREFIX}help_menu",
        value="Show this help message.",
        inline=False,
    )

    await ctx.send(embed=embed)


# =========================
# Scan Command
# =========================

@bot.command(name="scan")
async def scan(ctx, ip: str = None):

    if ip is None:
        await ctx.send(
            f"❌ Usage: `{PREFIX}scan 192.168.1.1`"
        )
        return

    if not validate_ip(ip):
        await ctx.send("❌ Invalid IP address.")
        return

    msg = await ctx.send(
        f"🔎 Scanning `{ip}` ..."
    )

    try:

        response, used_url = make_request(ip)

        if response is None:
            await msg.edit(
                content=f"🚫 Could not connect to `{ip}`"
            )
            return

        status, detail = check_idrac_response(response)

        if status == "RESPONDING":
            color = discord.Color.green()
        elif status == "SECURE":
            color = discord.Color.red()
        else:
            color = discord.Color.orange()

        embed = discord.Embed(
            title=f"🛡️ Scan Results - {ip}",
            color=color,
        )

        embed.add_field(
            name="Status",
            value=status,
            inline=False,
        )

        embed.add_field(
            name="Detail",
            value=detail,
            inline=False,
        )

        embed.add_field(
            name="Endpoint",
            value=used_url,
            inline=False,
        )

        embed.set_footer(
            text="iDRAC Response Analyzer"
        )

        await msg.edit(content=None, embed=embed)

    except Exception as e:
        await msg.edit(
            content=f"💥 Error: `{e}`"
        )


# =========================
# Auth Check Command
# =========================

@bot.command(name="authcheck")
async def authcheck(ctx, ip: str = None):

    if ip is None:
        await ctx.send(
            f"❌ Usage: `{PREFIX}authcheck 192.168.1.1`"
        )
        return

    if not validate_ip(ip):
        await ctx.send("❌ Invalid IP address.")
        return

    await ctx.send(
        f"🔐 Checking authentication endpoint on `{ip}`..."
    )

    try:

        response, used_url = make_request(ip)

        if response is None:
            await ctx.send(
                f"🚫 Could not connect to `{ip}`"
            )
            return

        embed = discord.Embed(
            title=f"🔐 Authentication Check - {ip}",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="HTTP Status",
            value=str(response.status_code),
            inline=True,
        )

        embed.add_field(
            name="Endpoint",
            value=used_url,
            inline=False,
        )

        preview = response.text[:300]

        if len(response.text) > 300:
            preview += "..."

        embed.add_field(
            name="Response Preview",
            value=f"```{preview}```",
            inline=False,
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(
            f"💥 Error: `{e}`"
        )


# =========================
# Run Bot
# =========================

if __name__ == "__main__":

    if BOT_TOKEN == "YOUR_BOT_TOKEN":

        print("===================================")
        print("ERROR: Replace YOUR_BOT_TOKEN")
        print("===================================")

    else:
        try:
            bot.run(BOT_TOKEN)

        except discord.LoginFailure:

            print("===================================")
            print("INVALID BOT TOKEN")
            print("===================================")
