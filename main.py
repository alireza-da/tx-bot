import functools
import typing
import json
import discord
import discord_slash
import datetime
import dateutil.parser
import jdatetime


from discord.ext import commands
from credentials import bot_token, tx_guild_id, staff_update_channel_id, request_list_id
from discord.ext import commands
from discord.utils import get
from discord_slash import SlashCommand, SlashContext
from setup_db import setup_tables, get_all_mechanics, get_user, update_mc
from model import TxEmployee


intents = discord.Intents.all()
intents.members = True
client = commands.Bot(command_prefix='$', intents=intents, help_command=None)
slash = SlashCommand(client, sync_commands=True)

dt_format = "%a, %d %b %Y %H:%M:%S"

with open('tx_data.json', "r") as f:
    tx_data = json.load(f)
    tx_data = dict(tx_data)


async def non_blocking_data_insertion(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    func = functools.partial(blocking_func, *args, **kwargs)
    return await client.loop.run_in_executor(None, func)


@client.event
async def on_ready():
    print(f"Ready to work. Client ID: {client.user.id}")
    emps = find_tx(client.guilds[0])
    tx_guild = client.guilds[0]
    await non_blocking_data_insertion(setup_tables, emps)
    staff_update_channel = tx_guild.get_channel(staff_update_channel_id)
    staff_msgs = await staff_update_channel.history(limit=4000).flatten()
    txs = get_all_mechanics()

    for tx in txs:
        tx_data[str(tx.discord_id)] = {"last_rank_up": "", "finish_reqs": 0}
        for msg in staff_msgs:
            if msg.mentions and tx.discord_id == msg.mentions[0].id and (
                    ":Rankup:" in msg.content or ":DemoteRank:" in msg.content or "Welcome! <:green:942504144013492314>" in msg.content):
                tx_data[str(tx.discord_id)]["last_rank_up"] = str(msg.created_at)

        date = tx_data[str(tx.discord_id)]["last_rank_up"]
        if date != "":
            rqs_list = tx_guild.get_channel(request_list_id)
            rqs_list_msg = await rqs_list.history(limit=10000).flatten()
            index = 0
            date = dateutil.parser.parse(date)
            size = len(rqs_list_msg)
            finish_reqs = 0
            name = tx.ic_name
            if "}" in tx.ic_name:
                name = tx.ic_name.split("} ")[1]
            while rqs_list_msg[index].created_at > date:
                if name in rqs_list_msg[index].content and "[Finish request]" in rqs_list_msg[index].content:
                    finish_reqs += 1
                index += 1
                if index > size - 1:
                    break
            tx_data[str(tx.discord_id)]["finish_reqs"] = finish_reqs
            tx.points += finish_reqs - tx.points
            update_mc(tx)
    with open('tx_data.json', "w") as fs:
        json.dump(tx_data, fs)


@client.event
async def on_message(message: discord.Message):
    if message.author != client:

        if message.channel.id == request_list_id and "[Finish request]" in message.content:
            name = message.content.split("Finish by : ")[1].split(" ")
            name = f"{name[0]} {name[1]}"
            print(name)
            tx = find_member_by_nick(message.guild.members, name)
            tx = get_user(tx.id)
            tx.points += 1
            update_mc(tx)
            tx_data[str(tx.discord_id)]["finish_reqs"] = tx_data[str(tx.discord_id)]["finish_reqs"]+1
            with open('tx_data.json', "w") as fs:
                json.dump(tx_data, fs)
        elif message.channel.id == staff_update_channel_id and ":Rankup:" in message.content or ":DemoteRank:" in message.content or "Welcome! <:green:942504144013492314>" in message.content:
            tx = get_user(message.mentions[0].id)
            tx_data[str(tx.discord_id)]["last_rank_up"] = str(message.created_at)
            with open('tx_data.json', "w") as fs:
                json.dump(tx_data, fs)


def find_member_by_nick(members: list[discord.Member], nick: str):
    for member in members:
        if (member.nick and nick in member.nick) or (member.display_name and nick in member.display_name):
            return member


def find_tx(guild: discord.Guild):
    res = []
    for member in guild.members:
        role_ids = [r.id for r in member.roles]
        if 884815982110060635 in role_ids or role_ids.__contains__(884815982110060635):
            ic_roster = get_ic_name_roster(member)
            tx = TxEmployee(ic_roster[0], ic_roster[1], member.id, "")
            res.append(tx)
    return res


def get_ic_name_roster(member: discord.member):
    if member.nick:
        name = member.nick.split("] ")[1]
        roster = member.nick.split("[")[1].split("]")[0]
        return name, roster


@slash.slash(name="FRPoints",
             description="Check Employee's Finished Requests and Points",
             guild_ids=[tx_guild_id],
             )
async def fr_points(ctx: SlashContext, employee):
    if ctx:
        _id = None
        if "!" in employee:
            _id = int(employee.split("!")[1].replace(">", ""))
        else:
            _id = int(employee.split("@")[1].replace(">", ""))
        if _id:
            tx = get_user(_id)
            embedVar = discord.Embed(title=f"{tx.ic_name}'s Finished Requests Report",
                                     description=f":abc: IC Name: {tx.ic_name}\n:1234: Points: {tx.points}\n:taxi: "
                                                 f"Finishe"
                                                 f"d Requests: {tx_data[str(tx.discord_id)]['finish_reqs']}\n:date: "
                                                 f"Since: {tx_data[str(tx.discord_id)]['last_rank_up']}")
            await ctx.channel.send(embed=embedVar)


@slash.slash(name="ClearFRPoints",
             description="Clear Employee's Points",
             guild_ids=[tx_guild_id],
             )
async def clear_points(ctx: SlashContext, employee):
    if ctx:
        _id = None
        if "!" in employee:
            _id = int(employee.split("!")[1].replace(">", ""))
        else:
            _id = int(employee.split("@")[1].replace(">", ""))
        if _id:
            tx = get_user(_id)
            tx.points = 0
            update_mc(tx)
            embedVar = discord.Embed(title=f"Clear Points Report",
                                     description=f"Cleared {tx.ic_name} points.", color=discord.Color("#FFFF00"))
            await ctx.channel.send(embed=embedVar)


@slash.slash(name="AddFRPoints",
             description="Add points to an employee",
             guild_ids=[tx_guild_id],
             )
async def add_points(ctx: SlashContext, employee, points):
    if ctx:
        _id = None
        if "!" in employee:
            _id = int(employee.split("!")[1].replace(">", ""))
        else:
            _id = int(employee.split("@")[1].replace(">", ""))
        if _id:
            tx = get_user(_id)
            tx.points += int(points)
            update_mc(tx)
            embedVar = discord.Embed(title=f"Add Points Report",
                                     description=f"Added {str(points)} points to {tx.ic_name}.", color=discord.Color("#FFFF00"))
            await ctx.channel.send(embed=embedVar)


@slash.slash(name="RemoveFRPoints",
             description="Add points to an employee",
             guild_ids=[tx_guild_id],
             )
async def remove_points(ctx: SlashContext, employee, points):
    if ctx:
        _id = None
        if "!" in employee:
            _id = int(employee.split("!")[1].replace(">", ""))
        else:
            _id = int(employee.split("@")[1].replace(">", ""))
        if _id:
            tx = get_user(_id)
            tx.points -= int(points)
            update_mc(tx)
            embedVar = discord.Embed(title=f"Remove Points Report",
                                     description=f"Remove {str(points)} points from {tx.ic_name}.", color=discord.Color("#FFFF00"))
            await ctx.channel.send(embed=embedVar)


client.run(bot_token)
