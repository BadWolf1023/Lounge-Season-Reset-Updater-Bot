'''
Created on Feb 23, 2021

@author: willg
'''

from discord.ext.commands import CommandError

class NotLounge(CommandError):
    pass

class NotBadWolf(CommandError):
    pass

class BadAPIData(Exception):
    pass

class CutoffAPIBadData(BadAPIData):
    pass

class NoRoleFound(CutoffAPIBadData):
    pass

class PlayerDataAPIBadData(BadAPIData):
    pass

class FatalError(Exception):
    pass
