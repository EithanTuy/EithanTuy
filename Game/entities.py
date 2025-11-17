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
    ORANGE,
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
            new_x = self.x + vx * speed * dt
            new_y = self.y + vy * speed * dt

            if not dungeon.is_solid_world(new_x, self.y):
                self.x = new_x
            if not dungeon.is_solid_world(self.x, new_y):
                self.y = new_y

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
    def __init__(self, x, y, hp_mult=1.0, speed_mult=1.0, elite=False):
        self.x = x
        self.y = y
        self.max_hp = int(ENEMY_BASE_HP * hp_mult)
        self.hp = self.max_hp
        self.speed_mult = speed_mult
        self.phase = 0.0
        self.kind = "chaser"
        self.color = PURPLE
        self.size = 24
        self.is_elite = elite

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, dmg, particles):
        self.hp -= dmg
        for _ in range(6):
            ang = math.tau * (_ / 6.0)
            sp = 140
            vx = math.cos(ang) * sp
            vy = math.sin(ang) * sp
            particles.append(Particle(self.x, self.y, vx, vy, 0.25, self.color))

    def update(self, dt, player_pos, dungeon, enemy_bullets=None, rng=None, spawn_list=None):
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
        r = pygame.Rect(0, 0, self.size, self.size)
        r.center = (self.x - cam_x, self.y - cam_y)
        pygame.draw.rect(surf, self.color, r)
        if self.is_elite:
            pygame.draw.rect(surf, YELLOW, r, 2)

        # hp bar
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bw = self.size - 2
        bx = r.centerx - bw // 2
        by = r.top - 6
        pygame.draw.rect(surf, (40, 40, 40), (bx, by, bw, 4))
        pygame.draw.rect(surf, RED, (bx, by, int(bw * ratio), 4))

class RangedTurret(Enemy):
    # stationary turret that fires aimed shots
    def __init__(self, x, y, hp_mult=1.0, speed_mult=1.0, elite=False):
        super().__init__(x, y, hp_mult, speed_mult, elite)
        self.kind = "turret"
        self.color = ORANGE
        self.size = 22
        self.shoot_timer = 1.4

    def update(self, dt, player_pos, dungeon, enemy_bullets=None, rng=None, spawn_list=None):
        if not self.is_alive():
            return
        self.shoot_timer -= dt
        if enemy_bullets is None:
            return
        if self.shoot_timer <= 0:
            self.shoot_timer = 1.4 if not self.is_elite else 1.0
            px, py = player_pos
            dx = px - self.x
            dy = py - self.y
            ang = math.atan2(dy, dx)
            spread = 0.08 if not self.is_elite else 0.05
            for i in range(-1, 2):
                enemy_bullets.append(
                    Bullet(
                        self.x,
                        self.y,
                        ang + spread * i,
                        BOSS_PROJECTILE_SPEED * 0.8,
                        8 if not self.is_elite else 12,
                        ORANGE,
                    )
                )

    def draw(self, surf, cam_x, cam_y):
        if not self.is_alive():
            return
        r = pygame.Rect(0, 0, self.size, self.size)
        r.center = (self.x - cam_x, self.y - cam_y)
        pygame.draw.ellipse(surf, self.color, r)
        if self.is_elite:
            pygame.draw.ellipse(surf, YELLOW, r, 2)
        pygame.draw.circle(surf, RED, r.center, 4)

class DasherEnemy(Enemy):
    # bursts toward the player in quick dashes
    def __init__(self, x, y, hp_mult=1.0, speed_mult=1.0, elite=False):
        super().__init__(x, y, hp_mult, speed_mult, elite)
        self.kind = "dasher"
        self.color = CYAN
        self.size = 22
        self.dash_cooldown = 1.8
        self.dash_timer = 0.0
        self.dashing = False
        self.dash_dir = (0.0, 0.0)

    def update(self, dt, player_pos, dungeon, enemy_bullets=None, rng=None, spawn_list=None):
        if not self.is_alive():
            return

        self.dash_timer -= dt
        px, py = player_pos
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy) + 1e-6
        dir_x = dx / dist
        dir_y = dy / dist

        if self.dashing:
            speed = ENEMY_BASE_SPEED * self.speed_mult * 3.0
            new_x = self.x + dir_x * speed * dt
            new_y = self.y + dir_y * speed * dt
            if not dungeon.is_solid_world(new_x, self.y):
                self.x = new_x
            if not dungeon.is_solid_world(self.x, new_y):
                self.y = new_y
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.dashing = False
                self.dash_timer = self.dash_cooldown
            return

        if self.dash_timer <= 0:
            self.dashing = True
            self.dash_timer = 0.45 if not self.is_elite else 0.6
            return

        speed = ENEMY_BASE_SPEED * self.speed_mult * 0.7
        new_x = self.x + dir_x * speed * dt
        new_y = self.y + dir_y * speed * dt
        if not dungeon.is_solid_world(new_x, self.y):
            self.x = new_x
        if not dungeon.is_solid_world(self.x, new_y):
            self.y = new_y

    def draw(self, surf, cam_x, cam_y):
        super().draw(surf, cam_x, cam_y)
        if not self.is_alive():
            return
        cx = self.x - cam_x
        cy = self.y - cam_y
        if self.dashing:
            pygame.draw.circle(surf, CYAN, (int(cx), int(cy)), self.size)

class ShielderEnemy(Enemy):
    # absorbs damage with a regenerating shield
    def __init__(self, x, y, hp_mult=1.0, speed_mult=1.0, elite=False):
        super().__init__(x, y, hp_mult, speed_mult, elite)
        self.kind = "shielder"
        self.color = GREEN
        self.size = 26
        self.shield_hp = 35 * (1.4 if elite else 1.0)
        self.shield_cd = 0.0

    def take_damage(self, dmg, particles):
        if self.shield_hp > 0:
            absorbed = min(dmg, self.shield_hp)
            self.shield_hp -= absorbed
            dmg -= absorbed
            particles.append(Particle(self.x, self.y, 0, 0, 0.25, CYAN))
        if dmg > 0:
            super().take_damage(dmg, particles)

    def update(self, dt, player_pos, dungeon, enemy_bullets=None, rng=None, spawn_list=None):
        if not self.is_alive():
            return
        self.shield_cd = min(2.5, self.shield_cd + dt)
        if self.shield_cd >= 2.5 and self.shield_hp <= 0:
            self.shield_hp = 20 if not self.is_elite else 35
            self.shield_cd = 0.0

        super().update(dt, player_pos, dungeon, enemy_bullets, rng, spawn_list)

    def draw(self, surf, cam_x, cam_y):
        super().draw(surf, cam_x, cam_y)
        if not self.is_alive():
            return
        cx = self.x - cam_x
        cy = self.y - cam_y
        if self.shield_hp > 0:
            radius = int(self.size)
            color = CYAN if not self.is_elite else YELLOW
            pygame.draw.circle(surf, color, (int(cx), int(cy)), radius, 2)

class SummonerEnemy(Enemy):
    # periodically summons basic minions
    def __init__(self, x, y, hp_mult=1.0, speed_mult=1.0, elite=False):
        super().__init__(x, y, hp_mult, speed_mult, elite)
        self.kind = "summoner"
        self.color = (200, 120, 255)
        self.size = 26
        self.summon_timer = 5.0

    def update(self, dt, player_pos, dungeon, enemy_bullets=None, rng=None, spawn_list=None):
        if not self.is_alive():
            return
        self.summon_timer -= dt
        if self.summon_timer <= 0 and spawn_list is not None and rng is not None:
            self.summon_timer = 6.0 if not self.is_elite else 4.5
            px, py = player_pos
            offset_angle = rng.random() * math.tau
            distance_offset = 60 + (30 if self.is_elite else 0)
            sx = self.x + math.cos(offset_angle) * distance_offset
            sy = self.y + math.sin(offset_angle) * distance_offset
            spawn_list.append(
                Enemy(sx, sy, hp_mult=0.8 if not self.is_elite else 1.2, speed_mult=1.0 + 0.1 * rng.random())
            )
        # light hover movement
        px, py = player_pos
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy) + 1e-6
        dir_x = dx / dist
        dir_y = dy / dist
        offset = math.sin(self.phase * 2.0) * 0.4
        side_x = -dir_y * offset
        side_y = dir_x * offset
        speed = ENEMY_BASE_SPEED * self.speed_mult * 0.4
        new_x = self.x + (dir_x + side_x) * speed * dt
        new_y = self.y + (dir_y + side_y) * speed * dt
        if not dungeon.is_solid_world(new_x, self.y):
            self.x = new_x
        if not dungeon.is_solid_world(self.x, new_y):
            self.y = new_y
        self.phase += dt

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
        self.telegraphs = []
        self.laser_angle = 0.0
        self.wave_timer = 8.0
        self.laser_timer = 0.0

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

    def _spawn_telegraph(self, radius, delay, color):
        self.telegraphs.append({"r": radius, "timer": delay, "color": color})

    def update(self, dt, player_pos, dungeon, enemy_bullets, rng, spawn_list):
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

        hp_ratio = self.hp / max(1, self.max_hp)

        # update tells
        for t in list(self.telegraphs):
            t["timer"] -= dt
            if t["timer"] <= 0:
                for i in range(12):
                    ang = math.tau * (i / 12.0)
                    enemy_bullets.append(
                        Bullet(
                            self.x,
                            self.y,
                            ang,
                            BOSS_PROJECTILE_SPEED * 0.9,
                            12,
                            t["color"],
                        )
                    )
                self.telegraphs.remove(t)

        # phase logic
        self.shoot_timer -= dt
        if hp_ratio > 0.66:
            if self.shoot_timer <= 0:
                self.shoot_timer = 1.4
                base_angle = math.atan2(dy, dx)
                for i in range(-2, 3):
                    ang = base_angle + i * 0.25
                    enemy_bullets.append(Bullet(self.x, self.y, ang, BOSS_PROJECTILE_SPEED, 10, (255, 140, 140)))
        elif hp_ratio > 0.33:
            if self.shoot_timer <= 0:
                self.shoot_timer = 2.0
                self._spawn_telegraph(60, 1.0, YELLOW)
        else:
            if self.shoot_timer <= 0:
                self.shoot_timer = 1.6
                self._spawn_telegraph(80, 1.2, ORANGE)
            # rotating lasers
            self.laser_timer -= dt
            self.laser_angle += dt * 0.9
            if self.laser_timer <= 0:
                self.laser_timer = 0.25
                for offset_ang in (0, math.pi / 2, math.pi):
                    ang = self.laser_angle + offset_ang
                    enemy_bullets.append(
                        Bullet(
                            self.x,
                            self.y,
                            ang,
                            BOSS_PROJECTILE_SPEED * 1.2,
                            14,
                            (255, 200, 200),
                        )
                    )
            # minion waves
            self.wave_timer -= dt
            if self.wave_timer <= 0 and rng is not None and spawn_list is not None:
                self.wave_timer = 10.0
                for _ in range(3):
                    angle = rng.random() * math.tau
                    dist_offset = 80 + rng.randint(0, 40)
                    sx = self.x + math.cos(angle) * dist_offset
                    sy = self.y + math.sin(angle) * dist_offset
                    spawn_list.append(DasherEnemy(sx, sy, hp_mult=1.2, speed_mult=1.1))

    def draw(self, surf, cam_x, cam_y, screen_width):
        if not self.is_alive():
            return
        # telegraphs
        for t in self.telegraphs:
            alpha = clamp(t["timer"], 0, 1)
            color = (
                int(t["color"][0] * alpha),
                int(t["color"][1] * alpha),
                int(t["color"][2] * alpha),
            )
            pygame.draw.circle(
                surf,
                color,
                (int(self.x - cam_x), int(self.y - cam_y)),
                int(t["r"] * (1.1 - alpha)),
                2,
            )

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
