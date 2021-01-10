import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3

conn = sqlite3.connect('colour.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('''CREATE TABLE IF NOT EXISTS server (`server_id` INT PRIMARY KEY, `embed` STR) ''')

async def requestEmbedTemplate(ctx, description, author):
    embed = discord.Embed(description=f"{description}", colour=embedColour(ctx.message.guild.id))
    embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar_url)
    return await ctx.send(embed=embed)

async def errorEmbedTemplate(ctx, description, author):
    embed = discord.Embed(description=f"❎ {description}", colour=embedColour(ctx.message.guild.id))
    embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar_url)
    return await ctx.send(embed=embed)

async def successEmbedTemplate(ctx, description, author):
    embed = discord.Embed(description=f"☑️ {description}", colour=embedColour(ctx.message.guild.id))
    embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar_url)
    return await ctx.send(embed=embed)


def embedColour(guild):
    for row in c.execute(f'SELECT embed FROM server WHERE server_id = {guild}'):
        colourEmbed = row[0]
        colourEmbedInt = int(colourEmbed, 16)
        return colourEmbedInt

def createGuildProfile(ID):
    c.execute(''' INSERT OR REPLACE INTO server VALUES (?, ?) ''', (ID, "0xdecaf0"))
    conn.commit()
    print(f"Added for {ID} into guild database.")



class Functions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description=f"embedsettings [colour code e.g. 0xffff0]**\n\nChanges the colour of the embed.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def embedsettings(self, ctx, colour):

        try:
            c.execute(f''' UPDATE SERVER SET embed = ? WHERE server_id = ? ''', (colour, ctx.message.guild.id))
            conn.commit()
            await requestEmbedTemplate(ctx, f"☑️ Embed colour successfully set to `{colour}` for `{ctx.message.guild}`.", ctx.author)
        except ValueError:
            await errorEmbedTemplate(ctx, f"Please make sure your input is correct! For example, `#ff0000` should be `0xff0000`.", ctx.author)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        guild_database = [row for row in c.execute('SELECT server_id FROM server')]

        if guild.id not in guild_database:
            createGuildProfile(guild.id)


    @commands.Cog.listener()
    async def on_ready(self):

        guild_database = [row[0] for row in c.execute('SELECT server_id FROM server')]

        for guild in self.bot.guilds:
            if guild.id not in guild_database:
                createGuildProfile(guild.id)




def setup(bot):
    bot.add_cog(Functions(bot))
