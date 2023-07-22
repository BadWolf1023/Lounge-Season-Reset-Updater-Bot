'''
Created on Mar 7, 2021

@author: willg
'''
from CustomExceptions import NotLounge
from common import is_lounge
from discord import app_commands



def lounge_only_check():
    return app_commands.check(exception_on_not_lounge)

async def exception_on_not_lounge(interaction):
    if not is_lounge(interaction):
        raise NotLounge("Not Lounge server.")
    return True


