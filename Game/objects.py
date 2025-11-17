# objects.py
# visual particles, bullets, xp orbs, and portals. all comments are lowercase.

import math
import pygame

from config import CYAN, GREEN, YELLOW, PURPLE, ORANGE
from config import TILE_SIZE, WEAPONS
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
    def __init__(self, x, y, angle, speed, damage, color, crit=False, kind="standard", owner=None):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = damage
        self.color = color
        self.crit = crit
        self.kind = kind
        self.owner = owner
        self.age = 0.0
        self.life = 1.8 if kind == "boomerang" else 1.3

    def update(self, dt, dungeon):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.age += dt
        self.life -= dt

        if self.kind == "boomerang" and self.owner is not None:
            if self.age > 0.35:
                dx = self.owner.x - self.x
                dy = self.owner.y - self.y
                dist = max(1.0, math.hypot(dx, dy))
                speed = math.hypot(self.vx, self.vy)
                self.vx = dx / dist * speed
                self.vy = dy / dist * speed
            if distance((self.x, self.y), (self.owner.x, self.owner.y)) < 18 and self.age > 0.25:
                self.life = 0

        if dungeon.is_solid_world(self.x, self.y):
            self.life = 0

    def draw(self, surf, cam_x, cam_y):
        if self.life <= 0:
            return
        size = 6 if self.kind != "rocket" else 8
        r = pygame.Rect(self.x - size / 2 - cam_x, self.y - size / 2 - cam_y, size, size)
        col = self.color
        if self.crit:
            col = (min(255, col[0] + 60), min(255, col[1] + 60), min(255, col[2] + 40))
        pygame.draw.rect(surf, col, r)
        if self.kind == "boomerang":
            pygame.draw.rect(surf, (0, 0, 0), r, 1)

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


class Pickup:
    # weapon, relic, or consumable pickup
    def __init__(self, x, y, label, kind, color, payload):
        self.x = x
        self.y = y
        self.label = label
        self.kind = kind
        self.color = color
        self.payload = payload
        self.wobble = 0.0

    def update(self, dt):
        self.wobble += dt * 2.0

    def can_collect(self, player_pos):
        return distance((self.x, self.y), player_pos) < 28

    def draw(self, surf, cam_x, cam_y):
        bx = self.x - cam_x
        by = self.y - cam_y + math.sin(self.wobble) * 3
        rect = pygame.Rect(0, 0, 32, 20)
        rect.center = (bx, by)
        pygame.draw.rect(surf, (20, 20, 20), rect.inflate(4, 4))
        pygame.draw.rect(surf, self.color, rect)
        txt_font = pygame.font.SysFont("consolas", 14)
        txt = txt_font.render(self.label, True, (0, 0, 0))
        surf.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))


class RareChest:
    # optional floor reward, drops loot when opened
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.opened = False
        self.timer = 0.0

    def update(self, dt):
        self.timer += dt

    def try_open(self, player_pos):
        if self.opened:
            return False
        if distance((self.x, self.y), player_pos) < 28:
            self.opened = True
            return True
        return False

    def draw(self, surf, cam_x, cam_y):
        bx = self.x - cam_x
        by = self.y - cam_y
        rect = pygame.Rect(0, 0, 30, 22)
        rect.center = (bx, by + math.sin(self.timer * 2) * 2)
        color = ORANGE if not self.opened else (90, 50, 20)
        pygame.draw.rect(surf, (20, 10, 5), rect.inflate(4, 4))
        pygame.draw.rect(surf, color, rect)
        if not self.opened:
            pygame.draw.rect(surf, YELLOW, rect, 2)

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


INTERACTABLE_COLORS = {
    "chest": YELLOW,
    "altar": CYAN,
    "vendor": ORANGE,
}

INTERACTABLE_MINIMAP = {
    "chest": YELLOW,
    "altar": CYAN,
    "vendor": ORANGE,
}


class Interactable:
    # simple interactable with small reward states
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x = x
        self.y = y
        self.state = "ready"
        self.uses = 2 if kind == "vendor" else 1

    def is_active(self):
        return self.state in ("ready", "charging")

    def interact(self, player, particles, rng=None):
        if not self.is_active():
            return
        rng = rng or __import__("random")
        if self.kind == "chest":
            self.state = "opened"
            player.add_xp(30)
            player.give_energy(25)
            player.heal(15)
            self._burst_particles(particles, YELLOW)
        elif self.kind == "altar":
            self.state = "spent"
            player.damage_mult += 0.05
            player.heal(25)
            self._burst_particles(particles, CYAN)
        elif self.kind == "vendor":
            self.uses -= 1
            self._burst_particles(particles, ORANGE)
            self._vendor_reward(player, rng)
            if self.uses <= 0:
                self.state = "spent"

    def _vendor_reward(self, player, rng):
        # either refill energy/hp or unlock a new weapon
        missing_weapons = [w for w in WEAPONS.keys() if w not in player.unlocked_weapons]
        if missing_weapons and rng.random() < 0.5:
            new_w = rng.choice(missing_weapons)
            player.unlocked_weapons.add(new_w)
        else:
            player.give_energy(35)
            player.heal(20)

    def _burst_particles(self, particles, color):
        for i in range(10):
            ang = math.tau * (i / 10.0)
            vx = math.cos(ang) * 120
            vy = math.sin(ang) * 120
            particles.append(Particle(self.x, self.y, vx, vy, 0.3, color))

    def draw(self, surf, cam_x, cam_y, font=None):
        col = INTERACTABLE_COLORS.get(self.kind, GREEN)
        if not self.is_active():
            col = (90, 90, 90)
        r = pygame.Rect(0, 0, TILE_SIZE * 0.6, TILE_SIZE * 0.6)
        r.center = (self.x - cam_x, self.y - cam_y)
        pygame.draw.rect(surf, col, r)
        pygame.draw.rect(surf, (10, 10, 10), r, 2)

        if font is None:
            font = pygame.font.SysFont("consolas", 14)
        letter = {"chest": "C", "altar": "A", "vendor": "V"}.get(self.kind, "?")
        txt = font.render(letter, True, (0, 0, 0))
        surf.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
