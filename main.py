'''
Created on Aug 5, 2021

@author: willg
'''
import discord
from discord.ext import commands, tasks
import google_sheet_loader
import website_api_loader
import Player
import common
from ExtraChecks import owner_or_staff, lounge_only_check, badwolf_command_check
import CustomExceptions
from datetime import datetime, timedelta
import queue
import asyncio
invite_link = "https://discord.com/api/oauth2/authorize?client_id=872936275320139786&permissions=268470272&scope=bot"
lounge_server_id = 387347467332485122
running_channel_id = 879957305007943710


finished_on_ready = False
USING_SHEET = False
USING_WEBSITE_FOR_CUTOFFS = True
LOOP_TIME = 300
HOURS_TO_ADD_TO_MAKE_EST = 3


def load_private_data():
    global master_sheet_url
    global bot_key
    
    with open("private.txt") as f:
        all_lines = f.readlines()
        google_sheet_loader.master_sheet_url = all_lines[0]
        bot_key = all_lines[1]
        
load_private_data()


async def safe_send(channel, message_text):
    try:
        await channel.send(message_text)
    except:
        print(f"Failed to send message: {message_text}")

class MessageSender(object):
    TIME_BETWEEN_MESSAGES = 10
    MAXIMUM_MESSAGE_LENGTH = 1999
    TIME_BETWEEN_TEMPROLE_NOTIFICATIONS = timedelta(minutes=20) #20 minutes
    
    def __init__(self, running_channel):
        self.running_channel = running_channel
        self.message_queue = queue.SimpleQueue()
        self.last_message_sent = datetime.now()
        self.copying = False
        self.temp_role_message_history = {}
        
    def __temp_role_history_check__(self):
        to_delete = set()
        current_time = datetime.now()
        for message, time_sent in self.temp_role_message_history.values():
            if (current_time - time_sent) > MessageSender.TIME_BETWEEN_TEMPROLE_NOTIFICATIONS:
                to_delete.add(message)
                
        for message_to_delete in to_delete:
            try:
                del self.temp_role_message_history[message_to_delete]
            except Exception as e:
                print(f"{datetime.now()}: {str(e)}")
                self.message_queue.put("Let Bad Wolf know there was an error and to check the bot.\n")
                pass
                
    async def queue_message(self, message_text, is_temp_role_message=False, alternative_ctx=None):
        if alternative_ctx is not None:
            await alternative_ctx.send(message_text)
            return 
        
        if not is_temp_role_message:
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
                if (current_time - last_sent) > MessageSender.TIME_BETWEEN_TEMPROLE_NOTIFICATIONS:
                    self.message_queue.put(message_text + "\n")
                    self.temp_role_message_history[message_text] = current_time

    
    @tasks.loop(hours=24)
    async def history_checker_clearing(self):
        self.__temp_role_history_check__()
                    
        
        
    @tasks.loop(seconds=TIME_BETWEEN_MESSAGES)
    async def send_queued_messages(self):
        await self.__background_sender__()
        
        
    async def __background_sender__(self):
        to_send = ""
        while True:
            to_add = ""
            try:
                to_add = self.message_queue.get(block=False)
            except queue.Empty:
                break
            
            #Message would be too long, send part of it first
            if len(to_send + to_add) >= MessageSender.MAXIMUM_MESSAGE_LENGTH:
                await safe_send(self.running_channel, to_send.strip("\n"))
                to_send = ""
            to_send += to_add
                
        #Send the constructed message
        if len(to_send) > 0:
            await safe_send(self.running_channel, to_send.strip("\n"))



def has_any_role_id(member:discord.Member, role_ids):
    for role in member.roles:
        if role.id in role_ids:
            return True
    return False

def determine_new_role(player_rating, cutoff_data):
    for cutoff in cutoff_data:
        if cutoff[0] is None or player_rating >= cutoff[0]:
            return cutoff[2]
    return None


def determine_role_name(player_rating, cutoff_data):
    for cutoff in cutoff_data:
        if cutoff[0] is None or player_rating >= cutoff[0]:
            return cutoff[1]
    return "No Class (didn't fall into any of the cutoff ranges)"

def get_roles_to_remove(member, guild, role_ids_to_remove):
    roles_to_remove = []
    for role in member.roles:
        if role.id in role_ids_to_remove:
            roles_to_remove.append(role)
    return roles_to_remove

def discard_role_from(role_to_discard, roles):
    to_discard = []
    for ind, role in enumerate(roles):
        if role_to_discard.id == role.id:
            to_discard.append(ind)
            
    to_discard.sort(reverse=True)
    for index in to_discard:
        roles.pop(index)
    return roles

def has_role(member:discord.Member, role_to_find):
    for role in member.roles:
        if role.id == role_to_find.id:
            return True
    return False
            
    
async def __update_roles__(message_sender, guild:discord.Guild, rating_func, previous_role_ids, cutoff_data, remove_old_role=False, track_type="RT", role_type="Class", verbose_output=True, modify_roles=True):
    members = guild.members if modify_roles else guild.members[:500]
    
    for ind, member in enumerate(members):
        if ind % 300 == 0:
            if verbose_output:
                await message_sender.queue_message(f"---- {int(ind/len(members) * 100)}% finished with {track_type} {role_type} role updating.")
        if has_any_role_id(member, previous_role_ids):
            #Need to update since they have previous role IDs
            lookup_name = Player.get_lookup_name(member.display_name)
            
            if lookup_name not in common.all_player_data:
                await message_sender.queue_message(f"---- {common.get_member_info(member)} has previous {track_type} roles, but I can't find them on the {'Google Sheet' if USING_SHEET else 'Website'}.")
                continue

            player_data = common.all_player_data[lookup_name]
            player_rating = rating_func(player_data)
            if player_rating is None:
                await message_sender.queue_message(f"---- {common.get_member_info(member)} has previous {track_type} roles, but their {track_type} rating on {'Google Sheet' if USING_SHEET else 'the Website'} is blank or invalid.")
                continue
        
            new_role_id = determine_new_role(player_rating, cutoff_data)
            if new_role_id is None:
                
                await message_sender.queue_message(f"---- {common.get_member_info(member)} could not determine new role ID for some reason, player rating is {player_rating}")
                continue
            
            new_role_obj = guild.get_role(new_role_id)
            if new_role_obj is None:
                await message_sender.queue_message(f"---- {common.get_member_info(member)} could not find the following role ID in the server: {new_role_id}")
                continue
            
            if remove_old_role:
                roles_to_remove = get_roles_to_remove(member, guild, previous_role_ids)
                if len(roles_to_remove) == 0:
                    await message_sender.queue_message(f"---- {common.get_member_info(member)} had no previous roles to remove. This shouldn't be possible.")
                    continue
                
                #The above 3 lines ensure that they have a role to remove
                #The 3 lines below throw out the new role from that list and check if we need to remove anything
                #If we don't need to remove anything, don't
                original_length = len(roles_to_remove)
                original_roles = [r for r in roles_to_remove]
                discard_role_from(new_role_obj, roles_to_remove)
                if len(roles_to_remove) == 0:
                    continue
                if original_length != len(roles_to_remove):
                    await message_sender.queue_message(f"{common.get_member_info(member)} has multiple roles ({', '.join([r.name for r in original_roles])}). They are either temp-roled, or this is a mistake. I will not change their roles.", True)
                    continue
                
                if modify_roles:
                    try:
                        await member.remove_roles(*roles_to_remove, reason=None, atomic=True)
                    except:
                        await message_sender.queue_message(f"---- {common.get_member_info(member)} could not remove roles: {','.join([role.name for role in roles_to_remove])} - Discord Exception")
                        continue
                    
                    await message_sender.queue_message(f"{common.get_member_info(member)} removed roles: {','.join([role.name for role in roles_to_remove])}")
                else:
                    await message_sender.queue_message(f"{common.get_member_info(member)} would remove roles: {','.join([role.name for role in roles_to_remove])}")
                    
                        
            #If they already have the role, don't bother wasting an API call to add it
            if has_any_role_id(member, [new_role_obj.id]):
                continue
            
            if not modify_roles:
                await message_sender.queue_message(f"{common.get_member_info(member)} would add roles: {new_role_obj.name}")
                pass
            else:
                try:
                    await member.add_roles(new_role_obj, reason=None, atomic=True)
                except:
                    await message_sender.queue_message(f"---- {common.get_member_info(member)} could not add roles: {new_role_obj.name} - Discord Exception")
                
                
                await message_sender.queue_message(f"{common.get_member_info(member)} added roles: {new_role_obj.name}")

                
            
            
                
        

async def update_roles(message_sender, guild, verbose=True, modify_roles=True, only_rt=None):
    if verbose:
        await message_sender.queue_message(f"Lounge server has {len(guild.members)} members.")
    do_ct = only_rt is False or only_rt is None
    do_rt = only_rt is True or only_rt is None
    
    if do_rt:
        if verbose:
            await message_sender.queue_message("--------------- Updating RT Class Roles ---------------")
        rt_class_rating_func = lambda p: p.rt_mmr
        rt_cutoff_to_use = common.RT_CLASS_ROLE_CUTOFFS if len(common.test_cutoffs) == 0 else common.test_cutoffs
        await __update_roles__(message_sender, guild, rt_class_rating_func, common.RT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE, rt_cutoff_to_use, True, track_type="RT", role_type="Class", verbose_output=verbose, modify_roles=modify_roles)
        
        if verbose:
            await message_sender.queue_message("--------------- Updating RT Ranking Roles ---------------")
        rt_role_rating_func = lambda p: p.rt_lr
        await __update_roles__(message_sender, guild, rt_role_rating_func, common.RT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE, common.RT_RANKING_ROLE_CUTOFFS, True, track_type="RT", role_type="Ranking", verbose_output=verbose, modify_roles=modify_roles)
    
    if do_ct:
        if verbose:
            await message_sender.queue_message("--------------- Updating CT Class Roles ---------------")
        ct_class_rating_func = lambda p: p.ct_mmr
        ct_cutoff_to_use = common.CT_CLASS_ROLE_CUTOFFS if len(common.test_cutoffs) == 0 else common.test_cutoffs
        await __update_roles__(message_sender, guild, ct_class_rating_func, common.CT_MUST_HAVE_ROLE_ID_TO_UPDATE_CLASS_ROLE, ct_cutoff_to_use, True, track_type="CT", role_type="Class", verbose_output=verbose, modify_roles=modify_roles)
        
    
        if verbose:
            await message_sender.queue_message("--------------- Updating CT Ranking Roles ---------------")
        ct_role_rating_func = lambda p: p.ct_lr
        await __update_roles__(message_sender, guild, ct_role_rating_func, common.CT_MUST_HAVE_ROLE_ID_TO_UPDATE_RANKING_ROLE, common.CT_RANKING_ROLE_CUTOFFS, True, track_type="CT", role_type="Ranking", verbose_output=verbose, modify_roles=modify_roles)
        

async def pull_data(message_sender, verbose=True, alternative_ctx=None):
    if USING_SHEET:
        pass
        #google_sheet_loader.update_player_data() 
    else:
        await website_api_loader.PlayerDataLoader.update_player_data(message_sender, verbose, alternative_ctx)

    if USING_WEBSITE_FOR_CUTOFFS:
        if len(common.test_cutoffs) == 0: #No hypothetical cutoffs are being used, so pull data
            await website_api_loader.CutoffDataLoader.update_cutoff_data(message_sender, verbose, alternative_ctx)   
    
async def main(message_sender:MessageSender, verbose=True, modify_roles=True, only_rt=None):
    lounge_server = bot.get_guild(lounge_server_id)
    if lounge_server is None:
        print("I'm not in the Lounge server.")
        raise CustomExceptions.FatalError("Not in Lounge")
        return
    
    try:
        if verbose:
            await message_sender.queue_message(f"""Hello, I'm back to automate your role removal and addition process. Please pay me, my 1's and 0's work so hard.
I am now running. I **will {'' if modify_roles else 'NOT '}**be modifying roles in this server.

Updating roles started.""")
            
    except:
        print("I can't see the bots channel that I'm supposed to be running in.")
        return
    
    
    await pull_data(message_sender, verbose)
    
    await update_roles(message_sender, lounge_server, verbose, modify_roles, only_rt)
    
    if verbose:
        if not modify_roles:
            await message_sender.queue_message("Testing ended.")
        else:
            await message_sender.queue_message("Finished updating roles.")

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
        global message_sender
        
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
        self.message_sender_setup()
        self.just_initialized = True
        self.first_run = False
        self.role_updating_task = self.__role_updating_task__.start()
        
    
    def message_sender_setup(self):
        lounge_server = self.bot.get_guild(lounge_server_id)
        if lounge_server is None:
            print("I'm not in the Lounge server.")
            raise CustomExceptions.FatalError("Not in Lounge")
            return
        
        running_channel = bot.get_channel(running_channel_id)
        if running_channel is None:
            print("I can't see the running channel.")
            raise CustomExceptions.FatalError("Cannot see running channel.")
            return
        
        self.message_sender = MessageSender(running_channel)
        self.message_sender.send_queued_messages.start()
        self.message_sender.history_checker_clearing.start()
        


            
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def resumetop(self, ctx, number_of_top_players: int):
        """This command resumes the bot keeping the top x players "Top" roles up to date, which runs every 120 seconds. The normal role updating routine must be running already for this to work."""
        await ctx.send(f"This is not yet implemented.")
        return
    
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def stoptop(self, ctx):
        """This command stops the bot from keeping the top x players "Top" roles up to date every 120 seconds."""
        await ctx.send(f"This is not yet implemented.")
        return
    
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def toprole(self, ctx, rt_or_ct:str, role_id:int):
        """This command sets the Top X role id for either RTs or CTs."""
        await ctx.send(f"This is not yet implemented.")
        return
    
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def activeplayers(self, ctx:commands.Context, rt_or_ct:str, number_of_days:int):
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
        
        if not self.__role_updating_task__.is_running():
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
    async def inclass(self, ctx:commands.Context, rt_or_ct:str, number_of_days:int=None):
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
        
        if not self.__role_updating_task__.is_running():
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
    async def testcutoffs(self, ctx:commands.Context):
        """This command sets test cutoffs, which can then be used by the !activeplayers, !hypotheticalroles, and !inclass commands to see the effect a proposed cutoff may have.
        
        The syntax of the command is !testcutoffs ClassName, LowerCutoff, ClassName, LowerCutoff, ...
        If you want your lower cutoff to be Negative Infinity, do -Infinity
        
        For example, !testcutoffs Class F, -Infinity, Class E, 1500, Class D, 4000, Class C, 8000"""
        
        testcutoff_error_message = """The syntax of the command is `!testcutoffs ClassName, LowerCutoff, ClassName, LowerCutoff, ...`
If you want your lower cutoff to be Negative Infinity, do -Infinity
        
For example, `!testcutoffs Class F, -Infinity, Class E, 1500, Class D, 4000, Class C, 8000`"""
        
        if self.__role_updating_task__.is_running():
            await ctx.send(f"The bot is running role updating every {LOOP_TIME} seconds, which will override and test cutoffs you set. You should first do `!stop` and then use the `!testcutoffs` command.")
            return
        
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
    @badwolf_command_check()
    async def resume(self, ctx): #suppress
        """This command resumes the bot keeping everyone's role up to date, which runs every 120 seconds."""
        if self.__role_updating_task__.is_running():
            await ctx.send(f"The bot is already running role updating every {LOOP_TIME} seconds. If you want to stop it, do `!stop`")
        else:
            self.first_run = False
            self.__role_updating_task__.start()
            await ctx.send("Resumed.")
            
            
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def stop(self, ctx):
        """This command stops the bot from keeping everyone's role up to date every 120 seconds."""
        if not self.__role_updating_task__.is_running():
            await ctx.send(f"The bot is not updating roles in the background. If you want to start updating roles in the background, do `!resume`")
        else:
            self.first_run = True
            self.__role_updating_task__.cancel()
            await ctx.send(f"The bot has stopped updating roles in the background. If you want to start updating roles in the background again, do `!resume`")
        
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def updateroles(self, ctx):
        """This command resumes the bot keeping everyone's role up to date, which runs every 120 seconds."""
        if self.__role_updating_task__.is_running():
            await ctx.send(f"The bot is already running role updating every {LOOP_TIME} seconds. If you want to stop it and manually run the updating process **one time**, do `!stop` and then `!updateroles`. You should then start the automated role updating process again by doing `!resume`")
        else:
            await main(self.message_sender, verbose=True)
            
    @commands.command()
    @commands.guild_only()
    @lounge_only_check()
    @commands.max_concurrency(number=1,wait=True)
    @owner_or_staff()
    async def hypotheticalroles(self, ctx, rt_or_ct:str):
        """This command simply displays the roles each person were to receive and lose. It does not change anyone's roles. Before doing this command, you should !stop and then !testcutoffs to setup your test scenario."""
    
        is_rt = None
        if rt_or_ct.lower() == "rt":
            is_rt = True
        elif rt_or_ct.lower() == "ct":
            is_rt = False
        else:
            await ctx.send(f'"{rt_or_ct}" is not a valid option. Valid options are: RT or CT')
            return
    
        if self.__role_updating_task__.is_running():
            await ctx.send(f"The bot is already running role updating every {LOOP_TIME} seconds. If you want to stop it to set test cutoffs and view the role's people would hypothetically lose and receive, do `!stop` and then `!testcutoffs` and then `!hypotheticalroles`.")
        else:
            temp_message_sender = MessageSender(ctx.channel)
            temp_message_sender.send_queued_messages.start()
            await main(self.message_sender, verbose=True, modify_roles=False, only_rt=is_rt)
            await asyncio.sleep(MessageSender.TIME_BETWEEN_MESSAGES+1)
            temp_message_sender.send_queued_messages.cancel()
    
    @tasks.loop(seconds=LOOP_TIME)
    async def __role_updating_task__(self):
        common.test_cutoffs.clear()
        
        temp = self.first_run and not self.just_initialized
        if self.just_initialized:
            await self.message_sender.queue_message("I'm running again.")
        self.just_initialized = False
        self.first_run = False
        try:
            await main(self.message_sender, verbose=temp)
        except CustomExceptions.FatalError:
            #Should we exit...?
            print(f"{datetime.now()}: Fatal error.")
            raise
        except discord.Forbidden:
            print(f"{datetime.now()}: Forbidden error.")
            #We can't send messages, no big deal, staff probably made a mistake
            pass
        except CustomExceptions.NoRoleFound:
            print(f"{datetime.now()}: No role found.")
            pass
        except CustomExceptions.PlayerDataAPIBadData:
            print(f"{datetime.now()}: Bad data received from API for player.")
            pass
        except CustomExceptions.CutoffAPIBadData:
            print(f"{datetime.now()}: Bad data received from API for cutoffs.")
            pass
        except CustomExceptions.BadAPIData:
            print(f"{datetime.now()}: Bad data received from API. Other type of bad data, please make sure you specify and catch the exact exception, not just the base exception.")
            pass
        except Player.BadDataGiven:
            print(f"{datetime.now()}: Bad data given to Player.")
            pass
        except Exception as e:
            print(f"{datetime.now()}: Unknown error: {str(e)}")
            try:
                await self.message_sender.queue_message("An unknown error happened. Let Bad Wolf know (but don't ping him too much please).")
            except:
                pass

bot.run(bot_key)
    