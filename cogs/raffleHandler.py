import sqlite3
import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
import cogs.functions
from cogs.currencyHandler import determineSymbol
import pytz
import datetime
import re
import random
import traceback

conn = sqlite3.connect('raffle.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

invConn = sqlite3.connect('shop.db', timeout=5.0)
invC = invConn.cursor()

c.execute('CREATE TABLE IF NOT EXISTS raffle (server_id INT, channel_id INT, message_id INT, user_id INT, endsAt INT, winners INT, item TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS raffleParticipants (user_id INT, message_id INT, server_id INT)')


def dmyConverter(seconds):
    secondsInDays = 60 * 60 * 24
    secondsInHours = 60 * 60
    secondsInMinutes = 60

    days = seconds // secondsInDays
    hours = (seconds - (days * secondsInDays)) // secondsInHours
    minutes = ((seconds - (days * secondsInDays)) - (hours * secondsInHours)) // secondsInMinutes
    remainingSeconds = seconds - (days * secondsInDays) - (hours * secondsInHours) - (
            minutes * secondsInMinutes)

    timeStatement = ""

    if days != 0:
        timeStatement += f"{round(days)} days,"
    if hours != 0:
        timeStatement += f" {round(hours)} hours,"
    if minutes != 0:
        timeStatement += f" {round(minutes)} minutes,"
    if remainingSeconds != 0:
        timeStatement += f" {round(remainingSeconds)} seconds"
    if timeStatement[-1] == ",":
        timeStatement = timeStatement[:-1]

    return timeStatement


def in_seconds(text):
    unit_value = {'d': 60 * 60 * 24, 'h': 60 * 60, 'm': 60, 's': 1}
    seconds = 0
    for number, unit in re.findall(r'(\d+)([dhms])', text):
        seconds = seconds + unit_value[unit] * int(number)
    return seconds



class raffleSystem(commands.Cog, name="🎟️ Raffle System"):
    def __init__(self, bot):
        self.bot = bot
        self.rafflingHandler.start()

    @tasks.loop(seconds=30.0)
    async def rafflingHandler(self):

        try:
            now = datetime.datetime.now(pytz.timezone("Singapore")).timestamp()

            c.execute('SELECT * FROM raffle')
            allraffles = c.fetchall()

            for raffle in allraffles:

                serverID = raffle[0]
                channelID = raffle[1]
                msgID = raffle[2]
                hostID = raffle[3]
                endsAt = raffle[4]
                qtyWinners = raffle[5]
                prize = raffle[6]

                guildObject = self.bot.get_guild(serverID)
                channelObject = self.bot.get_channel(channelID)
                messageObject = await channelObject.fetch_message(msgID)
                hostObject = guildObject.get_member(hostID)
                endsAtTimeObject = datetime.datetime.fromtimestamp(endsAt, tz=pytz.timezone("Singapore"))

                timeLeft = endsAt - now
                formattedTime = dmyConverter(timeLeft)

                if timeLeft < 0:
                    raffle = [user[0] for user in c.execute('SELECT user_id FROM raffleParticipants WHERE message_id = ? ', (msgID, ))]
                    if not raffle:
                        totalDescription = "Could not determine a winner!\n"
                        totalDescription += f"Hosted by: {hostObject.mention}"
                        embed = discord.Embed(title=f'{prize}', description=totalDescription,
                                                    timestamp=endsAtTimeObject,
                                                    colour=cogs.functions.embedColour(serverID))

                        if qtyWinners == 1:
                            embed.set_footer(text=f"{qtyWinners} Winner | Ended at ")
                        else:
                            embed.set_footer(text=f"{qtyWinners} Winners | Ended at ")

                        await messageObject.edit(embed=embed)
                        endedDescription = f"🎟️ Could not determine a winner for **{prize}**"
                        await channelObject.send(endedDescription)
                        c.execute(' DELETE FROM raffle WHERE message_id = ? ', (msgID,))
                        conn.commit()
                        c.execute(' DELETE FROM raffleParticipants WHERE message_id = ?', (msgID,))
                        conn.commit()
                        return

                    winnerList = ""
                    winners = []

                    for i in range(qtyWinners):
                        if not raffle:
                            break
                        winner = random.choice(raffle)
                        winners.append(winner)
                        winnerObject = guildObject.get_member(winner)
                        winnerList += f"{winnerObject.mention}"
                        raffle.remove(winner)

                        totalDescription = f"Winner: {winnerList}\n"
                        totalDescription += f"Hosted by: {hostObject.mention}"
                        embed = discord.Embed(title=f'{prize}',
                                            description=totalDescription, timestamp=endsAtTimeObject,
                                            colour=cogs.functions.embedColour(serverID))

                        if qtyWinners == 1:
                            embed.set_footer(text=f"{qtyWinners} Winner | Ended at ")
                        else:
                            embed.set_footer(text=f"{qtyWinners} Winners | Ended at ")

                        await messageObject.edit(embed=embed)
                        endedDescription = f"🎟️ Congratulations {winnerList}, you won **{prize}**"
                        await channelObject.send(endedDescription)

                    c.execute(' DELETE FROM raffle WHERE message_id = ? ', (msgID,))
                    conn.commit()
                    c.execute(' DELETE FROM raffleParticipants WHERE message_id = ?', (msgID,))
                    conn.commit()
                    return

                totalDescription = f"Use the command `r {msgID}`️ to enter!\n"
                totalDescription += f"Time Remaining: {formattedTime}\n"
                totalDescription += f"Hosted by: {hostObject.mention}"

                embed = discord.Embed(title=f'{prize}', description=totalDescription, timestamp=endsAtTimeObject,
                                      colour=cogs.functions.embedColour(serverID))

                if qtyWinners == 1:
                    embed.set_footer(text=f"{qtyWinners} Winner | Ends at ")
                else:
                    embed.set_footer(text=f"{qtyWinners} Winners | Ends at ")

                await messageObject.edit(embed=embed)

        except:
            traceback.print_exc()

    @rafflingHandler.before_loop
    async def before_status(self):
        print('Waiting to handle raffles...')
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        c.execute('DELETE FROM raffleParticipants WHERE user_id = ? AND server_id = ? ', (member.id, member.guild.id))
        conn.commit()

    @commands.command(
        description="r [message ID] [entries (optional)]**\n\nJoins a Raffle by their Message ID using Raffle Ticket(s). Default entry is one if not specified.",
        aliases=['r'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def raffle(self, ctx, msgID, entries: int = 1):

        messageList = [message[0] for message in c.execute('SELECT message_id FROM raffle')]
        invC.execute(f''' SELECT Raffle FROM inventory WHERE user_id = ? ''', (ctx.author.id,))
        ticketCount = invC.fetchall()[0][0]

        if msgID not in messageList:
            return await cogs.functions.errorEmbedTemplate(ctx, f"The Raffle ID does not exist!", ctx.message.author)

        initialCount = len([user[0] for user in
                            c.execute('''SELECT user_id FROM raffleParticipants WHERE user_id = ? ''',
                                      (ctx.author.id,))])

        if initialCount == 0:
            ticketCount += 1

        ticketCount -= entries

        if ticketCount < 0:
            return await cogs.functions.errorEmbedTemplate(ctx,
                                                           f"You do not have enough raffle tickets to partake in the raffle!",
                                                           ctx.message.author)

        c.execute('INSERT OR REPLACE INTO raffleParticipants VALUES (?, ?, ?)', (ctx.author.id, int(msgID), ctx.guild.id))
        conn.commit()
        invC.execute(f''' UPDATE inventory SET "{"Raffle Ticket"}"  = ? WHERE user_id = ? ''', (ticketCount, ctx.author.id))
        invConn.commit()

        raffleCount = len([user[0] for user in
                           c.execute('''SELECT user_id FROM raffleParticipants WHERE user_id = ? ''',
                                     (ctx.author.id,))])

        if raffleCount == 1:
            entryDesc = "entry"
        else:
            entryDesc = "entries"

        return await cogs.functions.successEmbedTemplate(ctx,
                                                         f"You've successfully enrolled into the raffle!\n\nYour raffle entry count(s): **{raffleCount} {entryDesc}**",
                                                         ctx.message.author)


    @commands.command(description="rafflestart [start channel] [duration (in %d%h%m%s)] [no. of winners] [item]**\n\nStarts a Raffle! Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def rafflestart(self, ctx, channel: discord.TextChannel, duration, winners: int, *, item: str):

        seconds = in_seconds(duration)

        if seconds <= 0:
            return await cogs.functions.errorEmbedTemplate(ctx,
                                                      f"Invalid time format or input! Please restart the command and try again. Time must be at least 5 minutes!",
                                                      ctx.message.author)

        formattedTime = dmyConverter(seconds)

        timeRemaining = f"Time Remaining: {formattedTime}"
        hostedBy = f"Hosted by: {ctx.author.mention}"

        now = datetime.datetime.now(pytz.timezone("Singapore"))
        endsAt = now + datetime.timedelta(seconds=seconds)
        description = f"Use the command `r [Message ID To Be Updated...]` to enter!\n"
        description += f"{timeRemaining}\n"
        description += f"{hostedBy}"

        embed = discord.Embed(title=f'{item}', description=description, timestamp=endsAt,
                              colour=cogs.functions.embedColour(ctx.message.guild.id))

        if winners == 1:
            embed.set_footer(text=f"{winners} Winner | Ends at ")
        else:
            embed.set_footer(text=f"{winners} Winners | Ends at ")

        checkingMsg = await ctx.send(embed=embed)
        await ctx.send("🎟️ This will how the raffle look like, please react below to confirm if you want to start the raffle!")

        await checkingMsg.add_reaction("✅")
        await checkingMsg.add_reaction("❎")

        def check(reaction, user):
            return str(reaction.emoji) in ["✅", "❎"] and user == ctx.message.author

        reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=60)

        if str(reaction.emoji) == "✅":
            msg = await channel.send(embed=embed)
            c.execute('INSERT OR REPLACE INTO raffle VALUES (?, ?, ?, ?, ?, ?, ?)', (ctx.guild.id, channel.id, msg.id, ctx.author.id, endsAt.timestamp(), winners, item))
            conn.commit()
            await cogs.functions.successEmbedTemplate(ctx, f"Raffle successfully started on {channel.mention}", ctx.message.author)

        elif str(reaction.emoji) == "❎":
            await cogs.functions.successEmbedTemplate(ctx, "You have discarded your input, please start the command again!", ctx.message.author)
            await ctx.send(embed=embed)
            await checkingMsg.delete()


def setup(bot):
    bot.add_cog(raffleSystem(bot))
