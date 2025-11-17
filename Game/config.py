WIDTH = 960
HEIGHT = 540
FPS = 60

MAX_FLOORS = 4

PLAYER_BASE_SPEED = 240
PLAYER_BASE_HP = 100
PLAYER_BASE_ENERGY = 100
PLAYER_ENERGY_REGEN = 18

DASH_COST = 20
DASH_SPEED = 520
DASH_TIME = 0.15

MAP_W = 40
MAP_H = 30
TILE_SIZE = 48

BIOMES = ["cavern","ice","crypt","magma","machine"]

ENEMY_BASE_HP = 40
ENEMY_BASE_SPEED = 140

BOSS_BASE_HP = 400
BOSS_BASE_SPEED = 110
BOSS_PROJECTILE_SPEED = 300

WEAPONS = {
    "pistol": {"cooldown":0.20,"damage":22,"speed":480,"spread":0.05,"pellets":1,"energy":0,"color":(80,200,255)},
    "shotgun":{"cooldown":0.65,"damage":15,"speed":420,"spread":0.55,"pellets":6,"energy":6,"color":(255,230,120)},
    "rail":{"cooldown":1.25,"damage":80,"speed":820,"spread":0.02,"pellets":1,"energy":14,"color":(170,120,255)},
    "beam": {"cooldown":0.12,"damage":14,"speed":980,"spread":0.0,"pellets":1,"energy":2,"color":(140,230,255)},
    "rocket": {"cooldown":1.05,"damage":140,"speed":520,"spread":0.07,"pellets":1,"energy":16,"color":(255,160,90)},
    "boomerang": {"cooldown":0.42,"damage":36,"speed":520,"spread":0.0,"pellets":1,"energy":6,"color":(255,220,120)}
}

BLACK = (0,0,0)
WHITE = (240,240,240)
GRAY = (70,70,70)
DARK_GRAY = (20,20,20)
RED = (220,60,60)
GREEN = (50,200,120)
BLUE = (80,150,255)
CYAN = (80,220,220)
YELLOW = (240,220,80)
ORANGE = (255,150,60)
PURPLE = (160,100,255)
