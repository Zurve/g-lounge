import sqlite3
from discord.ext import commands
from discord.ext.commands import has_permissions

import cogs.functions

conn = sqlite3.connect('currency.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('''CREATE TABLE IF NOT EXISTS symbol (`server_id` INT PRIMARY KEY,
    `currency` TEXT)''')

def determineSymbol(id):
    c.execute(f'SELECT currency FROM symbol WHERE server_id = ? ', (id,))
    result = c.fetchall()

    symbol = result[0][0]

    return symbol


def createCurrencyProfile(ID):
    c.execute('''INSERT OR REPLACE INTO symbol VALUES (?, ?) ''', (ID, "💰"))
    conn.commit()
    print(f"Added for {ID} into currency database.")


class setCurrency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        description="currencyset [symbol/letters]**\n\nChanges the currency of the Bot in your Server! Administrator Only!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def currencyset(self, ctx, symbol):

        c.execute(''' INSERT OR REPLACE INTO symbol VALUES (?, ?) ''', (ctx.guild.id, symbol))
        conn.commit()
        await cogs.functions.successEmbedTemplate(ctx, f"Currency successfully set as {symbol}!", ctx.message.author)

    @commands.Cog.listener()
    async def on_ready(self):

        guildDatabase = [guild[0] for guild in c.execute('SELECT server_id FROM symbol')]

        for guild in self.bot.guilds:
            if guild.id not in guildDatabase:
                createCurrencyProfile(guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        guildDatabase = [guild[0] for guild in c.execute('SELECT server_id FROM symbol')]

        if guild.id not in guildDatabase:
            createCurrencyProfile(guild.id)



def setup(bot):
    bot.add_cog(setCurrency(bot))
