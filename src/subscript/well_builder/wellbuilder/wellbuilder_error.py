# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 14:22:54 2019

@author: iari
"""
import sys

VERBOSE = True     # override this if you dont want info-messages displayed

def wb_error(message):
    """Print error messages and exit the program

    Args:
        message (str) : messages
    """
    print("Error : " + message)
    sys.exit()


def wb_warning(message):
    """Print warning messages

    Args:
        message (str) : messages
    """
    print("Warning : " + message)


def wb_message(message):
    """Print messages
        No worries, it is not an error or warning, just information

    Args:
        message (str) : messages
    """
    if not VERBOSE: return
    print("Message : " + message)
