import os
import asyncio
import sqlite3
import discord
import random
from discord.ext import commands
import datetime

TOKEN = os.getenv("TOKEN", None)

if TOKEN is None:
    raise RuntimeError("Environment variable not found")

conn = sqlite3.connect('quotes.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS quotes (quote_id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, quote_text VARCHAR, 
quoted_person VARCHAR, quoted_date, guild_id INTEGER)''')

event_loop = asyncio.get_event_loop()
client = discord.Client(loop=event_loop)

bot = commands.Bot(command_prefix='q!')


def user_from_user_mention(mention):
    result = bot.get_user(int(mention[3:-1]))
    return result


async def message_delete_soon(ctx, message, delay):
    await (await ctx.send(f"{message}")).delete(delay=delay)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name="add", help="Adds a quote to the database, (QUOTE, @USER)")
@commands.has_role('Quoter')
async def add_quote(ctx, *quote_mention_date):
    guild_id = ctx.guild.id
    fused_arguments = ' '.join(quote_mention_date[:-1])
    print(fused_arguments)
    mention = quote_mention_date[-1:][0]
    date = datetime.date.today()
    print(date)
    print(mention[1:3])
    if mention[1:3] == "@!":
        insert = [fused_arguments, mention, date, guild_id]
        c.execute('''INSERT INTO quotes (quote_text, quoted_person, quoted_date, guild_id) VALUES (?,?,?,?)''', insert)
        quote_id = c.execute('''SELECT last_insert_rowid()''')
        quote_id = quote_id.lastrowid
        conn.commit()
        await ctx.send(f"Quote added as ID:`{quote_id}`! Thanks for your contribution {ctx.author.mention}!")
    else:
        message = f'That player is not in the server or invalid entry used'
        await message_delete_soon(ctx, message, 3)


@bot.command(name="getrand", help="Gives you 5 random quotes from: all(anyone), @USER(from user)")
@commands.has_role('Quoter')
async def get_random_quote(ctx, user):
    guild_id = ctx.guild.id
    if user == "all":
        c.execute('''SELECT * from quotes WHERE guild_id=?''', (guild_id,))
        records = c.fetchall()
        messages = []
        if len(records) != 0:
            while len(messages) < 5 and len(records) != 0:
                message = random.choice(records)
                target_user = user_from_user_mention(message[2]).name
                messages.append(f'''**"{message[1]}"**\n    -*{target_user}*, {message[3]} (Quote ID:{message[0]})''')
                records.remove(message)
            messages.append("Here you go!")
            await ctx.send("\n".join(messages))
        else:
            await ctx.send(f"No quotes available yet")
    elif user[1:3] == "@!":
        target_user = user_from_user_mention(user).name
        c.execute(f'''SELECT * FROM quotes WHERE quoted_person=? AND guild_id=?''', (user, guild_id))
        records = c.fetchall()
        if len(records) == 0:
            message = f"`{target_user}` hasn't been quoted yet!"
            await message_delete_soon(ctx, message, 3)
        else:
            messages = []
            while len(messages) < 5 and len(records) != 0:
                message = random.choice(records)
                messages.append(
                    f'''**"{message[1]}"**\n    -*{target_user}*, {message[3]} (Quote ID:{message[0]})''')
                records.remove(message)
            messages.append("Here you go!")
            await ctx.send("\n".join(messages))
    else:
        await ctx.send("Invalid input!")


@bot.command(name="getbyid", help="Gives you the quote linked with selected id, (ID)")
@commands.has_role('Quoter')
async def get_quote_by_id(ctx, quote_id):
    try:
        int(quote_id)
        guild_id = ctx.guild.id
        c.execute(f'''SELECT * FROM quotes WHERE quote_id=? AND guild_id=?''', (quote_id, guild_id))
        record = c.fetchone()
        if record is None:
            message = f"Quote #`{quote_id}` doesn't exist yet!"
            await message_delete_soon(ctx, message, 3)
        else:
            target_user = user_from_user_mention(record[2]).name
            await ctx.send(
                f'''**"{record[1]}"**\n    -*{target_user}*, {record[3]} (Quote ID:{record[0]})\nHere you go!''')
    except ValueError:
        message = f"`{quote_id}` is not a number!"
        await message_delete_soon(ctx, message, 3)


@bot.command(name="amount", help="Tells you how many quotes are available to you here!")
@commands.has_role('Quoter')
async def get_quote_amt(ctx):
    guild_id = ctx.guild.id
    c.execute(f'''SELECT COUNT(*) FROM quotes WHERE guild_id=?''', (guild_id,))
    record = c.fetchone()
    if record[0] == 0:
        message = f"There are no quotes from this server in the database..."
        await message_delete_soon(ctx, message, 3)
    else:
        await ctx.send(f"This server currently has `{record[0]}` quote(s)!")


@bot.command(name="getbykeywords", help="Gives you the quote similar to your keyword(s), (KEYWORDS)")
@commands.has_role('Quoter')
async def get_quote_by_keyword(ctx, *keywords):
    guild_id = ctx.guild.id
    fused_arguments = ' '.join(keywords)
    print(fused_arguments)
    c.execute("""SELECT * FROM quotes WHERE quote_text LIKE ? AND guild_id=?""",
              ("%" + fused_arguments + "%", guild_id))
    records = c.fetchone()
    if records is None:
        print(records)
        message = f"Couldn't find a quote with `{fused_arguments}`!"
        await message_delete_soon(ctx, message, 3)
    else:
        target_user = user_from_user_mention(records[2]).name
        await ctx.send(
            f'''**"{records[1]}"**\n    -*{target_user}*, {records[3]} (Quote ID:{records[0]})\nHere you go!''')


@bot.command(name="delete", help="Allows user to delete a quote using it's ID, (ID|all)")
@commands.has_guild_permissions(administrator=True)
async def delete(ctx, choice):
    guild_id = ctx.guild.id
    try:
        int(choice)
        c.execute(f'''SELECT COUNT(*) FROM quotes WHERE guild_id=? AND quote_id=?''', (guild_id, choice))
        record = c.fetchone()
        if record[0] == 1:
            c.execute("""DELETE FROM quotes WHERE quote_id=? AND guild_id=?""", (choice, guild_id))
            conn.commit()
            message = f"Quote #`{choice}` deleted successfully!"
            await message_delete_soon(ctx, message, 3)
        else:
            message = f"Could not delete quote #`{choice}`"
            await message_delete_soon(ctx, message, 3)
    except ValueError:
        if choice == "all":
            c.execute(f'''SELECT COUNT(*) FROM quotes WHERE guild_id=?''', (guild_id,))
            record = c.fetchone()
            if record[0] > 0:
                c.execute("""DELETE FROM quotes WHERE guild_id=?""", (guild_id,))
                conn.commit()
                message = f"Deleted `{record[0]}` quote(s)"
                await message_delete_soon(ctx, message, 3)
            else:
                message = f"There are no quotes to delete"
                await message_delete_soon(ctx, message, 3)
        else:
            message = f"`{choice}` is not a number!"
            await message_delete_soon(ctx, message, 3)


@bot.command(name='report', help='Report an error to the dev, (MESSAGE)')
@commands.has_guild_permissions(administrator=True)
async def report(ctx, *message):
    message = ' '.join(message)
    creator = bot.get_user(226465836267732992)
    await creator.create_dm()
    await creator.dm_channel.send(f"`{ctx.author}` is having issues with Quote Bot on Guild:`{ctx.guild.name}` "
                                  f"Error message:\n`{message}`")
    await ctx.send(f"Report sent successfully! If you receive a DM from {creator.name}, it is my developer")


@bot.event
async def on_command_error(ctx, error):
    if error.args[0] == 'This command cannot be used in private messages.':
        message = f"Sorry, I only work in servers!"
        await message_delete_soon(ctx, message, 3)
    else:
        await ctx.send(f"There seems to have been a problem!\n`{error}`\nIf you believe this is a mistake, "
                       f"please use !report to report it!")


@bot.command(name="test", description="Lets you figure out if the bot is online")
async def test(ctx):
    await ctx.send(f"The bot is indeed online, {str(ctx.author)[:-5]}")


bot.run(TOKEN)
