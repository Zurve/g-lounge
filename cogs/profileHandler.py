import sqlite3
import discord
from discord.ext import commands
import cogs.functions
from cogs.currencyHandler import determineSymbol

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

invConn = sqlite3.connect('shop.db', timeout=5.0)
invC = invConn.cursor()


c.execute('''CREATE TABLE IF NOT EXISTS userProfile (`user_id` INT PRIMARY KEY, `currentExp` INT, `cooldown` INT, `money` INT) ''')

def getMaxExp(level):
    value = max(100 + (150 * (level - 1)), 100)
    return value

def getTotalExp(level):
    accumulatedExp = 0
    for x in range(1, level):
        accumulatedExp += getMaxExp(x)
    return accumulatedExp

def getLevel(exp):
    checkLevel = 1
    while exp >= 0:
        exp -= getMaxExp(checkLevel)
        checkLevel += 1
    return max(checkLevel - 1, 1)


def profileCreate(id):
    c.execute('''INSERT OR REPLACE INTO userProfile VALUES (?, ?, ?, ?)''', (id, 0, 0, 200))
    conn.commit()
    c.execute('''INSERT OR REPLACE INTO userDaily VALUES (?, ?, ?) ''', (id, 0, 0))
    conn.commit()
    invC.execute(f'''INSERT OR REPLACE INTO inventory (user_id) VALUES (?)''', (id, ))
    invConn.commit()

def profileGet(id):
    c.execute(''' SELECT user_id, currentExp, cooldown, money FROM userProfile WHERE user_id = ? ''', (id,))
    profile = c.fetchall()

    result = profile[0]
    exp = result[1]
    level = getLevel(exp)
    expTnl = getMaxExp(level)
    expRemainder = exp - getTotalExp(level)
    money = result[3]

    return result, exp, level, expTnl, money, expRemainder

class profileSystem(commands.Cog, name="📖 Profile System"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="p**\n\nShows your adventurer profile or someone else's!", aliases=['p'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def profile(self, ctx, user: discord.Member = None):

        if not user:
            user = ctx.author

        userProfile = profileGet(user.id)
        embed = discord.Embed(title=f"{user}'s Profile", description="",
                              colour=cogs.functions.embedColour(ctx.guild.id))
        embed.add_field(name="Statistics",
                        value=f"Level: {userProfile[2]:,}\nEXP: {userProfile[5]:,}/{userProfile[3]:,}", inline=False)
        embed.add_field(name=f"Currency", value=f"{userProfile[4]:,} {determineSymbol(ctx.guild.id)}", inline=True)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):

        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM userProfile')]

        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.bot:
                    if member.id not in userDatabase:
                        profileCreate(member.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM userProfile')]

        for member in guild.members:
            if not member.bot:
                if member.id not in userDatabase:
                    profileCreate(member.id)

    @commands.Cog.listener()
    async def on_member_join(self, member):

        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM userProfile')]

        if not member.bot:
            if member.id not in userDatabase:
                profileCreate(member.id)

def setup(bot):
    bot.add_cog(profileSystem(bot))
