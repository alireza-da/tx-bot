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
from setup_db import setup_tables, get_all_mechanics, get_user, update_mc, add_mcs_to_db
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
    tx_guild = client.guilds[0]
    # emps = find_tx(tx_guild)
    # await non_blocking_data_insertion(setup_tables, emps)
    staff_update_channel = tx_guild.get_channel(staff_update_channel_id)
    staff_msgs = await staff_update_channel.history(limit=10000).flatten()
    txs = get_all_mechanics()
    rqs_list = tx_guild.get_channel(request_list_id)
    rqs_list_msg = await rqs_list.history(limit=10000).flatten()
    for tx in txs:
        tx_data[str(tx.discord_id)] = {"last_rank_up": "N/A", "finish_reqs": 0}
        for msg in staff_msgs:
            if msg.mentions and tx.discord_id == msg.mentions[0].id and (
                    ":PromoteRank:" in msg.content or ":DemoteRank:" in msg.content or "Welcome! <:Accepted:942504144013492314>" in msg.content):
                tx_data[str(tx.discord_id)]["last_rank_up"] = str(msg.created_at)

        date = tx_data[str(tx.discord_id)]["last_rank_up"]
        if date != "":

            index = 0
            date = dateutil.parser.parse(date)
            size = len(rqs_list_msg)
            finish_reqs = 0
            name = tx.ic_name
            if "}" in tx.ic_name:
                name = tx.ic_name.split("} ")[1]
            print(name)
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
            tx_data[str(tx.discord_id)]["finish_reqs"] = tx_data[str(tx.discord_id)]["finish_reqs"] + 1
            with open('tx_data.json', "w") as fs:
                json.dump(tx_data, fs)
        elif message.channel.id == staff_update_channel_id and ":PromoteRank:" in message.content or ":DemoteRank:" in message.content or "Welcome! <:green:942504144013492314>" in message.content:
            tx = get_user(message.mentions[0].id)
            tx.points = 0
            update_mc(tx)
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
            roster = get_ic_name_roster(ctx.guild.get_member(_id))[1]
            member = get(ctx.guild.members, id=_id)
            embedVar = discord.Embed(title=f"{member.nick}'s Finished Requests Report",
                                     description=f":abc: IC Name: {tx.ic_name}\n"
                                                 f":taxi: Taxi Code: {roster}\n:1234: Points: {tx.points}\n:white_check_mark: "
                                                 f"Finishe"
                                                 f"d Requests: {tx_data[str(tx.discord_id)]['finish_reqs']}\n:date: "
                                                 f"Since: {tx_data[str(tx.discord_id)]['last_rank_up'].split('.')[0]}")
            await ctx.send(embed=embedVar)


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
            prev_txp = tx.points
            tx.points = 0
            update_mc(tx)
            member = get(ctx.guild.members, id=_id)
            embedVar = discord.Embed(title=f"Clear Points Report",
                                     description=f"Cleared {member.mention} points.\nPrevious Points: {prev_txp}")
            await ctx.send(embed=embedVar)


@slash.slash(name="AddFRPoints",
             description="Add points to an employee",
             guild_ids=[tx_guild_id],
             )
async def add_points(ctx: SlashContext, employee, points):
    if ctx:
        await ctx.send(":hourglass: In Progress ...")
        _id = None
        if "!" in employee:
            _id = int(employee.split("!")[1].replace(">", ""))
        else:
            _id = int(employee.split("@")[1].replace(">", ""))
        if _id:
            tx = get_user(_id)
            prev_txp = tx.points
            tx.points += int(points)
            update_mc(tx)
            member = get(ctx.guild.members, id=_id)
            embedVar = discord.Embed(title=f"Add Points Report",
                                     description=f"Added {str(points)} points to {member.mention}.\nCurrent Points: {tx.points}.\nPrevious Points: {prev_txp}")
            await ctx.send(embed=embedVar)


@slash.slash(name="RemoveFRPoints",
             description="Remove points from an employee",
             guild_ids=[tx_guild_id],
             )
async def remove_points(ctx: SlashContext, employee, points):
    if ctx:
        await ctx.send(":hourglass: In Progress ...")
        _id = None
        if "!" in employee:
            _id = int(employee.split("!")[1].replace(">", ""))
        else:
            _id = int(employee.split("@")[1].replace(">", ""))
        if _id:
            tx = get_user(_id)
            prev_txp = tx.points
            tx.points -= int(points)
            update_mc(tx)
            member = get(ctx.guild.members, id=_id)
            embedVar = discord.Embed(title=f"Remove Points Report",
                                     description=f"Removed {str(points)} points from {member.mention}.\nPrevious "
                                                 f"Points: {prev_txp}.\nCurrent Points: {tx.points}")
            await ctx.send(embed=embedVar)


@slash.slash(name="FRA",
             description="Job Abuse Detector",
             guild_ids=[tx_guild_id],
             )
async def fra(ctx: SlashContext, user):
    if ctx:
        req_list_channel = ctx.guild.get_channel(request_list_id)
        await ctx.send(":hourglass: In Progress ...")
        hist = await req_list_channel.history(limit=10000).flatten()
        res = {}
        reqs_pair = []
        fid = 0
        fname = ""
        nid = 0
        for msg in hist:
            if "[Finish request]" in msg.content:
                lines = msg.content.split("\n")
                fid = lines[-1].split(" ")[-1]
                fname_list = lines[2].split(" ")
                fname = f"{fname_list[4]} {fname_list[5]}"
                reqs_pair.append(fid)
                print(fid)
            elif "[New request]" in msg.content:
                lines = msg.content.split("\n")
                nid = lines[-1].split(" ")[-1]
                print(nid)
                if nid in reqs_pair:
                    name = lines[-1].split(" ")[-1]
                    if name == user:
                        try:
                            res[fname] += 1
                        except KeyError as e:
                            res[fname] = 1
                    reqs_pair.remove(nid)
        embedVar = discord.Embed(title="FRA Report")
        for key in res.keys():
            if res[key] < 3:
                del res[key]
            else:
                embedVar.add_field(name=f"{key}", value=f"Finished Requests: {res[key]}")
        await ctx.channel.send(embed=embedVar)


@slash.slash(name="set-job",
             description="Set Job",
             guild_ids=[tx_guild_id],
             )
async def set_job(ctx: SlashContext, employee, rank, taxi_code, ic_name, license):
    if ctx:
        _id = None
        if "!" in employee:
            _id = int(employee.split("!")[1].replace(">", ""))
        else:
            _id = int(employee.split("@")[1].replace(">", ""))
        if _id and int(rank) < 5:
            member = get(ctx.guild.members, id=_id)
            roles = get_ranks_roles_by_id(ctx.guild)
            await member.add_roles(roles[884815982110060635])
            await member.add_roles(roles[884815998249758830])
            await member.edit(nick=f"[{taxi_code}] {ic_name}")
            embedVar = discord.Embed(title=f"Set Job Report", description=f"Successfully Signed {member.mention}")
            await ctx.send(embed=embedVar)
            staff_channel = ctx.guild.get_channel(staff_update_channel_id)
            await staff_channel.send(f"**Additional Staff update [{jdatetime.datetime.now().strftime(dt_format)}]** 📌\n" 
                                    f"{member.mention} Has Been joined To SSTX and Will Be Known as [{taxi_code}], "
                                     f"Welcome!\n "
                                     f"Author: {ctx.author.mention}")
            if license.lower() == "no":
                await member.add_roles(roles[920018697924522074])
            tx = TxEmployee(ic_name, taxi_code, member.id, "")
            add_mcs_to_db([tx])
            tx_data[str(tx.discord_id)]["last_rank_up"] = str(jdatetime.datetime.now())
            tx_data[str(tx.discord_id)]["finish_reqs"] = 0
            with open('tx_data.json', "w") as fs:
                json.dump(tx_data, fs)


def get_ranks_roles_by_id(guild: discord.Guild):
    res = {}
    for role in guild.roles:
        res[role.id] = role
    return res


client.run(bot_token)
