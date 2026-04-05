import discord
from discord import app_commands, ui
import random
import os
import asyncio
import cloudscraper
from datetime import datetime

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

user_tokens = {}
MINES_METHODS = ["Balanced", "Algorithm", "Smart", "Safe", "Full Line"]

def check_active_game_sync(token, game):
    url = f"https://api.bloxflip.com/games/{game}"
    headers = {"x-auth-token": token}
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, headers=headers)
        data = resp.json()
        return data.get("game_active", False)
    except:
        return None

async def check_active_game(token, game):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_active_game_sync, token, game)

class RepeatView(ui.View):
    def __init__(self, embed):
        super().__init__(timeout=600)
        self.embed = embed

    @ui.button(label="🔄 Repeat", style=discord.ButtonStyle.gray)
    async def repeat(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(embed=self.embed, view=RepeatView(self.embed))

@tree.command(name="free-connect", description="Submit your app.rt token")
async def free_connect(interaction: discord.Interaction):
    class TokenModal(ui.Modal, title="app.rt"):
        token = ui.TextInput(label="Paste app.rt", required=True)

        async def on_submit(self, interaction: discord.Interaction):
            user_tokens[interaction.user.id] = self.token.value.strip()
            embed = discord.Embed(title="✅ app.rt Saved", description="Ready! Use /mines or /towers.", color=0x00ff88)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    await interaction.response.send_modal(TokenModal())

@tree.command(name="mines", description="Get a Mines prediction")
async def mines_cmd(interaction: discord.Interaction):
    if interaction.user.id not in user_tokens:
        await interaction.response.send_message("❌ Use /free-connect first.", ephemeral=True)
        return

    await interaction.response.defer()

    token = user_tokens[interaction.user.id]
    active = await check_active_game(token, "mines")

    if active is None:
        await interaction.followup.send("❌ Could not reach BloxFlip. Try again.", ephemeral=True)
        return
    if not active:
        await interaction.followup.send("😭 Mines isn't active. Start a game on BloxFlip first!", ephemeral=True)
        return

    clicks_val = 8
    method = random.choice(MINES_METHODS)
    safe_tiles = []

    if method == "Safe":
        center = [7,8,9,12,13,14,17,18,19]
        safe_tiles = random.sample(center, min(clicks_val, len(center)))
    elif method == "Balanced":
        safe_tiles = random.sample(range(1,26), clicks_val)
    elif method == "Algorithm":
        safe_tiles = sorted(random.sample(range(1,26), clicks_val))
    elif method == "Smart":
        avoid_edges = list(range(6,20))
        safe_tiles = random.sample(avoid_edges, min(clicks_val, len(avoid_edges)))
    elif method == "Full Line":
        lines = [[1,2,3,4,5],[6,7,8,9,10],[11,12,13,14,15],[16,17,18,19,20],[21,22,23,24,25]]
        chosen = random.choice(lines)
        safe_tiles = chosen[:clicks_val] if clicks_val <= 5 else random.sample(range(1,26), clicks_val)

    if len(safe_tiles) < clicks_val:
        safe_tiles = sorted(random.sample(range(1,26), clicks_val))

    grid = ""
    for i in range(25):
        grid += "🤑 " if (i+1) in safe_tiles else "😭 "
        if (i + 1) % 5 == 0:
            grid += "\n"

    embed = discord.Embed(title="💣 Mines Prediction", color=0xff8800)
    embed.add_field(name="Method", value=method, inline=True)
    embed.add_field(name="Safe Tiles", value=f"`{', '.join(map(str, sorted(safe_tiles)))}`", inline=False)
    embed.add_field(name="Grid", value=grid, inline=False)
    embed.set_footer(text="🤑 = Safe Point • 😭 = BOOM")
    embed.timestamp = datetime.now()

    await interaction.followup.send(embed=embed, view=RepeatView(embed))

@tree.command(name="towers", description="Get a Towers prediction")
async def towers_cmd(interaction: discord.Interaction):
    if interaction.user.id not in user_tokens:
        await interaction.response.send_message("❌ Use /free-connect first.", ephemeral=True)
        return

    await interaction.response.defer()

    token = user_tokens[interaction.user.id]
    active = await check_active_game(token, "towers")

    if active is None:
        await interaction.followup.send("❌ Could not reach BloxFlip. Try again.", ephemeral=True)
        return
    if not active:
        await interaction.followup.send("😭 Towers isn't active. Start a game on BloxFlip first!", ephemeral=True)
        return

    levels_val = 8
    method = random.choice(["Safe Method", "Aggressive Method", "Pattern Method"])

    if "safe" in method.lower():
        path = [2] * levels_val
    elif "aggressive" in method.lower():
        path = [random.randint(1, 3) for _ in range(levels_val)]
    else:
        base = [1, 2, 3, 2, 1]
        path = (base * (levels_val // 5 + 2))[:levels_val]

    grid = ""
    for i, col in enumerate(path):
        row = ""
        for c in range(1, 4):
            row += "🤑 " if c == col else "😭 "
        grid += f"Level {i+1}: {row}\n"

    embed = discord.Embed(title="🗼 Towers Prediction", color=0x00ccff)
    embed.add_field(name="Method", value=method, inline=True)
    embed.add_field(name="Grid", value=grid, inline=False)
    embed.set_footer(text="🤑 = Safe Point • 😭 = BOOM")
    embed.timestamp = datetime.now()

    await interaction.followup.send(embed=embed, view=RepeatView(embed))

@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot online: {client.user}")

token = os.getenv("DISCORD_TOKEN")
client.run(token)
