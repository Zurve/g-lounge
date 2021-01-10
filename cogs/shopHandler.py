import asyncio
import math
import sqlite3
import traceback
from cogs.currencyHandler import determineSymbol
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import cogs.functions
import datetime
import pytz

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

invConn = sqlite3.connect('shop.db', timeout=5.0)
invC = invConn.cursor()

invC.execute(
    '''CREATE TABLE IF NOT EXISTS shopsettings (`server_id` INT PRIMARY KEY, `name` TEXT, `description` TEXT, `thankyoumessage` TEXT) ''')
invC.execute(
    '''CREATE TABLE IF NOT EXISTS inventory (`user_id` INT PRIMARY KEY, `Raffle Ticket` INT NOT NULL DEFAULT 0) ''')
invC.execute('''CREATE TABLE IF NOT EXISTS shop (`server_id` INT, `item` TEXT, `price` INT, `stock` TEXT, `role` TEXT) ''')
invC.execute('''CREATE TABLE IF NOT EXISTS shophistory (`server_id` INT, `item` TEXT, `price` INT, `stock` TEXT, `role` TEXT) ''')


def itemChecker(item):
    invC.execute(f''' SELECT item, price, stock, role FROM shophistory WHERE item = ?''', (f"{item}",))
    itemProperties = invC.fetchall()[0]

    itemName = itemProperties[0]
    itemPrice = itemProperties[1]

    if itemProperties[2] == 0:
        itemStock = "Unlimited"
    else:
        itemStock = itemProperties[2]

    if itemProperties[3] != "none" or itemProperties[3] != "skip":
        itemRole = itemProperties[3]
        return itemName, itemPrice, itemStock, itemRole

    else:
        return itemName, itemPrice, itemStock


def coinTransaction(id, amount):
    c.execute(''' SELECT money FROM userProfile WHERE user_id = ? ''', (id,))
    coins = c.fetchall()[0][0]
    updatedCoins = coins + amount
    c.execute(''' UPDATE userProfile SET money = ? WHERE user_id = ? ''', (updatedCoins, id))
    conn.commit()


def coinGet(id):
    c.execute(''' SELECT money FROM userProfile WHERE user_id = ? ''', (id,))
    coins = c.fetchall()[0][0]

    return coins


def stockTransaction(amount, item):
    invC.execute(f''' SELECT stock FROM shop WHERE item = "{item}" ''')
    result = invC.fetchall()

    for data in result:
        stockAvailable = int(data[0])
        stockAvailable += amount
        invC.execute(f''' UPDATE shop SET stock = ? WHERE item = ? ''', (stockAvailable, item))
        invConn.commit()
    return


async def shopEmbed(ctx, author, nameMessage=None, priceMessage=None, stockMessage="", roleMessage=None):
    embed = discord.Embed(title=f"Product Item Information",
                          description=f"As you respond with more information, item info will show up below.")
    embed.set_footer(text=f'Type "cancel" to cancel.', icon_url=author.avatar_url)
    try:
        embed.add_field(name="Item", value=f"{nameMessage.content}")
    except:
        pass
    try:
        embed.add_field(name="Price", value=f"{priceMessage.content}")
    except:
        pass
    try:
        if stockMessage == "":
            pass
        else:
            embed.add_field(name="Stock", value=f"{stockMessage}")
    except:
        pass
    try:
        if roleMessage.content == "none" or roleMessage.content =="skip":
            pass
        else:
            embed.add_field(name="Acquired Role", value=f"{roleMessage.content}")
    except:
        pass

    return await ctx.send(embed=embed)


async def shopErrorEmbed(ctx, author, nameMessage=None, priceMessage=None, stockMessage=""):
    embed = discord.Embed(title=f"Error!",
                          description=f"Invalid Price/Role/Argument provided. Please make sure your input is a valid positive integer or role mention!")
    embed.set_footer(text=f'Type "cancel" to cancel.', icon_url=author.avatar_url)
    try:
        embed.add_field(name="Item", value=f"{nameMessage.content}")
    except:
        pass
    try:
        embed.add_field(name="Price", value=f"{priceMessage.content} {determineSymbol(ctx.guild.id)}")
    except:
        pass
    try:
        if stockMessage == "":
            pass
        else:
            embed.add_field(name="Stock", value=f"{stockMessage}")
    except:
        pass

    return await ctx.send(embed=embed)


class Shop(commands.Cog, name="🛒 Shop"):  # You create a class instance and everything goes in it

    def __init__(self, bot):  # This runs when you first load this extension script
        self.bot = bot

    @commands.command(description="use [item name]**\n\nUses an item.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def use(self, ctx, *, itemName: str):

        invC.execute(f''' SELECT "{itemName}" FROM inventory WHERE user_id = {ctx.message.author.id}''')
        result = invC.fetchall()

        try:
            itemProperties = itemChecker(itemName)

        except IndexError:
            return await cogs.functions.errorEmbedTemplate(ctx, "Item does not exist!", ctx.message.author)

        itemQuantity = result[0][0]

        if itemQuantity <= 0:
            return await cogs.functions.errorEmbedTemplate(ctx, "You do not possess any of the said item!", ctx.message.author)

        if itemName == "Raffle Ticket":
            return await cogs.functions.errorEmbedTemplate(ctx, f"You cannot use Raffle Ticket!", ctx.message.author)

        else:
            itemQuantity -= 1
            invC.execute(f''' UPDATE inventory SET "{itemName}" = ? WHERE user_id = ? ''',
                      (itemQuantity, ctx.message.author.id))
            invConn.commit()

            try:
                acquiredRole = itemProperties[3]
                roleToGiveID = acquiredRole.replace('<', '').replace('>', '').replace('@', '').replace('&', '')
                givenRole = ctx.guild.get_role(role_id=int(roleToGiveID))
                await ctx.message.author.add_roles(givenRole)
                await cogs.functions.successEmbedTemplate(ctx, f"You've gained the {givenRole.mention} role!", ctx.message.author)
            except:
                traceback.print_exc()

            await cogs.functions.successEmbedTemplate(ctx, f"You have used `{itemName}`!", ctx.message.author)

    @commands.command(description="reset [user mention]**\n\nResets a user's inventory! Administrator Only!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def resetinv(self, ctx, user: discord.Member):

        invC.execute(f''' SELECT * FROM inventory WHERE user_id = {user.id}''')
        names = list(map(lambda x: x[0], invC.description))
        result = invC.fetchall()
        userData = result[0]

        i = 1

        for item in userData:
            try:
                invC.execute(f''' UPDATE inventory SET "{names[i]}" = ? WHERE user_id = ? ''', (0, user.id))
                conn.commit()
                i += 1
            except:
                pass

        await cogs.functions.requestEmbedTemplate(ctx, f"{user.mention}'s inventory has been successfully reset!",
                                                  ctx.message.author)

    @commands.command(description="shopsettings**\n\nSets the title and description of the shop. Administrator Only!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def shopsettings(self, ctx):

        def messageCheck(m):
            return m.channel == ctx.message.channel and m.author == ctx.message.author

        try:
            await cogs.functions.requestEmbedTemplate(ctx, "What will be the title of your shop?", ctx.message.author)
            titleMessage = await self.bot.wait_for('message', check=messageCheck, timeout=30)
            await cogs.functions.requestEmbedTemplate(ctx, "What will be the description of your shop?",
                                                      ctx.message.author)
            descriptionMessage = await self.bot.wait_for('message', check=messageCheck, timeout=30)
            await cogs.functions.requestEmbedTemplate(ctx, "What will be the thank you message of your shop?",
                                                      ctx.message.author)
            thankYouMessage = await self.bot.wait_for('message', check=messageCheck, timeout=30)

            description = "**These are your shop details:**\n\n"
            description += f"**Title:** {titleMessage.content}\n\n"
            description += f"**Description:** {descriptionMessage.content}\n\n"
            description += f"**Thank You Message:** {thankYouMessage.content}\n\n"
            description += "This is the information you gave me. Is it correct?\n"
            description += "Please react accordingly if it's correct. Otherwise, I will cancel the entry."

            msg = await cogs.functions.requestEmbedTemplate(ctx, description, ctx.message.author)

            await msg.add_reaction("☑")
            await msg.add_reaction("❌")

            def confirmationCheck(reaction, user):
                return str(reaction.emoji) in ['☑',
                                               '❌'] and user == ctx.message.author and reaction.message.id == msg.id

            reaction, user = await self.bot.wait_for('reaction_add', check=confirmationCheck, timeout=30)

            if str(reaction.emoji) == "❌":
                await cogs.functions.requestEmbedTemplate(ctx, "Shop set-up cancelled.", ctx.message.author)

            elif str(reaction.emoji) == "☑":
                invC.execute(''' INSERT OR REPLACE INTO shopsettings VALUES (?, ?, ?, ?) ''',
                          (ctx.guild.id, titleMessage.content, descriptionMessage.content, thankYouMessage.content))
                invConn.commit()
                invC.execute(''' INSERT OR REPLACE INTO shop VALUES (?, ?, ?, ?, ?) ''',
                          (ctx.guild.id, "Raffle Ticket", 500, "Unlimited", "none"))
                invConn.commit()
                invC.execute(''' INSERT OR REPLACE INTO shophistory VALUES (?, ?, ?, ?, ?) ''',
                          (ctx.guild.id, "Raffle Ticket", 500, "Unlimited", "none"))
                invConn.commit()
                await cogs.functions.requestEmbedTemplate(ctx, "☑️ Shop Created Successfully.", ctx.message.author)

        except asyncio.TimeoutError:
            await cogs.functions.requestEmbedTemplate(ctx,
                                                      "HMPH! You took too long to respond. Try again when you're going to respond to me!",
                                                      ctx.message.author)

    @commands.command(
        description="setshop**\n\nInteractive Administrator Command to set up an item (add/edit/delete) for the shop.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def setshop(self, ctx):
        msg = await cogs.functions.requestEmbedTemplate(ctx,
                                                        "Would you like to `add` a new item or `remove` an existing item or `edit` an existing item?\nPlease react with ➕, ➖ or 🛠️ respectively.\nyou can cancel this command by reacting with ❌.",
                                                        ctx.message.author)
        await msg.add_reaction("➕")
        await msg.add_reaction("➖")
        await msg.add_reaction("🛠️")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return str(reaction.emoji) in ['➕', '➖', '🛠️',
                                           '❌'] and user == ctx.message.author and reaction.message.id == msg.id

        try:

            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=30)

            def messageCheck(m):
                return m.channel == ctx.message.channel and m.author == ctx.message.author

            if str(reaction.emoji) == "➕":
                await ctx.send("**What should the name of the item be?**")
                msg = await shopEmbed(ctx, ctx.message.author)
                nameMessage = await self.bot.wait_for('message', check=messageCheck)

                items = [item[0] for item in
                         invC.execute(f''' SELECT item FROM shop WHERE server_id = ? ''', (ctx.guild.id,))]

                if nameMessage.content == "cancel":
                    return await cogs.functions.successEmbedTemplate(ctx,
                                                                     "Item creation / deletion / editing cancelled.",
                                                                     ctx.message.author)

                elif nameMessage.content in items:
                    return await cogs.functions.errorEmbedTemplate(ctx,
                                                                   "The item already exist! Please restart the command and use a different name!",
                                                                   ctx.message.author)

                else:
                    await ctx.send("**How much will this item cost?**")
                    msg = await shopEmbed(ctx, ctx.message.author, nameMessage)

                    priceMessage = await self.bot.wait_for('message', check=messageCheck)

                    while not priceMessage.content.isdigit() or priceMessage.content == "0" or priceMessage.content == "cancel":

                        await ctx.send("**How much will this item cost?**")
                        msg = await shopErrorEmbed(ctx, ctx.message.author, nameMessage)

                        priceMessage = await self.bot.wait_for('message', check=messageCheck)

                        if priceMessage.content == "cancel":
                            return await cogs.functions.requestEmbedTemplate(ctx,
                                                                             "Item creation / deletion / editing cancelled.",
                                                                             ctx.message.author)

                    if priceMessage.content.isdigit():

                        await ctx.send(
                            "**How many of this item will be sold before removed from the shop?\nPlease put 0 for unlimited / infinity.**")
                        msg = await shopEmbed(ctx, ctx.message.author, nameMessage, priceMessage)
                        stockMessage = await self.bot.wait_for('message', check=messageCheck)

                        while not stockMessage.content.isdigit() or str(stockMessage.content) == "cancel" or int(
                                stockMessage.content) < 0:

                            await ctx.send(
                                "**How many of this item will be sold before removed from the shop?\nPlease put 0 for unlimited / infinity.**")

                            msg = await shopErrorEmbed(ctx, ctx.message.author, nameMessage,
                                                       priceMessage)

                            stockMessage = await self.bot.wait_for('message', check=messageCheck)

                            if stockMessage.content == "cancel":
                                return await cogs.functions.requestEmbedTemplate(ctx,
                                                                                 "Item creation / deletion / editing cancelled.",
                                                                                 ctx.message.author)

                        if stockMessage.content.isdigit():
                            if stockMessage.content == "0":
                                enteredStock = "Unlimited"
                            else:
                                enteredStock = stockMessage.content

                            await ctx.send(
                                "**What role will be rewarded / given to the user when they use this item?**\nPlease put `none` or `skip` if you don't want a rewarded role.")

                            msg = await shopEmbed(ctx, ctx.message.author, nameMessage, priceMessage, enteredStock)

                            roleMentions = []

                            for role in ctx.guild.roles:
                                roleMentions.append(role.mention)

                            roleMessage = await self.bot.wait_for('message', check=messageCheck)

                            if roleMessage.content == "cancel":
                                return await cogs.functions.successEmbedTemplate(ctx, "Item creation / deletion / editing cancelled.", ctx.message.author)

                            while roleMessage.content not in roleMentions:
                                if roleMessage.content == "none" or roleMessage.content == "skip":
                                    break

                                elif roleMessage.content == "cancel":
                                    return await cogs.functions.successEmbedTemplate(ctx,
                                                                                     "Item creation / deletion / editing cancelled.",
                                                                                     ctx.message.author)

                                else:
                                    await ctx.send(
                                        "**What role will be rewarded / given to the user when they use this item?**\nPlease put `none` or `skip` if you don't want a rewarded role.")

                                    await shopErrorEmbed(ctx, ctx.message.author, nameMessage, priceMessage, enteredStock)

                                    roleMessage = await self.bot.wait_for('message', check=messageCheck)

                            await ctx.send("**Wonderful Job! This is the information you gave me. Is it correct?**\nPlease react accordingly if it's correct. Otherwise, I will cancel item creation so you can start all over again.")
                            msg = await shopEmbed(ctx, ctx.message.author, nameMessage, priceMessage,
                                                  enteredStock, roleMessage)

                            await msg.add_reaction("☑")
                            await msg.add_reaction("❌")

                            def confirmationCheck(reaction, user):
                                return str(reaction.emoji) in ['☑',
                                                               '❌'] and user == ctx.message.author and reaction.message.id == msg.id

                            reaction, user = await self.bot.wait_for('reaction_add',
                                                                     check=confirmationCheck,
                                                                     timeout=30)

                            if str(reaction.emoji) == "❌":
                                await cogs.functions.requestEmbedTemplate(ctx,
                                                                          "Item creation / deletion / editing cancelled.",
                                                                          ctx.message.author)

                            elif str(reaction.emoji) == "☑":
                                invC.execute(''' INSERT OR REPLACE INTO shop VALUES (?, ?, ?, ?, ?) ''', (
                                    ctx.message.guild.id, nameMessage.content, priceMessage.content, enteredStock, roleMessage.content))
                                invConn.commit()
                                invC.execute(
                                    ''' INSERT OR REPLACE INTO shophistory VALUES (?, ?, ?, ?, ?) ''',
                                    (ctx.message.guild.id, nameMessage.content,
                                     priceMessage.content, enteredStock, roleMessage.content))
                                invConn.commit()
                                addItems = f"ALTER TABLE inventory ADD COLUMN `{nameMessage.content}` DEFAULT 0"
                                invC.execute(addItems)
                                invConn.commit()
                                await cogs.functions.requestEmbedTemplate(ctx,
                                                                          "☑️ Item Created Successfully.",
                                                                          ctx.message.author)

            elif str(reaction.emoji) == "➖":
                items = []
                invC.execute(f''' SELECT item FROM shop ''')
                result = invC.fetchall()

                for item in result:
                    items.append(item[0])

                def messageCheck(m):
                    return m.channel == ctx.message.channel and m.author == ctx.message.author

                try:
                    await cogs.functions.requestEmbedTemplate(ctx,
                                                              "Please respond with the name of the item you'd like me to remove.\nYou can cancel this command using `cancel`",
                                                              ctx.message.author)

                    itemName = await self.bot.wait_for('message', check=messageCheck, timeout=30)

                    if itemName.content == "cancel":
                        await cogs.functions.requestEmbedTemplate(ctx, "Item creation / deletion / editing cancelled.",
                                                                  ctx.message.author)

                    elif itemName.content not in items:
                        await cogs.functions.requestEmbedTemplate(ctx,
                                                                  "This item doesn't exist. Please restart the command!",
                                                                  ctx.message.author)

                    elif itemName.content == "Raffle Ticket":
                        return await cogs.functions.errorEmbedTemplate(ctx,
                                                                       "You cannot delete Raffle Ticket!",
                                                                       ctx.message.author)

                    else:
                        invC.execute(f'SELECT item, price, stock, role FROM shop WHERE server_id = ? AND item = ?',
                                  (ctx.message.guild.id, itemName.content))

                        items = invC.fetchall()
                        item = items[0]
                        itemDetails = ""

                        if item[2] != 0:
                            itemDetails += f"Stock Available: {item[2]}\n"

                        else:
                            itemDetails += "> Stock Available: Unlimited\n"

                        embed = discord.Embed(title="Deleted Products")

                        embed.add_field(name=f"{item[1]} • {item[0]} ", value=f"{itemDetails}", inline=False)

                        invC.execute(''' DELETE FROM shop where item = ? ''', (f"{itemName.content}",))
                        invConn.commit()
                        await ctx.send(embed=embed)

                except asyncio.TimeoutError:
                    await cogs.functions.requestEmbedTemplate(ctx,
                                                              "HMPH! You took too long to respond. Try again when you're going to respond to me!",
                                                              ctx.message.author)

            elif str(reaction.emoji) == "🛠️":
                items = []
                invC.execute(f''' SELECT item FROM shop ''')
                result = invC.fetchall()

                for item in result:
                    items.append(item[0])

                def messageCheck(m):
                    return m.channel == ctx.message.channel and m.author == ctx.message.author

                try:
                    await cogs.functions.requestEmbedTemplate(ctx,
                                                              "Please respond with the name of the item you'd like me to edit.\nYou can cancel this command using `cancel`",
                                                              ctx.message.author)
                    itemName = await self.bot.wait_for('message', check=messageCheck, timeout=30)

                    if itemName.content == "cancel":
                        await cogs.functions.requestEmbedTemplate(ctx, "Item creation / deletion / editing cancelled.",
                                                                  ctx.message.author)


                    elif itemName.content not in items:
                        await cogs.functions.requestEmbedTemplate(ctx,
                                                                  "This item doesn't exist. Please restart the command!",
                                                                  ctx.message.author)

                    else:
                        await cogs.functions.requestEmbedTemplate(ctx,
                                                                  "What would you like to edit? Please name one of the following: `price` `stock`, `role`",
                                                                  ctx.message.author)

                        editMessage = await self.bot.wait_for('message', check=messageCheck, timeout=30)
                        validResponse = ['price', 'stock', 'role']
                        invC.execute(f'SELECT item, price, stock, role FROM shop WHERE server_id = ? AND item = ?',
                                  (ctx.guild.id, f"{itemName.content}"))

                        items = invC.fetchall()

                        if editMessage.content not in validResponse:
                            await cogs.functions.requestEmbedTemplate(ctx,
                                                                      "This is not a valid response. Please restart the command!",
                                                                      ctx.message.author)


                        else:
                            if editMessage.content == "price":
                                await cogs.functions.requestEmbedTemplate(ctx,
                                                                          "What would you want the price to be changed to?",
                                                                          ctx.message.author)
                                priceMessage = await self.bot.wait_for('message', check=messageCheck, timeout=30)

                                if not priceMessage.content.isdigit() or priceMessage.content == "0":
                                    return await cogs.functions.requestEmbedTemplate(ctx,
                                                                                     "Invalid price amount! Please restart the command!",
                                                                                     ctx.message.author)

                                else:
                                    invC.execute(f''' UPDATE shop SET price = ? WHERE item = ? ''',
                                              (priceMessage.content, f"{itemName.content}"))
                                    invConn.commit()

                                    invC.execute(f''' UPDATE shophistory SET price = ? WHERE item = ? ''',
                                              (priceMessage.content, f"{itemName.content}"))
                                    invConn.commit()
                                    return await cogs.functions.requestEmbedTemplate(ctx,
                                                                                     f"Okie! Updated price to `{priceMessage.content}` successfully.",
                                                                                     ctx.message.author)

                            elif editMessage.content == "stock":
                                await cogs.functions.requestEmbedTemplate(ctx,
                                                                          "What would you want the stock to be changed to?",
                                                                          ctx.message.author)
                                stockMessage = await self.bot.wait_for('message', check=messageCheck, timeout=30)

                                if not stockMessage.content.isdigit() or int(stockMessage.content) < 0:
                                    return await cogs.functions.requestEmbedTemplate(ctx,
                                                                                     "Invalid stock amount! Please restart the command!",
                                                                                     ctx.message.author)

                                if stockMessage.content == 0:
                                    enteredStock = "Unlimited"
                                else:
                                    enteredStock = stockMessage.content

                                invC.execute(f''' UPDATE shop SET stock = ? WHERE item = ? ''',
                                          (enteredStock, f"{itemName.content}"))
                                invConn.commit()
                                invC.execute(f''' UPDATE shophistory SET stock = ? WHERE item = ? ''',
                                          ('Unlimited', f"{itemName.content}"))
                                invConn.commit()
                                return await cogs.functions.requestEmbedTemplate(ctx,
                                                                                 f"Okie! Updated stock to `{enteredStock}` successfully.",
                                                                                 ctx.message.author)

                            elif editMessage.content == "role":

                                roleMentions = []

                                for role in ctx.guild.roles:
                                    roleMentions.append(role.mention)

                                roleMessage = await self.bot.wait_for('message', check=messageCheck)

                                if roleMessage.content == "cancel":
                                    return await cogs.functions.successEmbedTemplate(ctx,
                                                                                     "Item creation / deletion / editing cancelled.",
                                                                                     ctx.message.author)

                                if roleMessage.content not in roleMentions and roleMessage.content != "none" and roleMessage.content != "skip":
                                    return await cogs.functions.requestEmbedTemplate(ctx,
                                                                                     "Invalid role! Please restart the command!",
                                                                                     ctx.message.author)

                                invC.execute(f''' UPDATE shop SET role = ? WHERE item = ? ''',
                                          (roleMessage.content, f"{itemName.content}"))
                                invConn.commit()
                                invC.execute(f''' UPDATE shophistory SET role = ? WHERE item = ? ''',
                                          (roleMessage.content, f"{itemName.content}"))
                                invConn.commit()
                                return await cogs.functions.requestEmbedTemplate(ctx,
                                                                                 f"Okie! Updated role to `{roleMessage.content}` successfully.",
                                                                                 ctx.message.author)

                except asyncio.TimeoutError:
                    await cogs.functions.requestEmbedTemplate(ctx,
                                                              "HMPH! You took too long to respond. Try again when you're going to respond to me!",
                                                              ctx.message.author)


            elif str(reaction.emoji) == "❌":
                await cogs.functions.requestEmbedTemplate(ctx, "Item creation / deletion / editing cancelled.",
                                                          ctx.message.author)


        except asyncio.TimeoutError:
            await cogs.functions.requestEmbedTemplate(ctx,
                                                      "HMPH! You took too long to respond. Try again when you're going to respond to me!",
                                                      ctx.message.author)

        except Exception as e:
            traceback.print_exc()

    @commands.command(description="buy [item name]**\n\nBuys an item (item name has to be case-sensitive).")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def buy(self, ctx, *, itemName: str):

        global roleRequirement

        invC.execute(f'SELECT item, price, stock, role FROM shop WHERE server_id = ? AND item = ?',
                  (ctx.message.guild.id, itemName))
        result = invC.fetchall()

        if not result:
            await cogs.functions.errorEmbedTemplate(ctx,
                                                    "There is no item with such name! Please make sure you have entered the correct item name.",
                                                    ctx.message.author)
            return

        await ctx.send(f"How many {itemName} would you like to buy?")

        def messageCheck(m):
            return m.channel == ctx.message.channel and m.author == ctx.message.author

        qtyMessage = await self.bot.wait_for('message', check=messageCheck)

        if not qtyMessage.content.isdigit() or qtyMessage.content == "0":
            return await cogs.functions.errorEmbedTemplate(ctx,
                                                           f"Quantity has to be a valid integer! Please restart the command and try again!",
                                                           ctx.message.author)

        buyingQty = int(qtyMessage.content)

        embed = discord.Embed(title="Your Cart: Is this the item you'd like to buy?",
                              description="Make sure it's the correct item. Item bought are **NOT** refundable!")

        for items in result:

            itemProperties = items

            itemName = itemProperties[0]
            embed.add_field(name=f"Item Name", value=f"{itemName}")
            itemPrice = itemProperties[1]
            embed.add_field(name=f"Price",
                            value=f"{'{:,}'.format(itemPrice * buyingQty)} {determineSymbol(ctx.guild.id)}")
            itemStock = itemProperties[2]
            embed.add_field(name=f"Stock Remaining", value=f"{itemStock}")

            if itemProperties[3] == "none" or itemProperties[3] == "skip":
                pass
            else:
                itemRole = itemProperties[3]
                embed.add_field(name=f"Acquired Role", value=f"{itemRole}")

            msg = await ctx.send(embed=embed)
            await msg.add_reaction("☑")
            await msg.add_reaction("❌")

            def confirmationCheck(reaction, user):
                return str(reaction.emoji) in ['☑',
                                               '❌'] and user == ctx.message.author and reaction.message.id == msg.id

            try:

                reaction, user = await self.bot.wait_for('reaction_add', check=confirmationCheck, timeout=30)

                if str(reaction.emoji) == "❌":
                    await cogs.functions.requestEmbedTemplate(ctx, "Purchase cancelled.", ctx.message.author)

                elif str(reaction.emoji) == "☑":
                    balance = coinGet(ctx.message.author.id)
                    balance -= itemPrice * buyingQty

                    if balance < 0:
                        return await cogs.functions.requestEmbedTemplate(ctx,
                                                                         f"❌ Purchase is unsuccessful.\n\nYou do not have sufficient balance to make this purchase.\n\n**Your Balance:** {balance + itemPrice * buyingQty:,}",
                                                                         ctx.message.author)

                    if itemStock != "Unlimited":
                        if int(itemStock) <= 0 or buyingQty > int(itemStock):
                            return await cogs.functions.requestEmbedTemplate(ctx,
                                                                             "❌ Purchase is unsuccessful.\n\nThere is insufficient stock for the item.",
                                                                             ctx.message.author)
                        stockTransaction(-buyingQty, itemName)

                    invC.execute(f''' SELECT "{itemName}" FROM inventory WHERE user_id = {ctx.message.author.id}''')
                    result = invC.fetchall()

                    itemQuantity = int(result[0][0])
                    itemQuantity += buyingQty

                    invC.execute(f'SELECT thankyoumessage FROM shopsettings WHERE server_id = ?', (ctx.guild.id,))
                    result = invC.fetchall()

                    thankYouMessage = result[0][0]

                    coinTransaction(ctx.message.author.id, (-itemPrice * buyingQty))
                    invC.execute(f''' UPDATE inventory SET "{itemName}" = ? WHERE user_id = ? ''',
                              (itemQuantity, ctx.message.author.id))
                    invConn.commit()
                    return await cogs.functions.requestEmbedTemplate(ctx,
                                                                     f"☑️ Purchase is successful.\n\n{thankYouMessage}\n\n**Balance:** {'{:,}'.format(balance)}\n**{itemName}'s Quantity (Now):** {'{:,}'.format(itemQuantity)}",
                                                                     ctx.message.author)

            except asyncio.TimeoutError:
                await cogs.functions.requestEmbedTemplate(ctx,
                                                          "HMPH! You took too long to respond. Try again when you're going to respond to me!",
                                                          ctx.message.author)

    @commands.command(description="inv**\n\nShows your inventory and the item you currently own!", aliases=["inv", "i"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def inventory(self, ctx):

        invC.execute(f''' SELECT * FROM inventory WHERE user_id = {ctx.author.id}''')
        names = list(map(lambda x: x[0], invC.description))
        names.pop(0)
        myInventory = invC.fetchall()[0]
        inventoryList = list(myInventory)
        inventoryList.pop(0)
        itemList = []

        j = 0
        for item in inventoryList:
            itemName = names[j]
            qty = inventoryList[j]
            itemList.append((itemName, qty))
            j += 1

        i = 1
        pageRankingStart = 1
        everyPage = [item for item in itemList[10 * (i - 1):i * 10] if item[1] != 0]
        pages = math.ceil(len(itemList) / 10)

        lengthRecord = []

        for item in everyPage:
            lengthDescription = ''
            rankLength = len(f"{pageRankingStart}. |")
            lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
            itemLength = len(f" {item[0]} |")
            lengthDescription += f'{(24 - itemLength) * " "}{item[0]} |'
            quantityLength = len(f" {item[1]} |")
            lengthDescription += f'{(14 - quantityLength) * " "}{item[1]} |'
            lengthRecord.append(len(lengthDescription))
            pageRankingStart += 1

        description = f'```yaml\nNo. |    Item               | Quantity |\n{max(lengthRecord) * "="}\n'

        pageRankingStart = 10 * (i - 1) + 1

        for item in everyPage:
            rankLength = len(f"{pageRankingStart}. |")
            description += f'{(5 - rankLength) * " "}{pageRankingStart}. |'
            itemLength = len(f" {item[0]} |")
            description += f'{(25 - itemLength) * " "}{item[0]} |'
            quantityLength = len(f" {item[1]} |")
            description += f'{(12 - quantityLength) * " "}{item[1]} |\n'
            pageRankingStart += 1

        description += '```'

        embed = discord.Embed(title=f"{ctx.author}'s Inventory",
                              description=description,
                              timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
        embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)
        await msg.add_reaction('⏪')
        await msg.add_reaction('⏩')

        def check(reaction, user):

            return str(reaction.emoji) in ['⏪',
                                           '⏩'] and user == ctx.message.author and reaction.message.id == msg.id

        async def handle_rotate(reaction, msg, check, i):

            await msg.remove_reaction(reaction, ctx.message.author)

            if str(reaction.emoji) == '⏩':

                i += 1

                if i > pages:

                    embed = discord.Embed(description=f"You have reached the end of the pages!")
                    embed.set_thumbnail(url=f"{ctx.message.guild.icon_url}")
                    embed.set_footer(text=f"Press '⏪' to go back.", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

                else:

                    everyPage = [item for item in itemList[10 * (i - 1):i * 10] if item[1] != 0]
                    lengthRecord = []

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        lengthDescription = ''
                        rankLength = len(f"{pageRankingStart}. |")
                        lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        itemLength = len(f" {item[0]} |")
                        lengthDescription += f'{(24 - itemLength) * " "}{item[0]} |'
                        quantityLength = len(f" {item[1]} |")
                        lengthDescription += f'{(14 - quantityLength) * " "}{item[1]} |'
                        lengthRecord.append(len(lengthDescription))
                        pageRankingStart += 1

                    description = f'```yaml\nNo. |    Item               | Quantity |\n{max(lengthRecord) * "="}\n'

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        rankLength = len(f"{pageRankingStart}. |")
                        description += f'{(5 - rankLength) * " "}{pageRankingStart}. |'
                        itemLength = len(f" {item[0]} |")
                        description += f'{(25 - itemLength) * " "}{item[0]} |'
                        quantityLength = len(f" {item[1]} |")
                        description += f'{(12 - quantityLength) * " "}{item[1]} |\n'
                        pageRankingStart += 1

                    description += '```'

                    embed = discord.Embed(title=f"{ctx.author}'s Inventory",
                                          description=description,
                                          timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
                    embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

            elif str(reaction.emoji) == '⏪':

                i -= 1

                if i <= 0:

                    embed = discord.Embed(description=f"You have reached the end of the pages!")
                    embed.set_thumbnail(url=f"{ctx.message.guild.icon_url}")
                    embed.set_footer(text=f"Press '⏩' to go back.", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

                else:

                    everyPage = [item for item in itemList[10 * (i - 1):i * 10] if item[1] != 0]
                    lengthRecord = []

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        lengthDescription = ''
                        rankLength = len(f"{pageRankingStart}. |")
                        lengthDescription += f'{(7 - rankLength) * " "}{pageRankingStart}. |'
                        itemLength = len(f" {item[0]} |")
                        lengthDescription += f'{(24 - itemLength) * " "}{item[0]} |'
                        quantityLength = len(f" {item[1]} |")
                        lengthDescription += f'{(14 - quantityLength) * " "}{item[1]} |'
                        lengthRecord.append(len(lengthDescription))
                        pageRankingStart += 1

                    description = f'```yaml\nNo. |    Item               | Quantity |\n{max(lengthRecord) * "="}\n'

                    pageRankingStart = 10 * (i - 1) + 1

                    for item in everyPage:
                        rankLength = len(f"{pageRankingStart}. |")
                        description += f'{(5 - rankLength) * " "}{pageRankingStart}. |'
                        itemLength = len(f" {item[0]} |")
                        description += f'{(25 - itemLength) * " "}{item[0]} |'
                        quantityLength = len(f" {item[1]} |")
                        description += f'{(12 - quantityLength) * " "}{item[1]} |\n'
                        pageRankingStart += 1

                    description += '```'

                    embed = discord.Embed(title=f"{ctx.author}'s Inventory",
                                          description=description,
                                          timestamp=datetime.datetime.now(pytz.timezone("Singapore")))
                    embed.set_footer(text=f"{i} of {pages} pages", icon_url=ctx.author.avatar_url)
                    await msg.edit(embed=embed)

                    await msg.edit(embed=embed)

            else:
                return

            reaction, user = await self.bot.wait_for('reaction_add', check=check)
            await handle_rotate(reaction, msg, check, i)

        reaction, user = await self.bot.wait_for('reaction_add', check=check)
        await handle_rotate(reaction, msg, check, i)

    @commands.command(description="shop**\n\nShows the shop and the item available for purchase!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shop(self, ctx):

        try:

            invC.execute(f'SELECT name, description FROM shopsettings WHERE server_id = ?', (ctx.guild.id,))
            result = invC.fetchall()

            title = result[0][0]
            desc = result[0][1]

            invC.execute(f'SELECT item, price, stock, role FROM shop WHERE server_id = {ctx.message.guild.id}')
            items = invC.fetchall()

            pages = math.ceil(len(items) / 4)

            i = 1

            everyPage = [item for item in items[4 * (i - 1):i * 4]]

            embed = discord.Embed(title=f"{title}", description=f"{desc}")
            embed.set_thumbnail(url=f"{ctx.message.guild.icon_url}")
            embed.set_footer(text=f"Page {i} of {pages}", icon_url=ctx.author.avatar_url)

            if not items:
                raise IndexError

            for item in everyPage:
                itemDetails = ""

                if item[2] != 0:
                    itemDetails += f"Stock Available: {item[2]}\n"

                else:
                    itemDetails += "Stock Available: Unlimited\n"

                if item[3] == "none" or item[3] == "skip":
                    pass

                else:
                    itemDetails += f"Acquired Role: {item[3]}\n"

                embed.add_field(name=f"{item[1]} {determineSymbol(ctx.guild.id)} • {item[0]} ", value=f"{itemDetails}",
                                inline=False)

            msg = await ctx.send(embed=embed)
            await msg.add_reaction('⏪')
            await msg.add_reaction('⏩')

            def check(reaction, user):

                return str(reaction.emoji) in ['⏪',
                                               '⏩'] and user == ctx.message.author and reaction.message.id == msg.id

            async def handle_rotate(reaction, msg, check, i):
                await msg.remove_reaction(reaction, ctx.message.author)

                if str(reaction.emoji) == '⏩':

                    i += 1

                    if i > pages:

                        embed = discord.Embed(title=f"{title}", description=f"You have reached the end of the pages!")
                        embed.set_thumbnail(url=f"{ctx.message.guild.icon_url}")
                        embed.set_footer(text=f"Press '⏪' to go back.", icon_url=ctx.author.avatar_url)
                        await msg.edit(embed=embed)

                    else:

                        everyPage = [item for item in items[4 * (i - 1):i * 4]]

                        embed = discord.Embed(title=f"{title}", description=f"{desc}")
                        embed.set_thumbnail(url=f"{ctx.message.guild.icon_url}")
                        embed.set_footer(text=f"Page {i} of {pages}", icon_url=ctx.author.avatar_url)

                        if not items:
                            raise IndexError

                        for item in everyPage:

                            itemDetails = ""

                            if item[2] != 0:

                                itemDetails += f"Stock Available: {item[2]}\n"

                            else:

                                itemDetails += "Stock Available: Unlimited\n"

                            if item[3] == "none" or item[3] == "skip":
                                pass

                            else:
                                itemDetails += f"Acquired Role: {item[3]}\n"

                            embed.add_field(name=f"{item[1]} {determineSymbol(ctx.guild.id)} • {item[0]} ",
                                            value=f"{itemDetails}",
                                            inline=False)

                        await msg.edit(embed=embed)

                elif str(reaction.emoji) == '⏪':

                    i -= 1

                    if i <= 0:

                        embed = discord.Embed(title=f"{title}", description=f"You have reached the end of the pages!")
                        embed.set_thumbnail(url=f"{ctx.message.guild.icon_url}")
                        embed.set_footer(text=f"Press '⏩' to go back.", icon_url=ctx.author.avatar_url)
                        await msg.edit(embed=embed)

                    else:

                        everyPage = [item for item in items[4 * (i - 1):i * 4]]

                        embed = discord.Embed(title=f"{title}", description=f"{desc}")
                        embed.set_thumbnail(url=f"{ctx.message.guild.icon_url}")
                        embed.set_footer(text=f"Page {i} of {pages}", icon_url=ctx.author.avatar_url)

                        if not items:
                            raise IndexError

                        for item in everyPage:

                            itemDetails = ""

                            if item[2] != 0:

                                itemDetails += f"Stock Available: {item[2]}\n"

                            else:

                                itemDetails += "Stock Available: Unlimited\n"

                            if item[3] == "none" or item[3] == "skip":
                                pass

                            else:
                                itemDetails += f"Acquired Role: {item[3]}\n"

                            embed.add_field(name=f"{item[1]} {determineSymbol(ctx.guild.id)} • {item[0]} ",
                                            value=f"{itemDetails}",
                                            inline=False)

                        await msg.edit(embed=embed)

                else:

                    return

                reaction, user = await self.bot.wait_for('reaction_add', check=check)
                await handle_rotate(reaction, msg, check, i)

            reaction, user = await self.bot.wait_for('reaction_add', check=check)
            await handle_rotate(reaction, msg, check, i)


        except IndexError as e:

            await cogs.functions.requestEmbedTemplate(ctx,
                                                      "Sorry, there isn't such a page (or there isn't a shop yet)!\nTell the server owner / admins to add to the shop by using `setshop` or `shopsettings` command.",
                                                      ctx.message.author)
            traceback.print_exc()

        except Exception as e:

            traceback.print_exc()


def setup(bot):
    bot.add_cog(Shop(bot))
