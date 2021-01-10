import datetime
import discord
import pytz
from discord.ext import commands
import sqlite3
import random

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

serverConn = sqlite3.connect('server.db', timeout=5.0)
serverC = serverConn.cursor()


serverC.execute('''CREATE TABLE IF NOT EXISTS serverRanking (`server_id` INT PRIMARY KEY, `minExp` INT, `maxExp` INT, `minMoney` INT, `maxMoney` INT) ''')

def profileGet(id):
    c.execute(''' SELECT currentExp, money, cooldown FROM userProfile WHERE user_id = ? ''', (id,))
    profile = c.fetchall()[0]

    currentExp = profile[0]
    currentMoney = profile[1]
    cooldown = profile[2]

    return currentExp, currentMoney, cooldown

def profileTransaction(id, expAmount: int, moneyAmount: int):
    userProfile = profileGet(id)
    currentExp = userProfile[0]
    currentMoney = userProfile[1]
    cooldown = userProfile[2]

    now = int(datetime.datetime.now(pytz.timezone("Singapore")).timestamp())

    if now > cooldown + 60:
        currentExp += expAmount
        currentMoney += moneyAmount
        c.execute(''' UPDATE userProfile SET currentExp = ?, money = ?, cooldown = ? WHERE user_id = ? ''', (currentExp, currentMoney, now, id))
        conn.commit()
    else:
        return

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

def guildCreate(id):
    serverC.execute('''INSERT OR REPLACE INTO serverRanking VALUES (?, ?, ?, ?, ?)''', (id, 5, 10, 5, 10))
    conn.commit()

def guildStatsEXP(id):
    serverC.execute(''' SELECT minExp, maxExp FROM serverRanking WHERE server_id = ? ''', (id,))
    result = serverC.fetchall()[0]
    return result[0], result[1]

def guildStatsCurrency(id):
    serverC.execute(''' SELECT minMoney, maxMoney FROM serverRanking WHERE server_id = ? ''', (id,))
    result = serverC.fetchall()[0]
    return result[0], result[1]

def getUserLevel(id):
    currentExp = profileGet(id)[0]
    currentLevel = getLevel(currentExp)

    return currentLevel


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):

        guildDatabase = [guild[0] for guild in serverC.execute('SELECT server_id FROM serverRanking')]

        for guild in self.bot.guilds:
            if guild.id not in guildDatabase:
                guildCreate(guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        guildDatabase = [guild[0] for guild in serverC.execute('SELECT server_id FROM serverRanking')]

        if guild.id not in guildDatabase:
            guildCreate(guild.id)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        userLevel = getUserLevel(message.author.id)

        serverStats = guildStatsEXP(message.guild.id)
        minExp = serverStats[0]
        maxExp = serverStats[1]
        expGain = random.choice(range(minExp, maxExp + 1)) * (1 + userLevel * 0.02)

        serverStats = guildStatsCurrency(message.guild.id)
        minMoney = serverStats[0]
        maxMoney = serverStats[1]
        moneyGain = round(random.choice(range(minMoney, maxMoney + 1)) * (1 + userLevel * 0.02))

        profileTransaction(message.author.id, expGain, moneyGain)

        newUserLevel = getUserLevel(message.author.id)

        if newUserLevel > userLevel:
            profileTransaction(message.author.id, 0, moneyGain * 100)
            embed = discord.Embed(title="Congratulations!", description=f"{message.author.mention} is now Level {newUserLevel} and has gained {moneyGain * 100:,} as their leveling reward!")
            await message.channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Leveling(bot))
