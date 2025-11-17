# dungeon.py
# procedural dungeon generation with biomes. all comments are lowercase.

import pygame

from config import TILE_SIZE, MAP_W, MAP_H
from config import BLACK, DARK_GRAY, GREEN, BLUE, RED, ORANGE, PURPLE
from utils import clamp

# biome visual settings
BIOME_STYLES = {
    "cavern": {
        "floor": (15, 15, 18),
        "wall": (30, 30, 40),
        "accent": (40, 40, 60),
        "light_radius": 170,
    },
    "ice": {
        "floor": (15, 20, 30),
        "wall": (40, 60, 90),
        "accent": (70, 110, 150),
        "light_radius": 190,
    },
    "crypt": {
        "floor": (10, 10, 12),
        "wall": (30, 30, 35),
        "accent": (50, 50, 60),
        "light_radius": 140,
    },
    "magma": {
        "floor": (25, 12, 8),
        "wall": (55, 18, 8),
        "accent": (90, 40, 10),
        "light_radius": 180,
    },
    "machine": {
        "floor": (12, 12, 16),
        "wall": (30, 35, 40),
        "accent": (80, 80, 90),
        "light_radius": 160,
    },
}

class Tile:
    # single tile, may be wall, floor, or hazard
    def __init__(self, solid=True, hazard=False):
        self.solid = solid
        self.hazard = hazard

class Dungeon:
    # holds tilemap and biome data
    def __init__(self, rng, biome_name):
        self.w = MAP_W
        self.h = MAP_H
        self.rng = rng
        self.biome_name = biome_name
        self.tiles = [[Tile(True) for _ in range(self.h)] for _ in range(self.w)]
        self.generate()

    def generate(self):
        # random walk style generator
        x = self.w // 2
        y = self.h // 2
        steps = self.w * self.h * 7

        for _ in range(steps):
            self.tiles[x][y].solid = False
            # carve small rooms sometimes
            if self.rng.random() < 0.3:
                self._carve_room(x, y)

            dx, dy = self.rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            x = clamp(x + dx, 1, self.w - 2)
            y = clamp(y + dy, 1, self.h - 2)

        # add some hazards for magma biome
        if self.biome_name == "magma":
            self._add_hazards(prob=0.03)

    def _carve_room(self, cx, cy):
        # carves a small rectangular room around a center
        rw = self.rng.randint(3, 7)
        rh = self.rng.randint(3, 7)
        for x in range(cx - rw // 2, cx + rw // 2 + 1):
            for y in range(cy - rh // 2, cy + rh // 2 + 1):
                if 1 <= x < self.w - 1 and 1 <= y < self.h - 1:
                    self.tiles[x][y].solid = False

    def _add_hazards(self, prob=0.02):
        # marks some floor tiles as hazard (lava)
        for x in range(2, self.w - 2):
            for y in range(2, self.h - 2):
                t = self.tiles[x][y]
                if not t.solid and self.rng.random() < prob:
                    t.hazard = True

    def is_solid_world(self, wx, wy):
        # checks if world pos is solid
        tx = int(wx // TILE_SIZE)
        ty = int(wy // TILE_SIZE)
        if 0 <= tx < self.w and 0 <= ty < self.h:
            return self.tiles[tx][ty].solid
        return True

    def is_hazard_world(self, wx, wy):
        # checks if world pos is hazard
        tx = int(wx // TILE_SIZE)
        ty = int(wy // TILE_SIZE)
        if 0 <= tx < self.w and 0 <= ty < self.h:
            t = self.tiles[tx][ty]
            return (not t.solid) and t.hazard
        return False

    def random_floor_pos(self):
        # picks random non-solid tile center
        while True:
            x = self.rng.randint(1, self.w - 2)
            y = self.rng.randint(1, self.h - 2)
            if not self.tiles[x][y].solid:
                return x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2

    def draw(self, surf, cam_x, cam_y):
        # draws region around camera
        style = BIOME_STYLES[self.biome_name]
        floor_col = style["floor"]
        wall_col = style["wall"]
        accent_col = style["accent"]

        start_tx = int(cam_x // TILE_SIZE) - 1
        start_ty = int(cam_y // TILE_SIZE) - 1
        end_tx = int((cam_x + surf.get_width()) // TILE_SIZE) + 2
        end_ty = int((cam_y + surf.get_height()) // TILE_SIZE) + 2

        for tx in range(start_tx, end_tx):
            for ty in range(start_ty, end_ty):
                if 0 <= tx < self.w and 0 <= ty < self.h:
                    tile = self.tiles[tx][ty]
                    world_x = tx * TILE_SIZE
                    world_y = ty * TILE_SIZE
                    rect = pygame.Rect(
                        world_x - cam_x,
                        world_y - cam_y,
                        TILE_SIZE,
                        TILE_SIZE,
                    )
                    if tile.solid:
                        pygame.draw.rect(surf, wall_col, rect)
                    else:
                        pygame.draw.rect(surf, floor_col, rect)
                        # random accent pattern
                        if (tx + ty) % 7 == 0:
                            pygame.draw.circle(
                                surf,
                                accent_col,
                                rect.center,
                                TILE_SIZE // 4,
                            )
                        if tile.hazard:
                            pygame.draw.rect(surf, ORANGE, rect.inflate(-8, -8))

    def draw_minimap(self, surf, player_pos, floor_index, seed_string):
        # tiny minimap in top right
        mm_w, mm_h = 200, 150
        scale_x = mm_w / self.w
        scale_y = mm_h / self.h

        mm = pygame.Surface((mm_w, mm_h))
        mm.fill(BLACK)

        for x in range(self.w):
            for y in range(self.h):
                t = self.tiles[x][y]
                if not t.solid:
                    col = (70, 70, 70)
                    if t.hazard:
                        col = ORANGE
                    mm.set_at((int(x * scale_x), int(y * scale_y)), col)

        px = int(player_pos[0] / TILE_SIZE * scale_x)
        py = int(player_pos[1] / TILE_SIZE * scale_y)
        if 0 <= px < mm_w and 0 <= py < mm_h:
            pygame.draw.circle(mm, GREEN, (px, py), 3)

        surf.blit(mm, (surf.get_width() - mm_w - 16, 16))

        # floor + seed label
        font = pygame.font.SysFont("consolas", 14)
        txt = font.render(f"floor {floor_index}", True, WHITE)
        surf.blit(txt, (surf.get_width() - mm_w - 16, 16 + mm_h + 4))
        txt2 = font.render(f"seed {seed_string}", True, (160, 160, 160))
        surf.blit(txt2, (surf.get_width() - mm_w - 16, 16 + mm_h + 22))
