'''
Created on Mar 7, 2021

@author: willg
'''
from CustomExceptions import NotLounge, NotBadWolf
from common import is_lounge, BAD_WOLF_ID, get_guild_id
from discord.ext import commands

STAFF_ROLE_NAMES = ("Boss", "Lower Tier RT Arbitrator", "Higher Tier RT Arbitrator", "Lower Tier CT Arbitrator", "Higher Tier CT Arbitrator", "Developer Access", "Developer")
def owner_or_staff():
    original = commands.has_any_role(*STAFF_ROLE_NAMES).predicate
    async def extended_check(ctx):
        if ctx.guild is None:
            return False
        return ctx.author.id == BAD_WOLF_ID or await original(ctx)
    return commands.check(extended_check)


def lounge_only_check():
    return commands.check(exception_on_not_lounge)

async def exception_on_not_lounge(ctx):
    if not is_lounge(ctx):
        raise NotLounge("Not Lounge server.")
    return True

def badwolf_command_check():
    return commands.check(is_bad_wolf)

async def is_bad_wolf(ctx):
    if ctx.author.id != BAD_WOLF_ID:
        raise NotBadWolf("Author is not Bad Wolf.")
    return True       
