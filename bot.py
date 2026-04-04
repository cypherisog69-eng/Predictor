import discord
from discord import app_commands, ui
import random
import os
from datetime import datetime

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

user_tokens = {}

MINES_METHODS = ["Balanced", "Algorithm", "Smart", "Safe", "Full Line"]

class RepeatView(ui.View):
    def __init__(self, embed):
        super().__init__(timeout=600)
        self.embed = embed

    @ui.button(label="🔄 Repeat", style=discord.ButtonStyle.gray)
    async def repeat(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(embed=self.embed, view=RepeatView(self.embed))

class GameView(ui.View):
    @ui.button(label="🗼 Towers", style=discord.ButtonStyle.blurple)
    async def towers(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TowersModal())

    @ui.button(label="💣 Mines", style=discord.ButtonStyle.red)
    async def mines(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(MinesModal())

class TowersModal(ui.Modal, title="Towers"):
    mode = ui.TextInput(label="Mode", default="easy")
    bet = ui.TextInput(label="Bet", default="10")
    levels = ui.TextInput(label="Levels", default="8")

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id not in user_tokens:
            await interaction.response.send_message("No app.rt found.", ephemeral=True)
            return

        mode = self.mode.value.strip().lower().capitalize()
        if mode not in ["Easy", "Normal", "Hard"]:
            mode = "Easy"

        try:
            bet_val = int(self.bet.value)
            levels_val = int(self.levels.value)
        except:
            await interaction.response.send_message("Use numbers only.", ephemeral=True)
            return

        levels_val = max(3, min(levels_val, 12))
        method = random.choice(["Safe Method", "Aggressive Method", "Pattern Method"])

        if "safe" in method.lower():
            path = [2] * levels_val
        elif "aggressive" in method.lower():
            path = [random.randint(1, 3) for _ in range(levels_val)]
        else:
            base = [1, 2, 3, 2, 1]
            path = (base * (levels_val // 5 + 2))[:levels_val]

        path_str = " → ".join(f"Column {p}" for p in path)

        embed = discord.Embed(title=f"Towers • {mode}", color=0x00ccff)
        embed.add_field(name="Bet", value=f"{bet_val}", inline=True)
        embed.add_field(name="Method", value=method, inline=True)
        embed.add_field(name="Path", value=path_str, inline=False)
        embed.timestamp = datetime.now()

        await interaction.response.send_message(embed=embed, view=RepeatView(embed))

class MinesModal(ui.Modal, title="Mines"):
    clicks = ui.TextInput(label="Safe clicks", default="8")

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id not in user_tokens:
            await interaction.response.send_message("No app.rt found.", ephemeral=True)
            return

        try:
            clicks_val = int(self.clicks.value)
        except:
            await interaction.response.send_message("Enter number only.", ephemeral=True)
            return

        clicks_val = max(1, min(clicks_val, 15))
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
            grid += "🟩 " if (i+1) in safe_tiles else "⬛ "
            if (i + 1) % 5 == 0:
                grid += "\n"

        embed = discord.Embed(title="Mines", color=0xff8800)
        embed.add_field(name="Clicks", value=str(clicks_val), inline=True)
        embed.add_field(name="Method", value=method, inline=True)
        embed.add_field(name="Tiles", value=f"`{', '.join(map(str, sorted(safe_tiles)))}`", inline=False)
        embed.add_field(name="Grid", value=grid, inline=False)
        embed.timestamp = datetime.now()

        await interaction.response.send_message(embed=embed, view=RepeatView(embed))

@tree.command(name="free-connect", description="Submit app.rt")
async def free_connect(interaction: discord.Interaction):
    class TokenModal(ui.Modal, title="app.rt"):
        token = ui.TextInput(label="Paste app.rt", required=True)

        async def on_submit(self, interaction: discord.Interaction):
            user_tokens[interaction.user.id] = self.token.value.strip()
            embed = discord.Embed(title="app.rt Saved", description="Ready.", color=0x00ff88)
            await interaction.response.send_message(embed=embed, view=GameView(), ephemeral=False)

    await interaction.response.send_modal(TokenModal())

@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot online: {client.user}")

token = os.getenv("DISCORD_TOKEN")
client.run(token)
