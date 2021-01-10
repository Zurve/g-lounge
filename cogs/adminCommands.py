import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
import cogs.functions
import traceback
from cogs.economyHandler import coinTransaction
from cogs.currencyHandler import determineSymbol

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row


class adminCommands(commands.Cog, name="🛠️ Admin Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        description="addcoin [user mention] [amount]**\n\nAdds/Removes currency from a specified user! Administrator Only.")
    @has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def addcoin(self, ctx, user: discord.Member, amount: int):

        coinTransaction(user.id, amount)
        if amount > 0:
            await cogs.functions.successEmbedTemplate(ctx,
                                                      f"Successfully added **{amount:,}** {determineSymbol(ctx.guild.id)} to {user.mention}",
                                                      ctx.message.author)
        else:
            await cogs.functions.successEmbedTemplate(ctx,
                                                      f"Successfully removed **{abs(amount):,}** {determineSymbol(ctx.guild.id)} to {user.mention}",
                                                      ctx.message.author)

    @commands.command(description="setexp [min] [max]**\n\nSets the EXP range gain per message sent.")
    @has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def setexp(self, ctx, minimum: int, maximum: int):

        if minimum > maximum:
            await cogs.functions.errorEmbedTemplate(ctx,
                                                    f"Maximum EXP gain cannot be higher than minimum EXP gain!",
                                                    ctx.author)
            return

        c.execute('''UPDATE serverRanking SET minExp = ?, maxExp = ? WHERE server_id = ? ''',
                  (minimum, maximum, ctx.guild.id))
        conn.commit()
        await cogs.functions.successEmbedTemplate(ctx,
                                                  f"Successfully set, `{ctx.guild}` will provide randomly between **{minimum:,}** and **{maximum:,}** EXP for activity!",
                                                  ctx.author)

    @commands.command(description="setmoney [min] [max]**\n\nSets the Currency range gain per message sent.")
    @has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def setmoney(self, ctx, minimum: int, maximum: int):

        if minimum > maximum:
            await cogs.functions.errorEmbedTemplate(ctx,
                                                    f"Maximum Currency gain cannot be higher than minimum Currency gain!",
                                                    ctx.author)
            return

        c.execute('''UPDATE serverRanking SET minMoney = ?, maxMoney = ? WHERE server_id = ? ''',
                  (minimum, maximum, ctx.guild.id))
        conn.commit()
        await cogs.functions.successEmbedTemplate(ctx,
                                                  f"Successfully set, `{ctx.guild}` will provide randomly between **{minimum:,}** and **{maximum:,}** {determineSymbol(ctx.guild.id)} for activity!",
                                                  ctx.author)


def setup(bot):
    bot.add_cog(adminCommands(bot))
