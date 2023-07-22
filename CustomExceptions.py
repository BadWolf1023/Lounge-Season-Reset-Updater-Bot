'''
Created on Feb 23, 2021

@author: willg
'''
from discord.app_commands import AppCommandError

class NotLounge(AppCommandError):
    pass

class NotBadWolf(AppCommandError):
    pass

class BadAPIData(Exception):
    pass

class CutoffAPIBadData(BadAPIData):
    pass

class NoRoleFound(CutoffAPIBadData):
    pass

class EventAPIBadData(BadAPIData):
    pass

class PlayerDataAPIBadData(BadAPIData):
    pass

class FatalError(Exception):
    pass
