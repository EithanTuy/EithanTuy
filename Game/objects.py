# objects.py
# visual particles, bullets, xp orbs, and portals. all comments are lowercase.

import math
import pygame

from config import CYAN, GREEN, YELLOW, PURPLE, ORANGE
from config import TILE_SIZE
from utils import clamp, distance

class Particle:
    # small fading circle particle
    def __init__(self, x, y, vx, vy, life, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surf, cam_x, cam_y):
        if self.life <= 0:
            return
        alpha = clamp(self.life / self.max_life, 0, 1)
        radius = max(1, int(4 * alpha))
        col = (
            int(self.color[0] * alpha),
            int(self.color[1] * alpha),
            int(self.color[2] * alpha),
        )
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (radius, radius), radius)
        surf.blit(s, (self.x - radius - cam_x, self.y - radius - cam_y))

class Bullet:
    # basic projectile
    def __init__(self, x, y, angle, speed, damage, color):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = damage
        self.color = color
        self.life = 1.3

    def update(self, dt, dungeon):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

        if dungeon.is_solid_world(self.x, self.y):
            self.life = 0

    def draw(self, surf, cam_x, cam_y):
        if self.life <= 0:
            return
        r = pygame.Rect(self.x - 3 - cam_x, self.y - 3 - cam_y, 6, 6)
        pygame.draw.rect(surf, self.color, r)

class XpOrb:
    # xp orb dropped by enemies
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value

    def update(self, dt, player_pos):
        px, py = player_pos
        d = distance((self.x, self.y), (px, py))
        if d < 220 and d > 0:
            # light homing
            dx = (px - self.x) / d
            dy = (py - self.y) / d
            self.x += dx * 160 * dt
            self.y += dy * 160 * dt

    def draw(self, surf, cam_x, cam_y):
        r = pygame.Rect(self.x - 5 - cam_x, self.y - 5 - cam_y, 10, 10)
        pygame.draw.ellipse(surf, GREEN, r)

class Portal:
    # portal appears after boss dies and leads to next floor or victory
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = TILE_SIZE // 2

    def collides_with(self, player_pos):
        return distance((self.x, self.y), player_pos) < self.radius * 0.7

    def draw(self, surf, cam_x, cam_y, time):
        cx = self.x - cam_x
        cy = self.y - cam_y
        r = self.radius
        # animated ring
        angle = math.sin(time * 4.0) * 0.4
        color1 = (int(150 + 80 * math.sin(time * 2)), 120, 255)
        color2 = (120, int(150 + 80 * math.cos(time * 2)), 255)

        pygame.draw.circle(surf, color2, (int(cx), int(cy)), int(r))
        pygame.draw.circle(surf, color1, (int(cx), int(cy)), int(r * 0.6))
        pygame.draw.circle(surf, (0, 0, 0), (int(cx), int(cy)), int(r * 0.4))
