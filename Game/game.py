import json
import math
import os
import array
from dataclasses import dataclass

import pygame

# screen + physics constants
WIDTH, HEIGHT = 1000, 600
FPS = 60
GRAVITY = 0.6
MOVE_SPEED = 5.2
JUMP_SPEED = -12.5
PLAYER_W, PLAYER_H = 34, 46
MAX_LEVEL_TIME = 90  # seconds

DATA_PATH = os.path.join(os.path.dirname(__file__), "highscores.json")


@dataclass
class Platform:
    rect: pygame.Rect
    moving: bool = False
    axis: str = "x"
    min_pos: int = 0
    max_pos: int = 0
    speed: float = 0
    direction: int = 1

    def update(self):
        if not self.moving:
            return 0, 0
        dx = dy = 0
        if self.axis == "x":
            dx = self.speed * self.direction
            self.rect.x += int(dx)
            if self.rect.x < self.min_pos or self.rect.x > self.max_pos:
                self.direction *= -1
                self.rect.x = max(self.min_pos, min(self.rect.x, self.max_pos))
        else:
            dy = self.speed * self.direction
            self.rect.y += int(dy)
            if self.rect.y < self.min_pos or self.rect.y > self.max_pos:
                self.direction *= -1
                self.rect.y = max(self.min_pos, min(self.rect.y, self.max_pos))
        return dx, dy


@dataclass
class Spike:
    rect: pygame.Rect


@dataclass
class Enemy:
    rect: pygame.Rect
    left_bound: int
    right_bound: int
    speed: int = 2
    direction: int = 1

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.left <= self.left_bound or self.rect.right >= self.right_bound:
            self.direction *= -1


class Player:
    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(x, y, PLAYER_W, PLAYER_H)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.last_checkpoint = (x, y)

    def handle_input(self, keys):
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -MOVE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = MOVE_SPEED

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_SPEED
            self.on_ground = False

    def apply_gravity(self):
        self.vel_y += GRAVITY
        self.vel_y = min(self.vel_y, 14)


def build_levels():
    return [
        {
            "name": "Level 1 - Starter Sprint",
            "start": (80, 450),
            "finish": pygame.Rect(930, 380, 28, 95),
            "checkpoint": pygame.Rect(470, 420, 28, 55),
            "platforms": [
                Platform(pygame.Rect(0, 520, 1000, 80)),
                Platform(pygame.Rect(150, 460, 130, 20)),
                Platform(pygame.Rect(320, 420, 130, 20)),
                Platform(pygame.Rect(520, 390, 120, 20), True, "x", 500, 760, 2),
                Platform(pygame.Rect(790, 430, 100, 20)),
            ],
            "spikes": [
                Spike(pygame.Rect(250, 500, 60, 20)),
                Spike(pygame.Rect(640, 500, 70, 20)),
            ],
            "pits": [pygame.Rect(710, 520, 60, 80)],
            "enemies": [Enemy(pygame.Rect(560, 362, 28, 28), 520, 760)],
        },
        {
            "name": "Level 2 - Flow Route",
            "start": (60, 450),
            "finish": pygame.Rect(930, 180, 28, 110),
            "checkpoint": pygame.Rect(520, 360, 28, 55),
            "platforms": [
                Platform(pygame.Rect(0, 520, 1000, 80)),
                Platform(pygame.Rect(120, 450, 100, 20)),
                Platform(pygame.Rect(260, 390, 110, 20)),
                Platform(pygame.Rect(420, 330, 110, 20), True, "y", 250, 420, 2),
                Platform(pygame.Rect(600, 270, 120, 20)),
                Platform(pygame.Rect(760, 220, 110, 20), True, "x", 680, 860, 2),
            ],
            "spikes": [
                Spike(pygame.Rect(190, 500, 70, 20)),
                Spike(pygame.Rect(350, 500, 80, 20)),
                Spike(pygame.Rect(700, 500, 90, 20)),
            ],
            "pits": [pygame.Rect(860, 520, 90, 80)],
            "enemies": [Enemy(pygame.Rect(620, 242, 28, 28), 600, 720)],
        },
    ]


def load_best_times():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_best_times(times):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(times, f, indent=2)


def format_time(seconds: float):
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02}:{s:05.2f}"


def tone(freq=440, ms=100, volume=0.4, sample_rate=44100):
    n = int(sample_rate * (ms / 1000.0))
    buf = array.array("h")
    amp = int(32767 * volume)
    for i in range(n):
        t = i / sample_rate
        buf.append(int(amp * math.sin(2 * math.pi * freq * t)))
    return pygame.mixer.Sound(buffer=buf)


class PlatformerGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Speedrun Platformer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 24)
        self.small = pygame.font.SysFont("consolas", 18)

        self.snd_jump = tone(620, 70)
        self.snd_finish = tone(900, 220)
        self.snd_checkpoint = tone(780, 120)

        self.levels = build_levels()
        self.best_times = load_best_times()
        self.state = "menu"  # menu, running, paused, level_end, game_end
        self.level_index = 0
        self.time_left = MAX_LEVEL_TIME
        self.level_start_ms = 0
        self.finish_time = None
        self.checkpoint_msg_timer = 0
        self.checkpoint_hit = False
        self.player = None

    def reset_level(self, index):
        self.level_index = index
        level = self.levels[self.level_index]
        self.player = Player(*level["start"])
        self.time_left = MAX_LEVEL_TIME
        self.level_start_ms = pygame.time.get_ticks()
        self.finish_time = None
        self.checkpoint_msg_timer = 0
        self.checkpoint_hit = False

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_event(event)

            if self.state == "running":
                self.update(dt)
            self.draw()
        pygame.quit()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.state == "menu":
            if event.key == pygame.K_RETURN:
                self.reset_level(0)
                self.state = "running"
            elif event.key == pygame.K_q:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

        elif self.state == "running":
            if event.key == pygame.K_SPACE:
                self.player.jump()
                self.snd_jump.play()
            elif event.key == pygame.K_p:
                self.state = "paused"

        elif self.state == "paused":
            if event.key == pygame.K_p:
                self.state = "running"
                self.level_start_ms = pygame.time.get_ticks() - int((MAX_LEVEL_TIME - self.time_left) * 1000)

        elif self.state == "level_end":
            if event.key == pygame.K_r:
                self.reset_level(self.level_index)
                self.state = "running"
            elif event.key == pygame.K_n and self.level_index + 1 < len(self.levels):
                self.reset_level(self.level_index + 1)
                self.state = "running"
            elif event.key == pygame.K_n:
                self.state = "game_end"

        elif self.state == "game_end":
            if event.key == pygame.K_RETURN:
                self.state = "menu"

    def update(self, dt):
        level = self.levels[self.level_index]
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)

        elapsed = (pygame.time.get_ticks() - self.level_start_ms) / 1000
        self.time_left = max(0, MAX_LEVEL_TIME - elapsed)

        if self.time_left <= 0:
            self.respawn()
            self.time_left = MAX_LEVEL_TIME
            self.level_start_ms = pygame.time.get_ticks()

        prev_rect = self.player.rect.copy()

        self.player.rect.x += int(self.player.vel_x)
        for platform in level["platforms"]:
            if self.player.rect.colliderect(platform.rect):
                if self.player.vel_x > 0:
                    self.player.rect.right = platform.rect.left
                elif self.player.vel_x < 0:
                    self.player.rect.left = platform.rect.right

        self.player.apply_gravity()
        self.player.rect.y += int(self.player.vel_y)
        self.player.on_ground = False

        for platform in level["platforms"]:
            dx, dy = platform.update()
            if self.player.rect.colliderect(platform.rect):
                if prev_rect.bottom <= platform.rect.top and self.player.vel_y >= 0:
                    self.player.rect.bottom = platform.rect.top
                    self.player.vel_y = 0
                    self.player.on_ground = True
                    if platform.moving:
                        self.player.rect.x += int(dx)
                        self.player.rect.y += int(dy)
                elif prev_rect.top >= platform.rect.bottom and self.player.vel_y < 0:
                    self.player.rect.top = platform.rect.bottom
                    self.player.vel_y = 0

        for enemy in level["enemies"]:
            enemy.update()
            if self.player.rect.colliderect(enemy.rect):
                self.respawn()
                return

        for spike in level["spikes"]:
            if self.player.rect.colliderect(spike.rect):
                self.respawn()
                return

        for pit in level["pits"]:
            if self.player.rect.colliderect(pit):
                self.respawn()
                return

        if self.player.rect.top > HEIGHT + 100:
            self.respawn()
            return

        checkpoint = level["checkpoint"]
        if not self.checkpoint_hit and self.player.rect.colliderect(checkpoint):
            self.player.last_checkpoint = (checkpoint.x, checkpoint.y - PLAYER_H)
            self.checkpoint_hit = True
            self.checkpoint_msg_timer = 2.0
            self.snd_checkpoint.play()

        if self.checkpoint_msg_timer > 0:
            self.checkpoint_msg_timer -= dt

        if self.player.rect.colliderect(level["finish"]):
            self.finish_time = MAX_LEVEL_TIME - self.time_left
            key = f"level_{self.level_index + 1}"
            best = self.best_times.get(key)
            if best is None or self.finish_time < best:
                self.best_times[key] = self.finish_time
                save_best_times(self.best_times)
            self.snd_finish.play()
            self.state = "level_end"

    def respawn(self):
        self.player.rect.topleft = self.player.last_checkpoint
        self.player.vel_x = 0
        self.player.vel_y = 0

    def draw(self):
        self.screen.fill((145, 200, 255))

        if self.state == "menu":
            self.draw_menu()
        elif self.state in ("running", "paused", "level_end", "game_end"):
            self.draw_level()
            if self.state == "paused":
                self.draw_center_msg("Paused - Press P to Resume")
            elif self.state == "level_end":
                self.draw_level_end()
            elif self.state == "game_end":
                self.draw_game_end()

        pygame.display.flip()

    def draw_menu(self):
        title = self.font.render("2D Speedrun Platformer", True, (15, 20, 30))
        hint = self.small.render("Enter: Start    Q: Quit", True, (20, 30, 40))
        ctrl = self.small.render("Move: A/D or Arrow Keys, Jump: Space, Pause: P", True, (20, 30, 40))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 220))
        self.screen.blit(ctrl, (WIDTH // 2 - ctrl.get_width() // 2, 270))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 310))

    def draw_level(self):
        level = self.levels[self.level_index]

        pygame.draw.rect(self.screen, (30, 140, 45), (0, 520, WIDTH, 80))

        for platform in level["platforms"]:
            pygame.draw.rect(self.screen, (80, 80, 85), platform.rect)

        for spike in level["spikes"]:
            pygame.draw.rect(self.screen, (180, 30, 30), spike.rect)

        for pit in level["pits"]:
            pygame.draw.rect(self.screen, (30, 30, 35), pit)

        for enemy in level["enemies"]:
            pygame.draw.rect(self.screen, (170, 50, 210), enemy.rect)

        cp = level["checkpoint"]
        pygame.draw.rect(self.screen, (240, 215, 70), cp, 3)

        finish = level["finish"]
        pygame.draw.rect(self.screen, (35, 30, 30), (finish.x + 10, finish.y, 4, finish.h))
        pygame.draw.polygon(
            self.screen,
            (255, 60, 60),
            [(finish.x + 14, finish.y), (finish.x + 42, finish.y + 12), (finish.x + 14, finish.y + 24)],
        )

        pygame.draw.rect(self.screen, (25, 90, 220), self.player.rect)

        timer_t = self.font.render(f"Time Left: {self.time_left:05.2f}", True, (20, 20, 20))
        level_t = self.small.render(level["name"], True, (20, 20, 20))
        self.screen.blit(timer_t, (20, 15))
        self.screen.blit(level_t, (20, 45))

        key = f"level_{self.level_index + 1}"
        best = self.best_times.get(key)
        best_text = "--" if best is None else format_time(best)
        best_t = self.small.render(f"Best: {best_text}", True, (20, 20, 20))
        self.screen.blit(best_t, (820, 15))

        if self.checkpoint_msg_timer > 0:
            msg = self.font.render("Checkpoint Reached!", True, (255, 255, 255))
            self.screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 80))

    def draw_center_msg(self, text):
        surf = self.font.render(text, True, (255, 255, 255))
        bg = pygame.Surface((surf.get_width() + 30, surf.get_height() + 20), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 130))
        self.screen.blit(bg, (WIDTH // 2 - bg.get_width() // 2, HEIGHT // 2 - bg.get_height() // 2))
        self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - surf.get_height() // 2))

    def draw_level_end(self):
        level_no = self.level_index + 1
        msg = f"Level {level_no} complete in {format_time(self.finish_time)}"
        next_hint = "N: next level" if level_no < len(self.levels) else "N: final results"
        lines = [msg, "R: retry level", next_hint]
        self.draw_overlay(lines)

    def draw_game_end(self):
        lines = ["Run complete! Best Times:"]
        for i in range(len(self.levels)):
            key = f"level_{i + 1}"
            best = self.best_times.get(key)
            lines.append(f"Level {i + 1}: {'--' if best is None else format_time(best)}")
        lines.append("Press Enter for Menu")
        self.draw_overlay(lines)

    def draw_overlay(self, lines):
        box = pygame.Surface((640, 260), pygame.SRCALPHA)
        box.fill((0, 0, 0, 165))
        self.screen.blit(box, (WIDTH // 2 - 320, HEIGHT // 2 - 130))
        for i, line in enumerate(lines):
            surf = self.small.render(line, True, (255, 255, 255))
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - 95 + i * 34))


if __name__ == "__main__":
    PlatformerGame().run()
