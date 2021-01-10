import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
import pytz
import datetime
import cogs.functions
import math
import random
from cogs.currencyHandler import determineSymbol

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('''CREATE TABLE IF NOT EXISTS userDaily (`user_id` INT PRIMARY KEY, `dailyCheck` INT, `streak` INT) ''')

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

def barHandler(currentStreak):
    def startingBarHandler(currentStreak):
        if currentStreak >= 1:
            startingBar = "<a:aniProgress1:773526629032919090>"
        else:
            startingBar = "<:emptyStart1:769012009911975947>"
        return startingBar

    def progressBarHandler(currentStreak):
        if currentStreak >= 9:
            progressBar = 8 * "<a:aniProgress2:773526660695195679>"
        elif currentStreak <= 1:
            progressBar = 8 * "<:emptyProgress1:769012010092068894>"
        else:
            # 2 streak = 1 bar, 3 streak = 2 bar
            completed = currentStreak - 1
            progressBar = completed * "<a:aniProgress2:773526660695195679>" + (
                    8 - completed) * "<:emptyProgress1:769012010092068894>"
        return progressBar

    def endingBarHandler(currentStreak):
        if currentStreak == 10:
            endingBar = "<a:aniProgress3:773526698461233192>"
        else:
            endingBar = "<:emptyEnd1:769012010116579406>"
        return endingBar

    startingBar = startingBarHandler(currentStreak)
    progressBar = progressBarHandler(currentStreak)
    endingBar = endingBarHandler(currentStreak)

    return startingBar, progressBar, endingBar


def progressHandler(percentage):
    def startingBarHandler(percentage):
        if percentage > 0:
            startingBar = "<a:aniProgress1:773526629032919090>"
        else:
            startingBar = "<:emptyStart1:769012009911975947>"
        return startingBar

    def progressBarHandler(percentage):
        if percentage >= 0.9:
            progressBar = 8 * "<a:aniProgress2:773526660695195679>"
        elif percentage < 0.2:
            progressBar = 8 * "<:emptyProgress1:769012010092068894>"
        else:
            progressPercentage = (percentage - 0.1) * 100

            def roundDown(x):
                return int(math.floor(x / 10.0)) * 10

            blocks = int(roundDown(progressPercentage) / 10)

            progressBar = blocks * "<a:aniProgress2:773526660695195679>" + (
                    8 - blocks) * "<:emptyProgress1:769012010092068894>"
        return progressBar

    def endingBarHandler(percentage):
        if percentage == 1:
            endingBar = "<a:aniProgress3:773526698461233192>"
        else:
            endingBar = "<:emptyEnd1:769012010116579406>"
        return endingBar

    startingBar = startingBarHandler(percentage)
    progressBar = progressBarHandler(percentage)
    endingBar = endingBarHandler(percentage)

    return startingBar, progressBar, endingBar


def coinTransaction(id, amount):
    c.execute(''' SELECT money FROM userProfile WHERE user_id = ? ''', (id, ))
    coins = c.fetchall()[0][0]
    updatedCoins = coins + amount
    c.execute(''' UPDATE userProfile SET money = ? WHERE user_id = ? ''', (updatedCoins, id))
    conn.commit()

def coinGet(id):
    c.execute(''' SELECT money FROM userProfile WHERE user_id = ? ''', (id,))
    coins = c.fetchall()[0][0]
    return coins

def dailyGet(id):
    c.execute(''' SELECT dailyCheck, streak FROM userDaily WHERE user_id = ? ''', (id,))
    profile = c.fetchall()
    result = profile[0]
    dailyCheck = result[0]
    currentStreak = result[1]
    timeNow = int(datetime.datetime.now(pytz.timezone("Singapore")).timestamp())
    nextMidnight = int(datetime.datetime.now(pytz.timezone("Singapore")).replace(hour=0, minute=0, second=0,
                                                                                 microsecond=0).timestamp()) + 86400
    if dailyCheck > timeNow:
        return False

    else:
        if currentStreak < 10:
            currentStreak += 1
        elif currentStreak == 10:
            currentStreak -= 9

        c.execute(''' UPDATE userDaily SET dailyCheck = ?, streak = ? WHERE user_id = ? ''',
                  (nextMidnight, currentStreak, id))
        conn.commit()

        return currentStreak, 1

class Economy(commands.Cog, name="💰 Economy"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="xplb**\n\nShows the Server Leaderboard!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def xplb(self, ctx):

        c.execute('SELECT user_id, currentExp FROM userProfile')
        leaderboardUsers = c.fetchall()

        guildMemberList = [member.id for member in ctx.guild.members]
        guildLeaderboardUsers = [item for item in leaderboardUsers if item[0] in guildMemberList]

        def sortSecond(val):
            return val[1]

        guildLeaderboardUsers.sort(key=sortSecond, reverse=True)

        i = 1
        everyPage = [item for item in guildLeaderboardUsers[10 * (i - 1):i * 10] if item[0] in guildMemberList]
        pageRankingStart = 10 * (i - 1) + 1
        pages = math.ceil(len(guildLeaderboardUsers) / 10)

        lengthRecord = []

        for item in everyPage:
            lengthDescription = ''
            member = self.bot.get_user(item[0])

            currentLevel = getLevel(item[1])

            rankLength = len(f"{pageRankingStart}. |")
            lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
            EXPLength = len(f" {item[1]:,} |")
            lengthDescription += f'{(10 - EXPLength) * " "}{item[1]:,} |'
            levelLength = len(f" {currentLevel} |")  # Placeholder
            lengthDescription += f'{(9 - levelLength) * " "}{currentLevel} |'
            lengthDescription += f' {member}\n'
            lengthRecord.append(len(lengthDescription))
            pageRankingStart += 1

        authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

        authorExp = authorProfile[0][1]
        guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
        authorRank = guildLeaderboardID.index(ctx.author.id) + 1
        currentLevel = getLevel(authorExp)

        lengthDescription = ''

        rankLength = len(f"{authorRank}. |")
        lengthDescription += f'{(7 - rankLength) * " "}{authorRank:,}. |'
        EXPLength = len(f" {authorExp:,} |")
        lengthDescription += f'{(10 - EXPLength) * " "}{authorExp:,} |'
        levelLength = len(f" {currentLevel} |")
        lengthDescription += f'{(9 - levelLength) * " "}{currentLevel} |'
        lengthDescription += f' {ctx.author}\n'
        lengthRecord.append(len(lengthDescription))

        description = f'```yaml\nRank. | Exp.   | Level | Username\n{max(lengthRecord) * "="}\n'

        pageRankingStart = 10 * (i - 1) + 1

        for item in everyPage:
            member = self.bot.get_user(item[0])
            currentLevel = getLevel(item[1])

            rankLength = len(f"{pageRankingStart}. |")
            description += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
            EXPLength = len(f" {item[1]:,} |")
            description += f'{(10 - EXPLength) * " "}{item[1]:,} |'
            levelLength = len(f" {currentLevel} |")
            description += f'{(9 - levelLength) * " "}{currentLevel} |'
            description += f' {member}\n'
            pageRankingStart += 1

        description += f'{max(lengthRecord) * "~"}\n'

        authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

        authorExp = authorProfile[0][1]
        guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
        authorRank = guildLeaderboardID.index(ctx.author.id) + 1
        currentLevel = getLevel(authorExp)

        rankLength = len(f"{authorRank}. |")
        description += f'{(7 - rankLength) * " "}{authorRank:,}. |'
        EXPLength = len(f" {authorExp:,} |")
        description += f'{(10 - EXPLength) * " "}{authorExp:,} |'
        levelLength = len(f" {currentLevel} |")
        description += f'{(9 - levelLength) * " "}{currentLevel} |'
        description += f' {ctx.author}\n'

        description += '```'

        embed = discord.Embed(title=f"{ctx.guild}'s Leaderboard",
                              description=description,
                              timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
        embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)
        await msg.add_reaction('⏪')
        await msg.add_reaction('⏩')

        def check(reaction, user):
            return str(reaction.emoji) in ['⏪', '⏩'] and user == ctx.message.author and reaction.message.id == msg.id

        async def handle_rotate(reaction, msg, check, i):
            await msg.remove_reaction(reaction, ctx.message.author)

            if str(reaction.emoji) == '⏩':
                i += 1

                if i > pages:
                    embed = discord.Embed(description=f"You have reached the end of the pages!")
                    embed.set_footer(text=f"Press '⏪' to go back.", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

                else:

                    everyPage = [item for item in guildLeaderboardUsers[10 * (i - 1):i * 10] if
                                 item[0] in guildMemberList]
                    pageRankingStart = 10 * (i - 1) + 1

                    lengthRecord = []

                    for item in everyPage:
                        lengthDescription = ''
                        member = self.bot.get_user(item[0])

                        currentLevel = getLevel(item[1])

                        rankLength = len(f"{pageRankingStart}. |")
                        lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        EXPLength = len(f" {item[1]:,} |")
                        lengthDescription += f'{(10 - EXPLength) * " "}{item[1]:,} |'
                        levelLength = len(f" {currentLevel} |")  # Placeholder
                        lengthDescription += f'{(9 - levelLength) * " "}{currentLevel} |'
                        lengthDescription += f' {member}\n'
                        lengthRecord.append(len(lengthDescription))
                        pageRankingStart += 1

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1
                    currentLevel = getLevel(authorExp)

                    lengthDescription = ''

                    rankLength = len(f"{authorRank}. |")
                    lengthDescription += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    EXPLength = len(f" {authorExp:,} |")
                    lengthDescription += f'{(10 - EXPLength) * " "}{authorExp:,} |'
                    levelLength = len(f" {currentLevel} |")  # placeholder
                    lengthDescription += f'{(9 - levelLength) * " "}{currentLevel} |'
                    lengthDescription += f' {ctx.author}\n'
                    lengthRecord.append(len(lengthDescription))

                    description = f'```yaml\nRank. | Exp.   | Level | Username\n{max(lengthRecord) * "="}\n'

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        member = self.bot.get_user(item[0])
                        currentLevel = getLevel(item[1])

                        rankLength = len(f"{pageRankingStart}. |")
                        description += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        EXPLength = len(f" {item[1]:,} |")
                        description += f'{(10 - EXPLength) * " "}{item[1]:,} |'
                        levelLength = len(f" {currentLevel} |")  # Placeholder
                        description += f'{(9 - levelLength) * " "}{currentLevel} |'
                        description += f' {member}\n'
                        pageRankingStart += 1

                    description += f'{max(lengthRecord) * "~"}\n'

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1
                    currentLevel = getLevel(authorExp)

                    rankLength = len(f"{authorRank}. |")
                    description += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    EXPLength = len(f" {authorExp:,} |")
                    description += f'{(10 - EXPLength) * " "}{authorExp:,} |'
                    levelLength = len(f" {currentLevel} |")  # placeholder
                    description += f'{(9 - levelLength) * " "}{currentLevel} |'
                    description += f' {ctx.author}\n'

                    description += '```'

                    embed = discord.Embed(title=f"{ctx.guild}'s Leaderboard",
                                          description=description,
                                          timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
                    embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

            elif str(reaction.emoji) == '⏪':

                i -= 1

                if i <= 0:

                    embed = discord.Embed(description=f"You have reached the end of the pages!")
                    embed.set_footer(text=f"Press '⏩' to go back.", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

                else:

                    everyPage = [item for item in guildLeaderboardUsers[10 * (i - 1):i * 10] if
                                 item[0] in guildMemberList]
                    pageRankingStart = 10 * (i - 1) + 1

                    lengthRecord = []

                    for item in everyPage:
                        lengthDescription = ''
                        member = self.bot.get_user(item[0])

                        currentLevel = getLevel(item[1])

                        rankLength = len(f"{pageRankingStart}. |")
                        lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        EXPLength = len(f" {item[1]:,} |")
                        lengthDescription += f'{(10 - EXPLength) * " "}{item[1]:,} |'
                        levelLength = len(f" {currentLevel} |")  # Placeholder
                        lengthDescription += f'{(9 - levelLength) * " "}{currentLevel} |'
                        lengthDescription += f' {member}\n'
                        lengthRecord.append(len(lengthDescription))
                        pageRankingStart += 1

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1
                    currentLevel = getLevel(authorExp)

                    lengthDescription = ''

                    rankLength = len(f"{authorRank}. |")
                    lengthDescription += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    EXPLength = len(f" {authorExp:,} |")
                    lengthDescription += f'{(10 - EXPLength) * " "}{authorExp:,} |'
                    levelLength = len(f" {currentLevel} |")  # placeholder
                    lengthDescription += f'{(9 - levelLength) * " "}{currentLevel} |'
                    lengthDescription += f' {ctx.author}\n'
                    lengthRecord.append(len(lengthDescription))

                    description = f'```yaml\nRank. | Exp.   | Level | Username\n{max(lengthRecord) * "="}\n'

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        member = self.bot.get_user(item[0])
                        currentLevel = getLevel(item[1])

                        rankLength = len(f"{pageRankingStart}. |")
                        description += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        EXPLength = len(f" {item[1]:,} |")
                        description += f'{(10 - EXPLength) * " "}{item[1]:,} |'
                        levelLength = len(f" {currentLevel} |")  # Placeholder
                        description += f'{(9 - levelLength) * " "}{currentLevel} |'
                        description += f' {member}\n'
                        pageRankingStart += 1

                    description += f'{max(lengthRecord) * "~"}\n'

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1
                    currentLevel = getLevel(authorExp)

                    rankLength = len(f"{authorRank}. |")
                    description += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    EXPLength = len(f" {authorExp:,} |")
                    description += f'{(10 - EXPLength) * " "}{authorExp:,} |'
                    levelLength = len(f" {currentLevel} |")  # placeholder
                    description += f'{(9 - levelLength) * " "}{currentLevel} |'
                    description += f' {ctx.author}\n'

                    description += '```'

                    embed = discord.Embed(title=f"{ctx.guild}'s Leaderboard",
                                          description=description,
                                          timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
                    embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

            else:
                return

            reaction, user = await self.bot.wait_for('reaction_add', check=check)
            await handle_rotate(reaction, msg, check, i)

        reaction, user = await self.bot.wait_for('reaction_add', check=check)
        await handle_rotate(reaction, msg, check, i)

    @commands.command(description="lb**\n\nShows the Server Leaderboard!", aliases=['lb'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leaderboard(self, ctx):

        c.execute('SELECT user_id, money FROM userProfile')
        leaderboardUsers = c.fetchall()

        guildMemberList = [member.id for member in ctx.guild.members]
        guildLeaderboardUsers = [item for item in leaderboardUsers if item[0] in guildMemberList]

        def sortSecond(val):
            return val[1]

        guildLeaderboardUsers.sort(key=sortSecond, reverse=True)

        i = 1
        everyPage = [item for item in guildLeaderboardUsers[10 * (i - 1):i * 10] if item[0] in guildMemberList]
        pageRankingStart = 10 * (i - 1) + 1
        pages = math.ceil(len(guildLeaderboardUsers) / 10)

        lengthRecord = []

        for item in everyPage:
            lengthDescription = ''
            member = self.bot.get_user(item[0])

            rankLength = len(f"{pageRankingStart}. |")
            lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
            moneyLength = len(f" {item[1]:,} |")
            lengthDescription += f'{(14 - moneyLength) * " "}{item[1]:,} |'
            lengthDescription += f' {member}\n'
            lengthRecord.append(len(lengthDescription))
            pageRankingStart += 1

        authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

        authorExp = authorProfile[0][1]
        guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
        authorRank = guildLeaderboardID.index(ctx.author.id) + 1

        lengthDescription = ''

        rankLength = len(f"{authorRank}. |")
        lengthDescription += f'{(7 - rankLength) * " "}{authorRank:,}. |'
        moneyLength = len(f" {authorExp:,} |")
        lengthDescription += f'{(14 - moneyLength) * " "}{authorExp:,} |'
        lengthDescription += f' {ctx.author}\n'
        lengthRecord.append(len(lengthDescription))

        description = f'```yaml\nRank. | Currency   | Username\n{max(lengthRecord) * "="}\n'

        pageRankingStart = 10 * (i - 1) + 1

        for item in everyPage:
            member = self.bot.get_user(item[0])

            rankLength = len(f"{pageRankingStart}. |")
            description += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
            EXPLength = len(f" {item[1]:,} |")
            description += f'{(14 - EXPLength) * " "}{item[1]:,} |'
            description += f' {member}\n'
            pageRankingStart += 1

        description += f'{max(lengthRecord) * "~"}\n'

        authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

        authorExp = authorProfile[0][1]
        guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
        authorRank = guildLeaderboardID.index(ctx.author.id) + 1

        rankLength = len(f"{authorRank}. |")
        description += f'{(7 - rankLength) * " "}{authorRank:,}. |'
        moneyLength = len(f" {authorExp:,} |")
        description += f'{(14 - moneyLength) * " "}{authorExp:,} |'
        description += f' {ctx.author}\n'

        description += '```'

        embed = discord.Embed(title=f"{ctx.guild}'s Leaderboard",
                              description=description,
                              timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
        embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)
        await msg.add_reaction('⏪')
        await msg.add_reaction('⏩')

        def check(reaction, user):
            return str(reaction.emoji) in ['⏪', '⏩'] and user == ctx.message.author and reaction.message.id == msg.id

        async def handle_rotate(reaction, msg, check, i):
            await msg.remove_reaction(reaction, ctx.message.author)

            if str(reaction.emoji) == '⏩':
                i += 1

                if i > pages:
                    embed = discord.Embed(description=f"You have reached the end of the pages!")
                    embed.set_footer(text=f"Press '⏪' to go back.", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

                else:

                    everyPage = [item for item in guildLeaderboardUsers[10 * (i - 1):i * 10] if
                                 item[0] in guildMemberList]
                    pageRankingStart = 10 * (i - 1) + 1

                    lengthRecord = []

                    for item in everyPage:
                        lengthDescription = ''
                        member = self.bot.get_user(item[0])

                        rankLength = len(f"{pageRankingStart}. |")
                        lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        moneyLength = len(f" {item[1]:,} |")
                        lengthDescription += f'{(14 - moneyLength) * " "}{item[1]:,} |'
                        lengthDescription += f' {member}\n'
                        lengthRecord.append(len(lengthDescription))
                        pageRankingStart += 1

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1

                    lengthDescription = ''

                    rankLength = len(f"{authorRank}. |")
                    lengthDescription += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    moneyLength = len(f" {authorExp:,} |")
                    lengthDescription += f'{(14 - moneyLength) * " "}{authorExp:,} |'
                    lengthDescription += f' {ctx.author}\n'
                    lengthRecord.append(len(lengthDescription))

                    description = f'```yaml\nRank. | Currency   | Username\n{max(lengthRecord) * "="}\n'

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        member = self.bot.get_user(item[0])

                        rankLength = len(f"{pageRankingStart}. |")
                        description += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        EXPLength = len(f" {item[1]:,} |")
                        description += f'{(14 - EXPLength) * " "}{item[1]:,} |'
                        description += f' {member}\n'
                        pageRankingStart += 1

                    description += f'{max(lengthRecord) * "~"}\n'

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1

                    rankLength = len(f"{authorRank}. |")
                    description += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    moneyLength = len(f" {authorExp:,} |")
                    description += f'{(14 - moneyLength) * " "}{authorExp:,} |'
                    description += f' {ctx.author}\n'

                    description += '```'

                    embed = discord.Embed(title=f"{ctx.guild}'s Leaderboard",
                                          description=description,
                                          timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
                    embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)

                await msg.edit(embed=embed)

            elif str(reaction.emoji) == '⏪':

                i -= 1

                if i <= 0:

                    embed = discord.Embed(description=f"You have reached the end of the pages!")
                    embed.set_footer(text=f"Press '⏩' to go back.", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

                else:

                    everyPage = [item for item in guildLeaderboardUsers[10 * (i - 1):i * 10] if
                                 item[0] in guildMemberList]
                    pageRankingStart = 10 * (i - 1) + 1

                    lengthRecord = []

                    for item in everyPage:
                        lengthDescription = ''
                        member = self.bot.get_user(item[0])

                        rankLength = len(f"{pageRankingStart}. |")
                        lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        moneyLength = len(f" {item[1]:,} |")
                        lengthDescription += f'{(14 - moneyLength) * " "}{item[1]:,} |'
                        lengthDescription += f' {member}\n'
                        lengthRecord.append(len(lengthDescription))
                        pageRankingStart += 1

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1

                    lengthDescription = ''

                    rankLength = len(f"{authorRank}. |")
                    lengthDescription += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    moneyLength = len(f" {authorExp:,} |")
                    lengthDescription += f'{(14 - moneyLength) * " "}{authorExp:,} |'
                    lengthDescription += f' {ctx.author}\n'
                    lengthRecord.append(len(lengthDescription))

                    description = f'```yaml\nRank. | Currency   | Username\n{max(lengthRecord) * "="}\n'

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        member = self.bot.get_user(item[0])

                        rankLength = len(f"{pageRankingStart}. |")
                        description += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        EXPLength = len(f" {item[1]:,} |")
                        description += f'{(14 - EXPLength) * " "}{item[1]:,} |'
                        description += f' {member}\n'
                        pageRankingStart += 1

                    description += f'{max(lengthRecord) * "~"}\n'

                    authorProfile = [item for item in leaderboardUsers if item[0] == ctx.author.id]

                    authorExp = authorProfile[0][1]
                    guildLeaderboardID = [user[0] for user in guildLeaderboardUsers]
                    authorRank = guildLeaderboardID.index(ctx.author.id) + 1

                    rankLength = len(f"{authorRank}. |")
                    description += f'{(7 - rankLength) * " "}{authorRank:,}. |'
                    moneyLength = len(f" {authorExp:,} |")
                    description += f'{(14 - moneyLength) * " "}{authorExp:,} |'
                    description += f' {ctx.author}\n'

                    description += '```'

                    embed = discord.Embed(title=f"{ctx.guild}'s Leaderboard",
                                          description=description,
                                          timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
                    embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

            else:
                return

            reaction, user = await self.bot.wait_for('reaction_add', check=check)
            await handle_rotate(reaction, msg, check, i)

        reaction, user = await self.bot.wait_for('reaction_add', check=check)
        await handle_rotate(reaction, msg, check, i)


    @commands.command(description=f"daily**\n\nClaim your dailies! Resets on 12a.m. GMT+8 everyday!\nCommand Aliases: `d`", aliases=['d'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def daily(self, ctx):

        streak = dailyGet(ctx.author.id)

        if not streak:
            c.execute(''' SELECT dailyCheck FROM userDaily WHERE user_id = ? ''', (ctx.author.id,))
            profile = c.fetchall()
            result = profile[0]
            dailyCheck = result[0]
            timeNow = int(datetime.datetime.now(pytz.timezone("Singapore")).timestamp())
            secondsLeft = dailyCheck - timeNow

            def dmyConverter(secondsLeft):
                secondsInDays = 60 * 60 * 24
                secondsInHours = 60 * 60
                secondsInMinutes = 60

                days = secondsLeft // secondsInDays
                hours = (secondsLeft - (days * secondsInDays)) // secondsInHours
                minutes = ((secondsLeft - (days * secondsInDays)) - (hours * secondsInHours)) // secondsInMinutes
                remainingSeconds = secondsLeft - (days * secondsInDays) - (hours * secondsInHours) - (
                        minutes * secondsInMinutes)

                return hours, minutes, remainingSeconds

            timeLeft = dmyConverter(secondsLeft)

            return await cogs.functions.errorEmbedTemplate(ctx,
                                                    f"You've already claimed your dailies for today!\n\nPlease try again in {timeLeft[0]} hours, {timeLeft[1]} minutes, {timeLeft[2]} seconds.",
                                                    ctx.message.author)

        currentStreak = streak[0]

        if currentStreak == 10:
            coinsGained = random.choice(range(100, 200)) * 2
        else:
            coinsGained = random.choice(range(100, 200))

        description = f"You've successfully claimed your daily of **{coinsGained}** {determineSymbol(ctx.guild.id)}!\n\n"
        description += f'**Current Daily Streak:**\n{currentStreak}/10\n\n'

        startingBar = barHandler(currentStreak)[0]
        progressBar = barHandler(currentStreak)[1]
        endingBar = barHandler(currentStreak)[2]
        description += f"{startingBar}{progressBar}{endingBar}"

        if currentStreak == 10:
            description += "\n\nYou've completed a streak of ten and your daily reward has been doubled!"

        coinTransaction(ctx.author.id, coinsGained)

        embed = discord.Embed(title="You have successfully claimed your daily rewards!", description=description,
                              colour=cogs.functions.embedColour(ctx.guild.id))
        embed.set_footer(text=f"Daily resets at 00:00 GMT+8")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Economy(bot))
