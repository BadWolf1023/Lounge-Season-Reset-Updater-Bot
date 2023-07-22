'''
Created on Aug 5, 2021

@author: willg
'''
import discord
from discord.ext import commands, tasks
import website_api_loader
import Player
import common
from ExtraChecks import owner_or_staff, lounge_only_check, badwolf_command_check
import CustomExceptions
from datetime import datetime, timedelta
import queue
import asyncio
from collections import defaultdict
import traceback

invite_link = "https://discord.com/api/oauth2/authorize?client_id=872936275320139786&permissions=268470272&scope=bot"
lounge_server_id = 387347467332485122


finished_on_ready = False
HOURS_TO_ADD_TO_MAKE_EST = 3


def load_private_data():
    global bot_key
    with open("private.txt") as f:
        all_lines = f.readlines()
        bot_key = all_lines[0]
        
load_private_data()


async def safe_send(channel, message_text):
    try:
        await channel.send(message_text)
    except:
        print(f"Failed to send message: {message_text}")

class MessageSender(object):
    TIME_BETWEEN_MESSAGES = 10
    MAXIMUM_MESSAGE_LENGTH = 1999
    TIME_BETWEEN_TEMPROLE_NOTIFICATIONS = timedelta(minutes=60) #60 minutes
    TIME_BETWEEN_24_HR_NOTIFICATIONS = timedelta(hours=24)
    
    
    def __init__(self, running_channel):
        self.running_channel = running_channel
        self.message_queue = queue.SimpleQueue()
        self.last_message_sent = datetime.now()
        self.copying = False
        self.temp_role_message_history = {}

                
    async def send_message(self, message_text, is_temp_role_message=False, is_once_every_24_hr_message=False, alternative_ctx=None):
        if alternative_ctx is not None:
            await alternative_ctx.send(message_text)
            return 
        
        if not is_temp_role_message and not is_once_every_24_hr_message:
            self.message_queue.put(message_text + "\n")
        else:
            current_time = datetime.now()
            try:
                last_sent = self.temp_role_message_history[message_text]
            except KeyError: #the temprole message isn't in the history, so add it
                self.message_queue.put(message_text + "\n")
                self.temp_role_message_history[message_text] = current_time
            else:
                #The message was in the history
                #If we've exceeded 20 minutes from the last time we sent a temprole message, add it to the queue and update the time
                if is_temp_role_message:
                    if (current_time - last_sent) > MessageSender.TIME_BETWEEN_TEMPROLE_NOTIFICATIONS:
                        self.message_queue.put(message_text + "\n")
                        self.temp_role_message_history[message_text] = current_time
                if is_once_every_24_hr_message:
                    if (current_time - last_sent) > MessageSender.TIME_BETWEEN_24_HR_NOTIFICATIONS:
                        self.message_queue.put(message_text + "\n")
                        self.temp_role_message_history[message_text] = current_time



def determine_role_name(player_rating, cutoff_data):
    if player_rating is not None:
        for cutoff in cutoff_data:
            if cutoff[0] is None or player_rating >= cutoff[0]:
                return cutoff[1]
    return "No Class (didn't fall into any of the cutoff ranges)"

async def pull_data(message_sender, verbose=True, alternative_ctx=None):
    await website_api_loader.PlayerDataLoader.update_player_data(message_sender, verbose, alternative_ctx)
    await website_api_loader.CutoffDataLoader.update_cutoff_data(message_sender, verbose, alternative_ctx)

async def send_file_with_players_in_each_class(ctx, is_rt, last_x_days=None):
    current_est_time = datetime.now() + timedelta(hours=HOURS_TO_ADD_TO_MAKE_EST)
    need_to_have_played_after_date = None if last_x_days is None else (current_est_time - timedelta(days=last_x_days))
    get_mmr_and_date = None
    if is_rt:
        get_mmr_and_date = lambda x: (x.rt_mmr, x.rt_last_event)
    else:
        get_mmr_and_date = lambda y: (y.ct_mmr, y.ct_last_event)
    
    cutoffs = common.RT_CLASS_ROLE_CUTOFFS if is_rt else common.CT_CLASS_ROLE_CUTOFFS
    if len(common.test_cutoffs) > 0:
        cutoffs = common.test_cutoffs
        
    activity_reqs = {}
    for cutoff_data in reversed(cutoffs):
        activity_reqs[cutoff_data[1]] = [[], []] #active players, total players
    
    for player_data in common.all_player_data.values():
        mmr, last_event_date = get_mmr_and_date(player_data)
        if mmr is None: #They haven't ever played this track type (RT or CT), so don't count them - skip
            continue
        
        class_name_for_player = determine_role_name(mmr, cutoffs)
        activity_reqs[class_name_for_player][1].append(player_data.name)
        if need_to_have_played_after_date is None or last_event_date >= need_to_have_played_after_date:
            activity_reqs[class_name_for_player][0].append(player_data.name)
               
            
    to_send = f"Active players in each {'RT' if is_rt else 'CT'} class during the last {last_x_days} days.\nNote: Active is defined as players who have played at least 1 event in the past {last_x_days} days, as you specified.\nNote: Total players is the total players in the class, regardless of whether they have played an event this season."
    if need_to_have_played_after_date is None:
        to_send = f"Players in each {'RT' if is_rt else 'CT'} class.\nNote: All players are included, regardless of whether they have played an event this season."
    
    if need_to_have_played_after_date is not None:
        to_send += f"\n"
        for cutoff_name, (active_player_list, all_player_list) in reversed(activity_reqs.items()):
            percentage_active = 0.0
            if len(all_player_list) > 0:
                percentage_active = len(active_player_list) / len(all_player_list)
            percentage_active = int(round(100 * percentage_active, 0))
            
            to_send += f"\n{cutoff_name}"
            if need_to_have_played_after_date is not None:
                to_send += f": {len(active_player_list)} active players out of the {len(all_player_list)} players who are in this class ({percentage_active}%)"
    
    for cutoff_name, (active_player_list, all_player_list) in reversed(activity_reqs.items()):
        active_player_list.sort(key=lambda x:x.lower())
        to_send += f"\n\n\n{cutoff_name}\n"
        to_send += "\n".join(active_player_list)
    
    await common.safe_send_file(ctx, to_send)
    
async def send_active_players(ctx, is_rt, last_x_days):
    current_est_time = datetime.now() + timedelta(hours=HOURS_TO_ADD_TO_MAKE_EST)
    need_to_have_played_after_date = current_est_time - timedelta(days=last_x_days)
    get_mmr_and_date = None
    if is_rt:
        get_mmr_and_date = lambda x: (x.rt_mmr, x.rt_last_event)
    else:
        get_mmr_and_date = lambda y: (y.ct_mmr, y.ct_last_event)
    
    cutoffs = common.RT_CLASS_ROLE_CUTOFFS if is_rt else common.CT_CLASS_ROLE_CUTOFFS
    if len(common.test_cutoffs) > 0:
        cutoffs = common.test_cutoffs
    activity_reqs = {}
    for cutoff_data in reversed(cutoffs):
        activity_reqs[cutoff_data[1]] = [0, 0] #active players, total players
    
    for player_data in common.all_player_data.values():
        mmr, last_event_date = get_mmr_and_date(player_data)
        if mmr is None: #They haven't ever played this track type (RT or CT), so don't count them - skip
            continue
        if last_event_date == datetime.min: #They haven't played an event this season
            continue
        
        class_name_for_player = determine_role_name(mmr, cutoffs)
        activity_reqs[class_name_for_player][1] += 1
        if last_event_date >= need_to_have_played_after_date:
            activity_reqs[class_name_for_player][0] += 1
    to_send = f"Number of active players in each {'RT' if is_rt else 'CT'} class during the last **{last_x_days} days**.\n**Note:** The total number of players is the number of players in the Class who have played 1 event or more this season.\n**Note:** The number of active players are the players that have played at least 1 event in the past **{last_x_days} days**, as you specified."
    for cutoff_name, (active_players, total_players) in reversed(activity_reqs.items()):
        percentage_active = 0.0
        if total_players > 0:
            percentage_active = active_players / total_players
        percentage_active = int(round(100 * percentage_active, 0))
        
        
        to_send += f"\n{cutoff_name}: {active_players} active players out of {total_players} total players ({percentage_active}%)"
    
    await ctx.reply(to_send)
        



bot = commands.Bot(owner_id=common.BAD_WOLF_ID, allowed_mentions=discord.mentions.AllowedMentions.none(), command_prefix=('!'), case_insensitive=True, intents=discord.Intents.all())

@bot.event
async def on_ready():
    global finished_on_ready
    if not finished_on_ready:
        bot.add_cog(RoleUpdater(bot))
    finished_on_ready = True
        
@bot.event
async def on_command_error(ctx, error):
    if ctx.author.bot:
        return
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        try:
            await(await ctx.send("Your command is missing an argument: `%s`" %
                       str(error.param))).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, commands.CommandOnCooldown):
        try:
            await(await ctx.send("This command is on cooldown; try again in %.0fs"
                       % error.retry_after)).delete(delay=5)
        except discord.Forbidden:
            pass

        return
    
    if isinstance(error, commands.MissingAnyRole):
        try:
            await(await ctx.send(f"You need to have one of the following roles to use this command: `{', '.join(error.missing_roles)}`",
                             )
            
              ).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, commands.BadArgument):
        try:
            await(await ctx.send("BadArgument Error: `%s`" % error.args)).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    
    if isinstance(error, commands.BotMissingPermissions):
        try:
            await(await ctx.send("I need the following permissions to use this command: %s"
                       % ", ".join(error.missing_perms))).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    if isinstance(error, commands.NoPrivateMessage):
        return
    if isinstance(error, commands.MissingPermissions):
        try:
            await(await ctx.send("You need the following permissions to use this command: %s"
                       % ", ".join(error.missing_perms))).delete(delay=10)
        except discord.Forbidden:
            pass
        return
    
    if isinstance(error, CustomExceptions.NotLounge):
        return
    
    if isinstance(error, CustomExceptions.BadAPIData):
        return
    
    
    
    if 'original' in error.__dict__:
        if isinstance(error.original, discord.Forbidden):
            #This should only run if bot can't send messages
            return
    
    try:
        await ctx.send("An unknown error happened. Contact Bad Wolf #1023 on Discord if this keeps happening.")
    except discord.Forbidden:
        pass

    raise error

         
        

class RoleUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def activeplayers(self, ctx: commands.Context, rt_or_ct: str, number_of_days: int):
        """This command shows the number of active players in each class. You can specify the number of activity time limit. If you're unsure, 5 days is a good activity time limit."""
        
        if number_of_days < 1 or number_of_days > 365:
            await ctx.send(f'"{number_of_days}" is not a valid option. Valid options are between 1 days and 365 days.')
            return
        is_rt = None
        if rt_or_ct.lower() == "rt":
            is_rt = True
        elif rt_or_ct.lower() == "ct":
            is_rt = False
        else:
            await ctx.send(f'"{rt_or_ct}" is not a valid option. Valid options are: RT or CT')
            return

        to_delete = await ctx.send("Pulling player data...")
        try:
            await pull_data(self.message_sender, False, ctx) #pulls player data, and if no test cutoff data, pulls that too
        finally:
            await to_delete.delete()
            
        await send_active_players(ctx, is_rt, number_of_days)
        
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def inclass(self, ctx: commands.Context, rt_or_ct: str, number_of_days: int=None):
        """This command sends a list of players in each class. You can also specify an activity criteria.
        
        IMPORTANT NOTE: If you do not specify an activity requirement, all players are included, regardless of whether they have played an event this season. If you did specify an activity requirement, the total number of players statistic is the total number of players in that class, regardless of whether they played an event this season or not. If you're only interested in the activity among people who have played at least 1 event this season, you should check out !activeplayers
        
        Examples:
        - To send a list of players in each RT class: !inclass rt
        - To send a list of players in each CT class who have been active in the past 5 days: !inclass ct 5"""
        if number_of_days is not None:
            if number_of_days < 1 or number_of_days > 365:
                await ctx.send(f'"{number_of_days}" is not a valid option. Valid options are between 1 days and 365 days. If you don\'t want to filter by activity, don\'t specify a number of days.')
                return
        is_rt = None
        if rt_or_ct.lower() == "rt":
            is_rt = True
        elif rt_or_ct.lower() == "ct":
            is_rt = False
        else:
            await ctx.send(f'"{rt_or_ct}" is not a valid option. Valid options are: RT or CT')
            return
        

        to_delete = await ctx.send("Pulling player data...")
        try:
            await pull_data(self.message_sender, False, ctx) #pulls player data, and if no test cutoff data, pulls that too
        finally:
            await to_delete.delete()
            
        await send_file_with_players_in_each_class(ctx, is_rt, number_of_days)
    
    
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def testcutoffs(self, ctx: commands.Context):
        """This command sets test cutoffs, which can then be used by the !activeplayers, !hypotheticalroles, and !inclass commands to see the effect a proposed cutoff may have.
        
        The syntax of the command is !testcutoffs ClassName, LowerCutoff, ClassName, LowerCutoff, ...
        If you want your lower cutoff to be Negative Infinity, do -Infinity
        
        For example, !testcutoffs Class F, -Infinity, Class E, 1500, Class D, 4000, Class C, 8000"""
        
        testcutoff_error_message = """The syntax of the command is `!testcutoffs ClassName, LowerCutoff, ClassName, LowerCutoff, ...`
If you want your lower cutoff to be Negative Infinity, do -Infinity
        
For example, `!testcutoffs Class F, -Infinity, Class E, 1500, Class D, 4000, Class C, 8000`"""
        
        args = ctx.message.content.split(",")
        args[0] = args[0][len("!testcutoffs"):]
        LOWEST_CUTOFF = -99999999
        if len(args) < 2:
            await ctx.send(testcutoff_error_message)
            return
        
        allowed_negative_infinity_terms = ["-infinity", "negativeinfinity"]
        
        new_cutoffs = []
        cur_class_data = []
        for ind, item in enumerate(args):
            if ind % 2 == 0: #It's a Class name, new class
                cur_class_data = []
                cur_class_data.append(item.strip())
            else:
                lower_cutoff = None
                temp = item.lower().replace(" ", "")
                if common.isint(temp):
                    lower_cutoff = int(temp)
                    if lower_cutoff < LOWEST_CUTOFF:
                        await ctx.send(f'"{lower_cutoff}" is below the minimum number allowed: {LOWEST_CUTOFF}\n\nIf you want to do negative infinity, do "-infinity" for your cutoff number.')
                        return
                elif temp in allowed_negative_infinity_terms:
                    lower_cutoff = None
                else:
                    await ctx.send(f'"{item}" is not a valid number for the lower cutoff for class named {cur_class_data[0]}\n\n{testcutoff_error_message}')
                    return
                
                cur_class_data.insert(0, lower_cutoff)
                cur_class_data.append(0)
                new_cutoffs.append((cur_class_data[0], cur_class_data[1], cur_class_data[2]))
        
        new_cutoffs.sort(key=lambda cutoff_data: LOWEST_CUTOFF if cutoff_data[0] is None else cutoff_data[0], reverse=True)
        common.test_cutoffs.clear()
        common.test_cutoffs.extend(new_cutoffs)
        await ctx.send("Test cutoffs:\n" + common.cutoff_display_text(common.test_cutoffs) + "\n\nYou can now use `!activeplayers` or `!hypotheticalroles` or `!inclass` to see how the proposed cutoffs will change things.")
        
            
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def settiers(self, ctx:commands.Context):
        """This command sets which tiers a Class can see, which can then be used by the !activeplayers, !hypotheticalroles, and !inclass commands to see the effect a proposed cutoff may have.
        
        The syntax of the command is !testcutoffs ClassName, LowerCutoff, ClassName, LowerCutoff, ...
        If you want your lower cutoff to be Negative Infinity, do -Infinity
        
        For example, !testcutoffs Class F, -Infinity, Class E, 1500, Class D, 4000, Class C, 8000"""
        common.RT_CLASS_ROLE_CUTOFFS
        common.CT_CLASS_ROLE_CUTOFFS
        "https://www.mkwlounge.gg/api/ladderevent.php?all&ladder_type=rt"
        "https://www.mkwlounge.gg/api/ladderevent.php?all&ladder_type=ct" #Gets events dates and tiers



bot.run(bot_key)
    