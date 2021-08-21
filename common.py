'''
Created on Aug 21, 2021

@author: willg
'''

def isfloat(value:str):
    try:
        float(value)
        return True
    except ValueError:
        return False
    
def isint(value:str):
    try:
        int(value)
        return True
    except ValueError:
        return False