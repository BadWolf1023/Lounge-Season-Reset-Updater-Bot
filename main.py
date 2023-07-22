'''
Created on Aug 5, 2021

@author: willg
'''
import discord
from discord import app_commands
from discord.ext import commands, tasks
import website_api_loader
import Player
import common
from ExtraChecks import lounge_only_check
import CustomExceptions
from datetime import datetime, timedelta
import queue
from typing import Literal, Dict, Tuple, List, Optional, Union, Any

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



def determine_role_name(player_rating, cutoff_data):
    if player_rating is not None:
        for cutoff in cutoff_data:
            if cutoff[0] is None or player_rating >= cutoff[0]:
                return cutoff[1]
    return "No Class (didn't fall into any of the cutoff ranges)"

async def pull_data(interaction: discord.Interaction):
    await website_api_loader.PlayerDataLoader.update_player_data(interaction)
    await website_api_loader.CutoffDataLoader.update_cutoff_data(interaction)

async def pull_event_data(interaction: discord.Interaction):
    await website_api_loader.TierDataLoader.update_event_data(interaction)

async def send_file_with_players_in_each_class(interaction, is_rt, last_x_days, use_test_cutoffs):
    current_est_time = datetime.now() + timedelta(hours=HOURS_TO_ADD_TO_MAKE_EST)
    need_to_have_played_after_date = None if last_x_days == 0 else (current_est_time - timedelta(days=last_x_days))
    get_mmr_and_date = None
    if is_rt:
        get_mmr_and_date = lambda x: (x.rt_mmr, x.rt_last_event)
    else:
        get_mmr_and_date = lambda y: (y.ct_mmr, y.ct_last_event)
    
    cutoffs = common.RT_CLASS_ROLE_CUTOFFS if is_rt else common.CT_CLASS_ROLE_CUTOFFS
    if use_test_cutoffs:
        cutoffs = common.test_cutoffs
        
    activity_reqs = {}
    for cutoff_data in reversed(cutoffs):
        activity_reqs[cutoff_data[1]] = [[], []] #active players, total players
    activity_reqs["No Class (didn't fall into any of the cutoff ranges)"] = [[], []]
    
    for player_data in common.all_player_data.values():
        mmr, last_event_date = get_mmr_and_date(player_data)
        if mmr is None: #They haven't ever played this track type (RT or CT), so don't count them - skip
            continue
        
        class_name_for_player = determine_role_name(mmr, cutoffs)
        activity_reqs[class_name_for_player][1].append(player_data.name)
        if need_to_have_played_after_date is None or last_event_date >= need_to_have_played_after_date:
            activity_reqs[class_name_for_player][0].append(player_data.name)

    preface = "Using simulation cutoffs:" if use_test_cutoffs else "Currently in Lounge:"
    to_send = f"{preface} Active players in each {'RT' if is_rt else 'CT'} class during the last {last_x_days} days.\nNote: Active is defined as players who have played at least 1 event in the past {last_x_days} days, as you specified.\nNote: Total players is the total players in the class, regardless of whether they have played an event this season."
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
    
    await common.safe_send_file(interaction, to_send)
    

async def send_active_players(interaction: discord.Interaction, is_rt, last_x_days, use_test_cutoffs):
    current_est_time = datetime.now() + timedelta(hours=HOURS_TO_ADD_TO_MAKE_EST)
    need_to_have_played_after_date = current_est_time - timedelta(days=last_x_days)
    get_mmr_and_date = None
    if is_rt:
        get_mmr_and_date = lambda x: (x.rt_mmr, x.rt_last_event)
    else:
        get_mmr_and_date = lambda y: (y.ct_mmr, y.ct_last_event)
    
    cutoffs = common.RT_CLASS_ROLE_CUTOFFS if is_rt else common.CT_CLASS_ROLE_CUTOFFS
    if use_test_cutoffs:
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
    preface = "Using simulation cutoffs:" if use_test_cutoffs else "Currently in Lounge:"
    to_send = f"{preface} Number of active players in each {'RT' if is_rt else 'CT'} class during the last **{last_x_days} days**.\n**Note:** The total number of players is the number of players in the Class who have played 1 event or more this season.\n**Note:** The number of active players are the players that have played at least 1 event in the past **{last_x_days} days**, as you specified."
    for cutoff_name, (active_players, total_players) in reversed(activity_reqs.items()):
        percentage_active = 0.0
        if total_players > 0:
            percentage_active = active_players / total_players
        percentage_active = int(round(100 * percentage_active, 0))
        
        
        to_send += f"\n{cutoff_name}: {active_players} active players out of {total_players} total players ({percentage_active}%)"
    
    await interaction.followup.send(to_send)
        
async def send_tier_activity(interaction: discord.Interaction, is_rt, last_x_days):
    current_est_time = datetime.now() + timedelta(hours=HOURS_TO_ADD_TO_MAKE_EST)
    need_to_have_played_after_date = current_est_time - timedelta(days=last_x_days)
    event_data = common.RT_EVENT_DATA if is_rt else common.CT_EVENT_DATA

    results = {}
    for tier, event_date in event_data:
        if event_date >= need_to_have_played_after_date:
            if tier not in results:
                results[tier] = 0
            results[tier] += 1

    total_events = sum(results.values())
    
    to_send = f"Number of {'RT' if is_rt else 'CT'} events played in each tier in the last **{last_x_days} days**.\n"
    for tier_name, events_played in sorted(results.items(), reverse=True):
        percentage_played = events_played / total_events if total_events != 0 else 0.0
        percentage_played = int(round(100 * percentage_played, 0))

        to_send += f"\n{tier_name}: {events_played} events played out of {total_events} total events played ({percentage_played}%)"

    await interaction.followup.send(to_send)

bot = commands.Bot(owner_id=common.BAD_WOLF_ID, allowed_mentions=discord.mentions.AllowedMentions.none(), command_prefix=('!'), case_insensitive=True, intents=discord.Intents.all())

@bot.event
async def on_ready():
    global finished_on_ready
    if not finished_on_ready:
        await bot.add_cog(RoleUpdater(bot))
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands: {synced}")
        print("Finished on ready.")
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
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="active_players", description="Shows the number of active players in each class.")
    @app_commands.describe(track_type="RT or CT")
    @app_commands.describe(number_of_days="Only include players who played in the last X days. 7 days is a good starting point.")
    @app_commands.describe(cutoff_type="Use the current MMR cutoffs in Lounge? Or use simulation cutoffs (/simulation cutoffs set)?")
    @lounge_only_check()
    async def activeplayers(self, interaction: discord.Interaction,
                  track_type: Literal["RT", "CT"],
                  number_of_days: int,
                  cutoff_type: Literal["current", "simulation"]):
        """Shows the number of active players in each class."""
        await interaction.response.defer(thinking=True)
        if number_of_days < 1 or number_of_days > 365:
            await interaction.followup.send(f'"{number_of_days}" is not a valid option. Valid options are between 1 days and 365 days.')
            return
        is_rt = track_type == "RT"
        use_test_cutoffs = cutoff_type == "simulation"

        if use_test_cutoffs and len(common.test_cutoffs) == 0:
            await interaction.followup.send(f'You first need to set the simulation cutoffs by using `/simulation cutoffs set`')
            return

        to_edit = await interaction.followup.send("Pulling player data...", wait=True)
        try:
            await pull_data(interaction) #pulls player data, and if no test cutoff data, pulls that too
        finally:
            await to_edit.edit(content="Pulled data.")

            
        await send_active_players(interaction, is_rt, number_of_days, use_test_cutoffs)

    @app_commands.command(name="in_class", description="Show the players in each class.")
    @app_commands.describe(track_type="RT or CT")
    @app_commands.describe(number_of_days="Only include players who played in the last X days. 0 for all players (even with 0 events).")
    @app_commands.describe(cutoff_type="Use the current MMR cutoffs in Lounge? Or use simulation cutoffs (/simulation cutoffs set)?")
    @lounge_only_check()
    async def inclass(self, interaction: discord.Interaction,
                  track_type: Literal["RT", "CT"],
                  number_of_days: int,
                  cutoff_type: Literal["current", "simulation"]):
        """This command sends a list of players in each class. You can also specify an activity criteria.
        
        IMPORTANT NOTE: If you do not specify an activity requirement, all players are included, regardless of whether they have played an event this season. If you did specify an activity requirement, the total number of players statistic is the total number of players in that class, regardless of whether they played an event this season or not. If you're only interested in the activity among people who have played at least 1 event this season, you should check out !activeplayers"""
        await interaction.response.defer(thinking=True)
        if number_of_days < 0 or number_of_days > 365:
            await interaction.followup.send(f'"{number_of_days}" is not a valid option. Valid options are between 0 days and 365 days. If you don\'t want to filter by activity, put 0 days.')
            return
        is_rt = track_type == "RT"
        use_test_cutoffs = cutoff_type == "simulation"

        if use_test_cutoffs and len(common.test_cutoffs) == 0:
            await interaction.followup.send(f'You first need to set the simulation cutoffs by using `/simulation cutoffs set`')
            return

        to_edit = await interaction.followup.send("Pulling player data...", wait=True)
        try:
            await pull_data(interaction)  # pulls player data, and if no test cutoff data, pulls that too
        finally:
            await to_edit.edit(content="Pulled data.")
            
        await send_file_with_players_in_each_class(interaction, is_rt, number_of_days, use_test_cutoffs)

    cutoffs_group = app_commands.Group(name="cutoffs", description="...")
    @cutoffs_group.command(name="show", description="Show Lounge's current MMR cutoffs")
    @app_commands.describe(track_type="RT or CT")
    @lounge_only_check()
    async def display_real_cutoffs(self, interaction: discord.Interaction, track_type: Literal["RT", "CT"]):
        await interaction.response.defer(thinking=True)
        to_edit = await interaction.followup.send("Pulling data...", wait=True)
        try:
            await pull_data(interaction)  # pulls player data, and if no test cutoff data, pulls that too
        finally:
            await to_edit.edit(content="Pulled data.")
        cutoffs = common.RT_CLASS_ROLE_CUTOFFS if track_type == "RT" else common.CT_CLASS_ROLE_CUTOFFS
        await interaction.followup.send(f"Current Lounge {track_type} MMR cutoffs:\n" + common.cutoff_display_text(cutoffs))

    simulation_group = app_commands.Group(name="simulation", description="...")
    simulation_cutoffs_group = app_commands.Group(parent=simulation_group,name="cutoffs", description="Group for simulation cutoff commands")
    @simulation_cutoffs_group.command(name="set", description="Set MMR cutoffs to run simulations.")
    @app_commands.describe(cutoffs="Example: Class F, -Infinity, Class E, 1500, Class D, 4000, Class C, 8000")
    @lounge_only_check()
    async def set_simulation_cutoffs(self, interaction: discord.Interaction,
                          cutoffs: str):
        
        testcutoff_error_message = """The syntax of the command is `/simulation cutoffs set cutoffs: ClassName, LowerCutoff, ClassName, LowerCutoff, ...`
If you want your lower cutoff to be Negative Infinity, do -Infinity
        
For example, `/simulation cutoffs set cutoffs: Class F, -Infinity, Class E, 1500, Class D, 4000, Class C, 8000`"""

        await interaction.response.defer(thinking=True)
        args = cutoffs.split(",")
        LOWEST_CUTOFF = -99999999
        if len(args) < 2:
            await interaction.followup.send(testcutoff_error_message)
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
                        await interaction.followup.send(f'"{lower_cutoff}" is below the minimum number allowed: {LOWEST_CUTOFF}\n\nIf you want to do negative infinity, do "-infinity" for your cutoff number.')
                        return
                elif temp in allowed_negative_infinity_terms:
                    lower_cutoff = None
                else:
                    await interaction.followup.send(f'"{item}" is not a valid number for the lower cutoff for class named {cur_class_data[0]}\n\n{testcutoff_error_message}')
                    return
                
                cur_class_data.insert(0, lower_cutoff)
                new_cutoffs.append((cur_class_data[0], cur_class_data[1]))
        
        new_cutoffs.sort(key=lambda cutoff_data: LOWEST_CUTOFF if cutoff_data[0] is None else cutoff_data[0], reverse=True)
        common.test_cutoffs.clear()
        common.test_cutoffs.extend(new_cutoffs)
        await interaction.followup.send("Test cutoffs:\n" + common.cutoff_display_text(common.test_cutoffs) + "\n\nYou can now use `/active_players` or `/in_class` to see how the proposed cutoffs will change things.")

    @simulation_cutoffs_group.command(name="show", description="Show the currently set simulation MMR cutoffs")
    @lounge_only_check()
    async def display_simulation_cutoffs(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        if len(common.test_cutoffs) == 0:
            await interaction.followup.send(f'You first need to set the simulation cutoffs by using `/simulation cutoffs set`')
            return
        await interaction.followup.send("Test cutoffs:\n" + common.cutoff_display_text(common.test_cutoffs) + "\n\nYou can now use `/active_players` or `/in_class` to see how the proposed cutoffs will change things.")

    simulation_tiers_group = app_commands.Group(name="tier",
                                                description="Group for simulation of tiers.")
    @simulation_tiers_group.command(name="activity", description="See the number of events each tier has played.")
    @app_commands.describe(track_type="RT or CT")
    @app_commands.describe(number_of_days="Only include events played in the last X days. 7 days is a good starting point.")
    @lounge_only_check()
    async def tier_activity(self, interaction: discord.Interaction, track_type: Literal["RT", "CT"], number_of_days: int):
        await interaction.response.defer(thinking=True)

        if number_of_days < 1 or number_of_days > 365:
            await interaction.followup.send(f'"{number_of_days}" is not a valid option. Valid options are between 1 days and 365 days.')
            return
        is_rt = track_type == "RT"

        to_edit = await interaction.followup.send("Pulling event data...", wait=True)
        try:
            await pull_event_data(interaction)  # pulls event data
        finally:
            await to_edit.edit(content="Pulled event data.")
        event_data = common.RT_EVENT_DATA if track_type == "RT" else common.CT_EVENT_DATA

        await send_tier_activity(interaction, is_rt, number_of_days)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    if isinstance(error, CustomExceptions.NotLounge):
        await interaction.response.send_message(f"Command not allowed outside of Lounge.", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        retry_seconds = int(error.retry_after) + 1
        error_str = f"This command is on cooldown. Try again after {retry_seconds} " \
                    f"second{'' if retry_seconds == 1 else 's'}."
        await interaction.response.send_message(error_str, ephemeral=True)
    else:
        raise error

bot.run(bot_key)
    