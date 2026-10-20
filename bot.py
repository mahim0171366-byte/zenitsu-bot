import discord
from discord.ext import commands
import yt_dlp
import asyncio
import re
import random
from datetime import timedelta

# --- Intent Configuration ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="z!", intents=intents)

# --- Music Engine Configuration ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# --- Interactive Music Control Buttons View ---
class MusicControls(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
            await interaction.response.send_message("⏸️ Music paused!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No music is currently playing.", ephemeral=True)

    @discord.ui.button(label="Resume", style=discord.ButtonStyle.success, emoji="▶️")
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_paused():
            self.ctx.voice_client.resume()
            await interaction.response.send_message("▶️ Music resumed!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Music is not paused.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.primary, emoji="⏭️")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped the song!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No music to skip.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.voice_client:
            await self.ctx.voice_client.disconnect()
            await interaction.response.send_message("⏹️ Stopped music and disconnected.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not in a voice channel.", ephemeral=True)

# --- In-Memory Economy & Zoo Data ---
user_cash = {}
user_zoo = {}

ANIMAL_PRICES = {
    "🐶 Dog": 50,
    "🐱 Cat": 50,
    "🦊 Fox": 100,
    "🐻 Bear": 150,
    "🐰 Rabbit": 40,
    "🦁 Lion": 300,
    "🐯 Tiger": 250,
    "🦄 Unicorn": 1000
}

BAD_WORDS = ["fuck", "slang", "badword", "gali1", "gali2"]
LINK_REGEX = re.compile(r'https?://[^\s]+|discord\.gg/[^\s]+')

def get_balance(uid):
    if uid not in user_cash:
        user_cash[uid] = 200
    return user_cash[uid]

# ================= AUTOMOD & SECURITY EVENTS =================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("ZENITSU Bot is online with Security, OwO Games & Music Panel!")
    await bot.change_presence(activity=discord.Game(name="z!zenitsu help | Security Active ⚡"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 1. Anti-Link Protection
    if LINK_REGEX.search(message.content):
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=10), reason="Anti-Link Violation")
            await message.channel.send(f"🚨 {message.author.mention}, timed out for 10 minutes for sharing links!", delete_after=10)
            return
        except discord.Forbidden:
            pass

    # 2. Anti-Everyone Mention
    if "@everyone" in message.content or "@here" in message.content:
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                await message.author.timeout(timedelta(minutes=15), reason="Anti-Everyone Mention")
                await message.channel.send(f"⚠️ {message.author.mention}, timed out for 15 minutes for `@everyone`!", delete_after=10)
                return
            except discord.Forbidden:
                pass

    # 3. Antiloud / Caps Filter
    if len(message.content) >= 5:
        letters = [c for c in message.content if c.isalpha()]
        if len(letters) >= 5:
            uppercase_chars = sum(1 for c in letters if c.isupper())
            if (uppercase_chars / len(letters)) > 0.7:
                try:
                    await message.delete()
                    await message.author.timeout(timedelta(minutes=5), reason="Antiloud Violation")
                    await message.channel.send(f"🔇 {message.author.mention}, timed out for 5 minutes for excessive caps (shouting)!", delete_after=10)
                    return
                except discord.Forbidden:
                    pass

    # 4. Bad Word / Slang Filter
    content_lower = message.content.lower()
    if any(bad_word in content_lower for bad_word in BAD_WORDS):
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=5), reason="Bad Words Usage")
            await message.channel.send(f"🤬 {message.author.mention}, timed out for 5 minutes for bad language!", delete_after=10)
            return
        except discord.Forbidden:
            pass

    await bot.process_commands(message)

# ================= ZENITSU / OwO COMMANDS =================

@bot.group(name="zenitsu", invoke_without_command=True)
async def zenitsu(ctx):
    await ctx.send("⚡ **ZENITSU Bot Help Menu**\nCommands: `z!zenitsu cash`, `z!zenitsu hunt`, `z!zenitsu zoo`, `z!zenitsu cf <h/t/all>`, `z!zenitsu roll`, `z!zenitsu slots`, `z!zenitsu daily`, `z!play <song>`")

@zenitsu.command(name="owo")
async def zenitsu_owo(ctx):
    responses = ["o w o", "OwO", "uwu", "UwU", ">w<", "⚡ Zenitsu Mode!"]
    await ctx.send(random.choice(responses))

@zenitsu.command(name="cash", aliases=["bal", "money", "c"])
async def zenitsu_cash(ctx, member: discord.Member = None):
    target = member or ctx.author
    bal = get_balance(target.id)
    await ctx.send(f"💰 **{target.name}** currently has **{bal}** coins!")

@zenitsu.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def zenitsu_daily(ctx):
    uid = ctx.author.id
    reward = random.randint(300, 700)
    user_cash[uid] = get_balance(uid) + reward
    await ctx.send(f"🎁 **{ctx.author.name}**, you claimed your daily reward of **{reward}** coins!")

@zenitsu_daily.error
async def zenitsu_daily_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        hours = int(error.retry_after // 3600)
        minutes = int((error.retry_after % 3600) // 60)
        await ctx.send(f"⏳ Already claimed daily! Try again in **{hours}h {minutes}m**.")

@zenitsu.command(name="hunt", aliases=["h"])
async def zenitsu_hunt(ctx):
    uid = ctx.author.id
    animals = list(ANIMAL_PRICES.keys())
    caught = random.choice(animals)
    if uid not in user_zoo:
        user_zoo[uid] = []
    user_zoo[uid].append(caught)
    await ctx.send(f"⚡ **{ctx.author.name}** went hunting and caught a **{caught}**!")

@zenitsu.command(name="zoo", aliases=["z"])
async def zenitsu_zoo(ctx):
    uid = ctx.author.id
    animals = user_zoo.get(uid, [])
    if not animals:
        await ctx.send(f"🐾 **{ctx.author.name}**, your zoo is empty! Use `z!zenitsu hunt`.")
    else:
        counts = {a: animals.count(a) for a in set(animals)}
        zoo_text = "\n".join([f"{a} x{count}" for a, count in counts.items()])
        await ctx.send(f"🦁 **{ctx.author.name}'s Zoo:**\n{zoo_text}")

@zenitsu.command(name="sell")
async def zenitsu_sell(ctx, *, animal_input: str = None):
    uid = ctx.author.id
    animals = user_zoo.get(uid, [])
    if not animal_input:
        await ctx.send("❌ Specify what to sell! Example: `z!zenitsu sell Dog` or `z!zenitsu sell all`")
        return
    if animal_input.lower() == "all":
        if not animals:
            await ctx.send("❌ No animals to sell!")
            return
        total_earned = sum(ANIMAL_PRICES.get(a, 50) for a in animals)
        user_cash[uid] = get_balance(uid) + total_earned
        user_zoo[uid] = []
        await ctx.send(f"💵 Sold all animals for **{total_earned}** coins!")
        return

    matched = None
    for a in animals:
        if animal_input.lower() in a.lower():
            matched = a
            break
    if matched:
        price = ANIMAL_PRICES.get(matched, 50)
        user_zoo[uid].remove(matched)
        user_cash[uid] = get_balance(uid) + price
        await ctx.send(f"💵 Sold a **{matched}** for **{price}** coins!")
    else:
        await ctx.send("❌ Animal not found in your zoo!")

@zenitsu.command(name="cf", aliases=["coinflip"])
async def zenitsu_cf(ctx, choice: str = None, bet: str = "0"):
    uid = ctx.author.id
    bal = get_balance(uid)
    if not choice:
        await ctx.send("❌ Usage: `z!zenitsu cf <h/t> <amount>` or `z!zenitsu cf all`")
        return
    choice = choice.lower()
    if choice == "all" or bet.lower() == "all":
        bet = bal
        user_choice = "heads"
    elif choice in ["h", "heads"]:
        user_choice = "heads"
        try: bet = int(bet)
        except ValueError:
            await ctx.send("❌ Invalid amount!")
            return
    elif choice in ["t", "tails"]:
        user_choice = "tails"
        try: bet = int(bet)
        except ValueError:
            await ctx.send("❌ Invalid amount!")
            return
    else:
        await ctx.send("❌ Choose `heads` (h) or `tails` (t)!")
        return

    if bet <= 0 or bet > bal:
        await ctx.send("❌ Invalid bet amount or insufficient balance!")
        return

    result = random.choice(["heads", "tails"])
    if result == user_choice:
        user_cash[uid] += bet
        await ctx.send(f"🪙 Coin landed on **{result.upper()}**! 🎉 You won **{bet}** coins!")
    else:
        user_cash[uid] -= bet
        await ctx.send(f"🪙 Coin landed on **{result.upper()}**! 💀 You lost **{bet}** coins.")

@zenitsu.command(name="slots", aliases=["s"])
async def zenitsu_slots(ctx, bet: int):
    uid = ctx.author.id
    bal = get_balance(uid)
    if bet <= 0 or bet > bal:
        await ctx.send("❌ Invalid bet amount!")
        return
    emojis = ["🍎", "🍋", "🍒", "🍇", "💎"]
    r1, r2, r3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    if r1 == r2 == r3:
        win = bet * 3
        user_cash[uid] += win
        result = f"🎉 **JACKPOT!** You won **{win}** coins!"
    elif r1 == r2 or r2 == r3 or r1 == r3:
        win = bet * 2
        user_cash[uid] += win
        result = f"✨ **You Won!** You won **{win}** coins!"
    else:
        user_cash[uid] -= bet
        result = f"💀 **You Lost!** You lost **{bet}** coins."
    await ctx.send(f"🎰 **[ {r1} | {r2} | {r3} ]**\n{result}")

@zenitsu.command(name="roll", aliases=["dice"])
async def zenitsu_roll(ctx, bet: int):
    uid = ctx.author.id
    bal = get_balance(uid)
    if bet <= 0 or bet > bal:
        await ctx.send("❌ Invalid bet amount!")
        return
    bot_roll = random.randint(1, 6)
    user_roll = random.randint(1, 6)
    if user_roll > bot_roll:
        user_cash[uid] += bet
        res = f"🎉 You won! (You: **{user_roll}** vs Bot: **{bot_roll}**)\n+**{bet}** coins!"
    elif user_roll < bot_roll:
        user_cash[uid] -= bet
        res = f"💀 You lost! (You: **{user_roll}** vs Bot: **{bot_roll}**)\n-**{bet}** coins!"
    else:
        res = f"🤝 It's a tie! (Both rolled: **{user_roll}**)"
    await ctx.send(f"🎲 {res}")

@zenitsu.command(name="give")
async def zenitsu_give(ctx, member: discord.Member, amount: int):
    sender = ctx.author.id
    receiver = member.id
    if amount <= 0 or get_balance(sender) < amount:
        await ctx.send("❌ Insufficient balance or invalid amount!")
        return
    user_cash[sender] -= amount
    user_cash[receiver] = get_balance(receiver) + amount
    await ctx.send(f"💸 {ctx.author.mention} gave **{amount}** coins to {member.mention}!")

# ================= SHORTCUT COMMANDS =================
@bot.command(name="cash", aliases=["bal", "c"])
async def direct_cash(ctx, member: discord.Member = None):
    await zenitsu_cash(ctx, member)

@bot.command(name="hunt", aliases=["h"])
async def direct_hunt(ctx):
    await zenitsu_hunt(ctx)

@bot.command(name="zoo", aliases=["z"])
async def direct_zoo(ctx):
    await zenitsu_zoo(ctx)

@bot.command(name="daily")
async def direct_daily(ctx):
    await zenitsu_daily(ctx)

@bot.command(name="cf", aliases=["coinflip"])
async def direct_cf(ctx, choice: str = None, bet: str = "0"):
    await zenitsu_cf(ctx, choice, bet)

@bot.command(name="slots", aliases=["s"])
async def direct_slots(ctx, bet: int):
    await zenitsu_slots(ctx, bet)

# ================= MUSIC COMMANDS WITH EMBED & BUTTONS =================

@bot.command(name="join")
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"✅ Joined **{channel.name}**!")
    else:
        await ctx.send("❌ You need to be in a voice channel first!")

@bot.command(name="play")
async def play(ctx, *, search: str):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You are not connected to a voice channel!")
            return

    async with ctx.typing():
        try:
            if not search.startswith("http"):
                search = f"ytsearch:{search}"
            
            player = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            
            # --- Premium Music Embed Panel with Buttons ---
            embed = discord.Embed(
                title="🎶 ZENITSU MUSIC PANEL",
                description=f"**[{player.title}]({player.url})**",
                color=discord.Color.gold()
            )
            embed.add_field(name="👤 Requested By", value=ctx.author.mention, inline=True)
            embed.add_field(name="⏱️ Duration", value=f"{player.duration // 60}m {player.duration % 60}s" if player.duration else "Live/Unknown", inline=True)
            embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/q33q96z_0Z6G.../https/cdn.discordapp.com/emojis/845946112920256542.gif")
            
            view = MusicControls(ctx)
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name="stop")
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Stopped music and disconnected.")
    else:
        await ctx.send("❌ I am not in a voice channel.")

@bot.command(name="skip")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped the song!")
    else:
        await ctx.send("❌ No music is playing to skip.")

# ================= RUN BOT =================
TOKEN = "MTU2MTcyMDQ0NTQyNDc3MTA4NQ.GX6DJn.fNVj8bb-IvRaEejjLv8QQfcMqvkxSOC2_rMYt0"
bot.run(TOKEN)
