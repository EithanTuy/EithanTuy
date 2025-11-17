# utils.py
# general helper functions used by many modules. all comments are lowercase.

import math
import pygame

def clamp(v, lo, hi):
    # keep value inside range
    return max(lo, min(hi, v))

def distance(a, b):
    # euclidean distance
    return math.hypot(a[0] - b[0], a[1] - b[1])

def format_time(seconds):
    # turn float into m:ss.ms format for speedrunning
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:05.2f}"

def draw_text_center(surface, font, text, color, y):
    # utility for centered text
    t = font.render(text, True, color)
    surface.blit(t, (surface.get_width()//2 - t.get_width()//2, y))
