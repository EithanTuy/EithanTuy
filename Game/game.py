# game.py
# main game loop with seed input, speedrun timer, floors, and all systems wired together.
# all comments are lowercase.

import pygame
import sys
import math

from config import (
    WIDTH,
    HEIGHT,
    FPS,
    MAX_FLOORS,
    BIOMES,
    BLACK,
    WHITE,
    GRAY,
    DARK_GRAY,
    GREEN,
    CYAN,
    YELLOW,
    TILE_SIZE,
)
from utils import format_time, draw_text_center, distance
from seed import SeedRNG
from timer import RunTimer
from dungeon import Dungeon, BIOME_STYLES
from entities import Player, Enemy, Boss
from objects import Particle, Bullet, XpOrb, Portal

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("seeded dungeon speedrun")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("consolas", 20)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.big_font = pygame.font.SysFont("consolas", 40)

        self.state = "MENU"  # MENU, RUNNING, PAUSED, GAME_OVER, VICTORY
        self.seed_input = ""
        self.rng = None
        self.timer = RunTimer()

        self.floor = 1
        self.biome_name = "cavern"
        self.dungeon = None
        self.player = None

        self.enemies = []
        self.bullets = []
        self.boss_bullets = []
        self.particles = []
        self.xp_orbs = []
        self.portal = None
        self.boss = None
        self.interactables = []

        self.enemy_spawn_timer = 0.0
        self.enemy_spawn_interval = 3.0

        self.cam_x = 0.0
        self.cam_y = 0.0

        self.score = 0

    # ---------- setup ----------
    def start_run(self):
        # initialize rng from seed text
        self.rng = SeedRNG(self.seed_input)
        self.timer.reset()
        self.timer.start()
        self.floor = 1
        self.score = 0
        self._build_floor()
        self.state = "RUNNING"

    def _enemy_scalars(self):
        hp_mult = 1.0 + 0.35 * (self.floor - 1)
        speed_mult = 1.0 + 0.18 * (self.floor - 1)
        return hp_mult, speed_mult

    def _choose_enemy_class(self):
        pool = ENEMY_POOLS.get(self.biome_name, ENEMY_POOLS["cavern"])
        choices = [p for p in pool if self.floor >= p.get("min_floor", 1)]
        total = sum(p["weight"] * (1 + 0.12 * (self.floor - 1)) for p in choices)
        pick = self.rng.random() * total
        accum = 0.0
        for p in choices:
            accum += p["weight"] * (1 + 0.12 * (self.floor - 1))
            if pick <= accum:
                return p["cls"]
        return choices[-1]["cls"]

    def _spawn_enemy(self, elite=False):
        hp_mult, speed_mult = self._enemy_scalars()
        if elite:
            hp_mult *= 1.6
            speed_mult *= 1.1
        ex, ey = self.dungeon.random_floor_pos()
        cls = self._choose_enemy_class()
        enemy = cls(ex, ey, hp_mult=hp_mult, speed_mult=speed_mult, elite=elite)
        self.enemies.append(enemy)

    def _build_floor(self):
        # pick biome from rng
        self.biome_name = self.rng.choice(BIOMES)
        self.dungeon = Dungeon(self.rng, self.biome_name)
        self.interactables = list(self.dungeon.interactables)

        px, py = self.dungeon.random_floor_pos()
        if self.player is None:
            self.player = Player(px, py)
        else:
            # keep progression but move player to new pos
            self.player.x = px
            self.player.y = py

        self.enemies = []
        self.bullets = []
        self.enemy_bullets = []
        self.particles = []
        self.xp_orbs = []
        self.portal = None

        hp_mult = 1.0 + 0.35 * (self.floor - 1)
        speed_mult = 1.0 + 0.18 * (self.floor - 1)

        # spawn some starting enemies
        for _ in range(6 + self.floor * 2):
            self._spawn_enemy()

        # make boss for this floor
        bx, by = self.dungeon.random_floor_pos()
        self.boss = Boss(bx, by, hp_mult=hp_mult, speed_mult=speed_mult)

        self.enemy_spawn_interval = max(1.4, 3.0 - 0.2 * (self.floor - 1))
        self.enemy_spawn_timer = 1.0
        self.elite_spawn_timer = max(10.0, 18.0 - self.floor * 1.5)

    # ---------- event handling ----------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == "MENU":
                self._handle_menu_event(event)
            elif self.state == "RUNNING":
                self._handle_running_event(event)
            elif self.state == "PAUSED":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "RUNNING"
                    self.timer.start()
            elif self.state in ("GAME_OVER", "VICTORY"):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # restart new seed run
                        self.seed_input = ""
                        self.state = "MENU"
                    elif event.key == pygame.K_r:
                        # repeat same seed
                        self.state = "RUNNING"
                        self.start_run()

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_run()
            elif event.key == pygame.K_BACKSPACE:
                self.seed_input = self.seed_input[:-1]
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            else:
                ch = event.unicode
                if ch.isprintable() and len(self.seed_input) < 20:
                    self.seed_input += ch

    def _handle_running_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = "PAUSED"
                self.timer.stop()
            if event.key == pygame.K_1:
                self.player.switch_weapon(0)
            if event.key == pygame.K_2:
                self.player.switch_weapon(1)
            if event.key == pygame.K_3:
                self.player.switch_weapon(2)
            if event.key == pygame.K_e:
                self._interact_with_nearby()
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            world = (mx + self.cam_x, my + self.cam_y)
            if event.button == 1:
                # shoot
                if self.player.can_shoot(self.timer.get_time()):
                    self.player.shoot(world, self.bullets, self.timer.get_time(), self.particles)
            elif event.button == 3:
                # dash
                self.player.start_dash(world)

    # ---------- update ----------
    def update(self, dt):
        if self.state != "RUNNING":
            return

        self.timer.update(dt)

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.dungeon)
        self.player.check_auto_level()

        # camera follows player
        self.cam_x += ((self.player.x - WIDTH / 2) - self.cam_x) * 0.15
        self.cam_y += ((self.player.y - HEIGHT / 2) - self.cam_y) * 0.15

        # enemies
        spawned = []
        for e in self.enemies:
            e.update(dt, self.player.center(), self.dungeon, self.enemy_bullets, self.rng, spawned)
        if spawned:
            self.enemies.extend(spawned)

        # boss
        if self.boss is not None and self.boss.is_alive():
            self.boss.update(dt, self.player.center(), self.dungeon, self.enemy_bullets, self.rng, spawned)
            if spawned:
                self.enemies.extend(spawned)
        elif self.portal is None:
            # boss dead, spawn portal once
            self.portal = Portal(self.player.x, self.player.y - 40)

        # spawn new enemies periodically
        self.enemy_spawn_timer -= dt
        self.elite_spawn_timer -= dt
        if self.enemy_spawn_timer <= 0:
            self.enemy_spawn_timer = self.enemy_spawn_interval
            self._spawn_enemy()
        if self.elite_spawn_timer <= 0:
            self.elite_spawn_timer = max(12.0, 20.0 - self.floor * 2)
            self._spawn_enemy(elite=True)

        # bullets
        for b in list(self.bullets):
            b.update(dt, self.dungeon)
            if b.life <= 0:
                self.bullets.remove(b)

        for b in list(self.enemy_bullets):
            b.update(dt, self.dungeon)
            if b.life <= 0:
                self.enemy_bullets.remove(b)

        # xp orbs
        for orb in self.xp_orbs:
            orb.update(dt, self.player.center())

        # particles
        for p in list(self.particles):
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)

        # collisions: bullets vs enemies
        for b in list(self.bullets):
            hit_any = False
            for e in self.enemies:
                if e.is_alive() and distance((b.x, b.y), (e.x, e.y)) < 18:
                    e.take_damage(b.damage, self.particles)
                    hit_any = True
                    if not e.is_alive():
                        self.player.kills += 1
                        self.score += 10
                        self.player.add_xp(18 + 2 * self.floor)
                        self.xp_orbs.append(XpOrb(e.x, e.y, 12 + 2 * self.floor))
            if self.boss is not None and self.boss.is_alive():
                if distance((b.x, b.y), (self.boss.x, self.boss.y)) < 40:
                    self.boss.take_damage(b.damage, self.particles)
                    hit_any = True
                    if not self.boss.is_alive():
                        self.score += 200
                        self.player.add_xp(80 + 20 * self.floor)
            if hit_any and b in self.bullets:
                self.bullets.remove(b)

        # enemy contact damage
        for e in self.enemies:
            if e.is_alive() and distance(self.player.center(), (e.x, e.y)) < 20:
                self.player.hurt(25 * dt, self.particles)

        # boss bullet damage
        for b in self.boss_bullets:
            if distance(self.player.center(), (b.x, b.y)) < 18:
                self.player.hurt(40 * dt, self.particles)

        # hazard effects
        hazard = self.dungeon.hazard_at(self.player.x, self.player.y)
        if hazard:
            self._apply_hazard_effect(hazard, dt)

        # xp pickup
        for orb in list(self.xp_orbs):
            if distance(self.player.center(), (orb.x, orb.y)) < 18:
                self.player.add_xp(orb.value)
                self.xp_orbs.remove(orb)

        # portal usage
        if self.portal is not None:
            if self.portal.collides_with(self.player.center()):
                self.timer.split()
                if self.floor < MAX_FLOORS:
                    self.floor += 1
                    self._build_floor()
                else:
                    self.state = "VICTORY"
                    self.timer.stop()

        # death
        if self.player.hp <= 0:
            self.state = "GAME_OVER"
            self.timer.stop()

    # ---------- drawing ----------
    def draw(self):
        if self.state == "MENU":
            self._draw_menu()
        else:
            self._draw_world()

        pygame.display.flip()

    def _draw_menu(self):
        self.screen.fill(BLACK)
        draw_text_center(self.screen, self.big_font, "seeded dungeon speedrun", WHITE, HEIGHT // 3)
        draw_text_center(self.screen, self.font, "type a seed (or leave empty)", GRAY, HEIGHT // 3 + 60)
        draw_text_center(self.screen, self.font, "press enter to start", GRAY, HEIGHT // 3 + 90)

        seed_display = self.seed_input if self.seed_input else "<random>"
        draw_text_center(self.screen, self.font, f"seed: {seed_display}", CYAN, HEIGHT // 3 + 130)

    def _draw_world(self):
        # fill background
        style = BIOME_STYLES.get(self.biome_name, BIOME_STYLES["cavern"])
        base_col = style["floor"]
        self.screen.fill(base_col)

        # draw dungeon tiles
        self.dungeon.draw(self.screen, self.cam_x, self.cam_y)

        # highlight nearby interactables
        for obj in self.interactables:
            if obj.is_active() and distance(self.player.center(), (obj.x, obj.y)) < 70:
                self._draw_interact_prompt(obj)

        # draw orbs
        for orb in self.xp_orbs:
            orb.draw(self.screen, self.cam_x, self.cam_y)

        # draw bullets
        for b in self.bullets:
            b.draw(self.screen, self.cam_x, self.cam_y)
        for b in self.enemy_bullets:
            b.draw(self.screen, self.cam_x, self.cam_y)

        # draw enemies and boss
        for e in self.enemies:
            e.draw(self.screen, self.cam_x, self.cam_y)

        if self.boss is not None and self.boss.is_alive():
            self.boss.draw(self.screen, self.cam_x, self.cam_y, WIDTH)

        # draw particles
        for p in self.particles:
            p.draw(self.screen, self.cam_x, self.cam_y)

        # draw portal
        if self.portal is not None:
            self.portal.draw(self.screen, self.cam_x, self.cam_y, self.timer.get_time())

        # draw player
        self.player.draw(self.screen, self.cam_x, self.cam_y, pygame.mouse.get_pos())

        # lighting overlay
        light = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        light.fill((0, 0, 0, 220))
        px = self.player.x - self.cam_x
        py = self.player.y - self.cam_y
        light_radius = style["light_radius"]
        pygame.draw.circle(light, (0, 0, 0, 0), (int(px), int(py)), light_radius)
        self.screen.blit(light, (0, 0))

        # hud
        self._draw_hud()

        if self.state == "PAUSED":
            self._draw_pause()
        elif self.state == "GAME_OVER":
            self._draw_death()
        elif self.state == "VICTORY":
            self._draw_victory()

    def _draw_hud(self):
        # hp / energy / xp bars and time
        x = 16
        y = HEIGHT - 26

        # hp
        bar_w = 260
        bar_h = 16

        pygame.draw.rect(self.screen, DARK_GRAY, (x - 2, y - 2, bar_w + 4, bar_h + 4))
        hp_ratio = self.player.hp / self.player.max_hp
        pygame.draw.rect(self.screen, (200, 60, 60), (x, y, int(bar_w * hp_ratio), bar_h))
        txt = self.font.render(f"hp {int(self.player.hp)}/{self.player.max_hp}", True, WHITE)
        self.screen.blit(txt, (x, y - 24))

        # energy
        y -= 40
        pygame.draw.rect(self.screen, DARK_GRAY, (x - 2, y - 2, bar_w + 4, bar_h + 4))
        en_ratio = self.player.energy / self.player.max_energy
        pygame.draw.rect(self.screen, CYAN, (x, y, int(bar_w * en_ratio), bar_h))
        txt = self.font.render(f"energy {int(self.player.energy)}/{self.player.max_energy}", True, WHITE)
        self.screen.blit(txt, (x, y - 24))

        # xp
        y -= 40
        pygame.draw.rect(self.screen, DARK_GRAY, (x - 2, y - 2, bar_w + 4, bar_h + 4))
        xp_ratio = self.player.xp / max(1, self.player.xp_to_next)
        pygame.draw.rect(self.screen, GREEN, (x, y, int(bar_w * xp_ratio), bar_h))
        txt = self.font.render(f"lvl {self.player.level}", True, WHITE)
        self.screen.blit(txt, (x, y - 24))

        # time + floor + score
        time_text = self.font.render(f"time {format_time(self.timer.get_time())}", True, YELLOW)
        self.screen.blit(time_text, (WIDTH - 230, HEIGHT - 32))

        info = self.small_font.render(
            f"floor {self.floor}/{MAX_FLOORS}  score {self.score}  kills {self.player.kills}",
            True,
            WHITE,
        )
        self.screen.blit(info, (16, 16))

        # weapons
        wnames = sorted(list(self.player.unlocked_weapons))
        wx = WIDTH - 260
        wy = HEIGHT - 110
        pygame.draw.rect(self.screen, (15, 15, 15), (wx, wy, 240, 80))
        pygame.draw.rect(self.screen, GRAY, (wx, wy, 240, 80), 2)
        label = self.small_font.render("weapons 1-3", True, WHITE)
        self.screen.blit(label, (wx + 10, wy + 6))

        for i, name in enumerate(wnames[:3]):
            active = (name == self.player.current_weapon)
            col = CYAN if active else GRAY
            wt = self.small_font.render(f"{i+1}: {name}", True, col)
            self.screen.blit(wt, (wx + 10 + i * 70, wy + 28))

        # minimap
        self.dungeon.draw_minimap(self.screen, self.player.center(), self.floor, self.rng.seed_string)

    def _interact_with_nearby(self):
        best = None
        best_d = 9999
        for obj in self.interactables:
            if not obj.is_active():
                continue
            d = distance(self.player.center(), (obj.x, obj.y))
            if d < 70 and d < best_d:
                best_d = d
                best = obj
        if best is not None:
            best.interact(self.player, self.particles, self.rng)

    def _apply_hazard_effect(self, hazard, dt):
        htype = hazard.get("type")
        if htype == "lava":
            self.player.hurt(30 * dt, self.particles)
        elif htype == "ice":
            dx, dy = self.player.last_move_dir
            slip_speed = 90
            new_x = self.player.x + dx * slip_speed * dt
            new_y = self.player.y + dy * slip_speed * dt
            if not self.dungeon.is_solid_world(new_x, self.player.y):
                self.player.x = new_x
            if not self.dungeon.is_solid_world(self.player.x, new_y):
                self.player.y = new_y
        elif htype == "curse":
            self.player.hurt(18 * dt, self.particles)
            self.player.energy = max(0, self.player.energy - 10 * dt)
        elif htype == "conveyor":
            dir_x, dir_y = hazard.get("dir", (0, 0))
            push = 130
            new_x = self.player.x + dir_x * push * dt
            new_y = self.player.y + dir_y * push * dt
            if not self.dungeon.is_solid_world(new_x, self.player.y):
                self.player.x = new_x
            if not self.dungeon.is_solid_world(self.player.x, new_y):
                self.player.y = new_y

    def _draw_interact_prompt(self, obj):
        hint_font = pygame.font.SysFont("consolas", 14)
        text = hint_font.render("E", True, YELLOW)
        bx = obj.x - self.cam_x - text.get_width() // 2
        by = obj.y - self.cam_y - TILE_SIZE * 0.5
        self.screen.blit(text, (bx, by))

    def _draw_pause(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        draw_text_center(self.screen, self.big_font, "paused", WHITE, HEIGHT // 2 - 20)
        draw_text_center(self.screen, self.small_font, "press esc to resume", GRAY, HEIGHT // 2 + 20)

    def _draw_death(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        draw_text_center(self.screen, self.big_font, "you died", (255, 80, 80), HEIGHT // 3)
        draw_text_center(
            self.screen,
            self.font,
            f"time {format_time(self.timer.get_time())}   floor {self.floor}   score {self.score}",
            WHITE,
            HEIGHT // 3 + 60,
        )
        draw_text_center(
            self.screen,
            self.small_font,
            "enter = new seed   r = retry same seed",
            GRAY,
            HEIGHT // 3 + 100,
        )

    def _draw_victory(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))
        draw_text_center(self.screen, self.big_font, "victory", (120, 255, 120), HEIGHT // 3)
        draw_text_center(
            self.screen,
            self.font,
            f"final time {format_time(self.timer.get_time())}   score {self.score}",
            GRAY,
            HEIGHT // 3 + 60,
        )

        # splits per floor
        y = HEIGHT // 3 + 100
        for i, t in enumerate(self.timer.splits, start=1):
            txt = self.small_font.render(f"floor {i} split: {format_time(t)}", True, GRAY)
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, y))
            y += 20

        draw_text_center(
            self.screen,
            self.small_font,
            "enter = new seed   r = retry same seed",
            GRAY,
            y + 20,
        )

    # ---------- main loop ----------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

if __name__ == "__main__":
    Game().run()
