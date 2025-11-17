# entities.py
# player, enemy, and boss behavior. all comments are lowercase.

import math
import pygame

from config import (
    PLAYER_BASE_SPEED,
    PLAYER_BASE_HP,
    PLAYER_BASE_ENERGY,
    PLAYER_ENERGY_REGEN,
    DASH_COST,
    DASH_SPEED,
    DASH_TIME,
    ENEMY_BASE_HP,
    ENEMY_BASE_SPEED,
    BOSS_BASE_HP,
    BOSS_BASE_SPEED,
    BOSS_PROJECTILE_SPEED,
    WEAPONS,
    RED,
    BLUE,
    CYAN,
    GREEN,
    YELLOW,
    PURPLE,
)
from utils import clamp, distance
from objects import Particle, Bullet

class Player:
    # handles movement, dash, shooting, xp, and stats
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.max_hp = PLAYER_BASE_HP
        self.hp = PLAYER_BASE_HP
        self.max_energy = PLAYER_BASE_ENERGY
        self.energy = PLAYER_BASE_ENERGY

        self.speed_mult = 1.0
        self.damage_mult = 1.0
        self.fire_rate_mult = 1.0

        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_dir = (0.0, 0.0)
        self.iframes = 0.0

        self.current_weapon = "pistol"
        self.unlocked_weapons = {"pistol"}

        self.last_shot = 0.0

        self.level = 1
        self.xp = 0
        self.xp_to_next = 100

        self.kills = 0
        self.last_move_dir = (0.0, 0.0)

    def center(self):
        return (self.x, self.y)

    def add_xp(self, amount):
        self.xp += amount

    def check_auto_level(self):
        # automatically levels up and buffs stats
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.35 + 40)
            self.max_hp += 10
            self.hp += 10
            self.max_energy += 8
            self.energy += 8
            self.damage_mult += 0.07
            self.fire_rate_mult += 0.06
            self.speed_mult += 0.04
            leveled = True
        return leveled

    def heal(self, amount):
        self.hp = clamp(self.hp + amount, 0, self.max_hp)

    def give_energy(self, amount):
        self.energy = clamp(self.energy + amount, 0, self.max_energy)

    def hurt(self, dmg, particles):
        if self.iframes > 0 or self.is_dashing:
            return
        self.hp -= dmg
        self.iframes = 0.5
        for _ in range(8):
            a = math.tau * math.random() if hasattr(math, "random") else 0
        # simpler blood burst
        for _ in range(10):
            ang = math.tau * (float(_)/10.0)
            sp = 220
            vx = math.cos(ang) * sp
            vy = math.sin(ang) * sp
            particles.append(Particle(self.x, self.y, vx, vy, 0.35, RED))

    def update(self, dt, keys, dungeon):
        self.iframes = max(0.0, self.iframes - dt)
        self.energy = clamp(self.energy + PLAYER_ENERGY_REGEN * dt, 0, self.max_energy)

        # dash behavior
        if self.is_dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.is_dashing = False
            else:
                dx = self.dash_dir[0] * DASH_SPEED * dt
                dy = self.dash_dir[1] * DASH_SPEED * dt
                new_x = self.x + dx
                new_y = self.y + dy
                if not dungeon.is_solid_world(new_x, self.y):
                    self.x = new_x
                if not dungeon.is_solid_world(self.x, new_y):
                    self.y = new_y
                return

        # basic movement
        vx = 0.0
        vy = 0.0
        if keys[pygame.K_w]:
            vy -= 1.0
        if keys[pygame.K_s]:
            vy += 1.0
        if keys[pygame.K_a]:
            vx -= 1.0
        if keys[pygame.K_d]:
            vx += 1.0

        mag = math.hypot(vx, vy)
        if mag > 0:
            vx /= mag
            vy /= mag
            speed = PLAYER_BASE_SPEED * self.speed_mult
            self.last_move_dir = (vx, vy)
            new_x = self.x + vx * speed * dt
            new_y = self.y + vy * speed * dt

            if not dungeon.is_solid_world(new_x, self.y):
                self.x = new_x
            if not dungeon.is_solid_world(self.x, new_y):
                self.y = new_y
        else:
            self.last_move_dir = (self.last_move_dir[0] * 0.92, self.last_move_dir[1] * 0.92)

    def start_dash(self, target_world_pos):
        if self.is_dashing:
            return
        if self.energy < DASH_COST:
            return

        tx, ty = target_world_pos
        dx = tx - self.x
        dy = ty - self.y
        mag = math.hypot(dx, dy) or 1.0
        self.dash_dir = (dx / mag, dy / mag)
        self.dash_timer = DASH_TIME
        self.is_dashing = True
        self.energy -= DASH_COST

    def can_shoot(self, time_now):
        data = WEAPONS[self.current_weapon]
        cd = data["cooldown"] / self.fire_rate_mult
        return time_now - self.last_shot >= cd

    def shoot(self, target_world_pos, bullets, time_now, particles):
        data = WEAPONS[self.current_weapon]
        if self.energy < data["energy"]:
            return

        tx, ty = target_world_pos
        dx = tx - self.x
        dy = ty - self.y
        if dx == 0 and dy == 0:
            return

        base_angle = math.atan2(dy, dx)
        pellets = data["pellets"]
        spread = data["spread"]
        damage = int(data["damage"] * self.damage_mult)
        speed = data["speed"]
        color = data["color"]

        if pellets == 1:
            angles = [base_angle]
        else:
            angles = [
                base_angle + (i - (pellets - 1) / 2) * spread / max(pellets - 1, 1)
                for i in range(pellets)
            ]

        for ang in angles:
            bullets.append(Bullet(self.x, self.y, ang, speed, damage, color))

        self.energy -= data["energy"]
        self.last_shot = time_now

        # muzzle flash
        mx = self.x + math.cos(base_angle) * 20
        my = self.y + math.sin(base_angle) * 20
        for _ in range(6):
            ang = base_angle + (spread * (0.5 - _ / 6.0))
            sp = 260
            vx = math.cos(ang) * sp
            vy = math.sin(ang) * sp
            particles.append(Particle(mx, my, vx, vy, 0.25, YELLOW))

    def switch_weapon(self, index):
        names = sorted(list(self.unlocked_weapons))
        if 0 <= index < len(names):
            self.current_weapon = names[index]

    def draw(self, surf, cam_x, cam_y, mouse_pos):
        cx = self.x - cam_x
        cy = self.y - cam_y
        body = pygame.Rect(0, 0, 26, 26)
        body.center = (cx, cy)
        col = BLUE if self.iframes <= 0 else (120, 120, 255)
        pygame.draw.rect(surf, col, body)

        mx, my = mouse_pos
        dx = mx - cx
        dy = my - cy
        ang = math.atan2(dy, dx)
        hx = cx + math.cos(ang) * 20
        hy = cy + math.sin(ang) * 20
        pygame.draw.line(surf, CYAN, (cx, cy), (hx, hy), 3)

class Enemy:
    # simple chasing enemy
    def __init__(self, x, y, hp_mult=1.0, speed_mult=1.0):
        self.x = x
        self.y = y
        self.max_hp = int(ENEMY_BASE_HP * hp_mult)
        self.hp = self.max_hp
        self.speed_mult = speed_mult
        self.phase = 0.0

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, dmg, particles):
        self.hp -= dmg
        for _ in range(6):
            ang = math.tau * (_ / 6.0)
            sp = 140
            vx = math.cos(ang) * sp
            vy = math.sin(ang) * sp
            particles.append(Particle(self.x, self.y, vx, vy, 0.25, PURPLE))

    def update(self, dt, player_pos, dungeon):
        if not self.is_alive():
            return

        px, py = player_pos
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy) + 1e-6
        dir_x = dx / dist
        dir_y = dy / dist

        # wiggle so they don't all line up
        self.phase += dt * 4.0
        offset = math.sin(self.phase) * 0.7
        side_x = -dir_y * offset
        side_y = dir_x * offset

        speed = ENEMY_BASE_SPEED * self.speed_mult
        new_x = self.x + (dir_x + side_x) * speed * dt
        new_y = self.y + (dir_y + side_y) * speed * dt

        if not dungeon.is_solid_world(new_x, self.y):
            self.x = new_x
        if not dungeon.is_solid_world(self.x, new_y):
            self.y = new_y

    def draw(self, surf, cam_x, cam_y):
        if not self.is_alive():
            return
        r = pygame.Rect(0, 0, 24, 24)
        r.center = (self.x - cam_x, self.y - cam_y)
        pygame.draw.rect(surf, PURPLE, r)

        # hp bar
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bw = 22
        bx = r.centerx - bw // 2
        by = r.top - 6
        pygame.draw.rect(surf, (40, 40, 40), (bx, by, bw, 4))
        pygame.draw.rect(surf, RED, (bx, by, int(bw * ratio), 4))

class Boss:
    # big boss that shoots projectiles
    def __init__(self, x, y, hp_mult=1.0, speed_mult=1.0):
        self.x = x
        self.y = y
        self.max_hp = int(BOSS_BASE_HP * hp_mult)
        self.hp = self.max_hp
        self.speed_mult = speed_mult
        self.shoot_timer = 1.5
        self.phase = 0.0

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, dmg, particles):
        self.hp -= dmg
        for _ in range(12):
            ang = math.tau * (_ / 12.0)
            sp = 260
            vx = math.cos(ang) * sp
            vy = math.sin(ang) * sp
            particles.append(Particle(self.x, self.y, vx, vy, 0.35, (255, 180, 180)))

    def update(self, dt, player_pos, dungeon, boss_bullets):
        if not self.is_alive():
            return
        px, py = player_pos
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy) + 1e-6
        dir_x = dx / dist
        dir_y = dy / dist

        self.phase += dt
        offset = math.sin(self.phase * 1.7) * 0.9
        side_x = -dir_y * offset
        side_y = dir_x * offset

        speed = BOSS_BASE_SPEED * self.speed_mult
        new_x = self.x + (dir_x + side_x) * speed * dt
        new_y = self.y + (dir_y + side_y) * speed * dt

        if not dungeon.is_solid_world(new_x, self.y):
            self.x = new_x
        if not dungeon.is_solid_world(self.x, new_y):
            self.y = new_y

        # shooting pattern
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 1.4
            base_angle = math.atan2(dy, dx)
            for i in range(-2, 3):
                ang = base_angle + i * 0.25
                boss_bullets.append(
                    Bullet(
                        self.x,
                        self.y,
                        ang,
                        BOSS_PROJECTILE_SPEED,
                        10,
                        (255, 140, 140),
                    )
                )

    def draw(self, surf, cam_x, cam_y, screen_width):
        if not self.is_alive():
            return
        r = pygame.Rect(0, 0, 70, 70)
        r.center = (self.x - cam_x, self.y - cam_y)
        pygame.draw.rect(surf, (130, 30, 30), r)
        pygame.draw.rect(surf, (220, 80, 80), r, 3)

        # boss hp bar on top of screen
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bw = 260
        bx = screen_width // 2 - bw // 2
        by = 18
        pygame.draw.rect(surf, (40, 40, 40), (bx - 2, by - 2, bw + 4, 14))
        pygame.draw.rect(surf, RED, (bx, by, int(bw * ratio), 10))
