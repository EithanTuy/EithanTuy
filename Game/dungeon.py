# dungeon.py
# procedural dungeon generation with biomes. all comments are lowercase.

import pygame

from config import TILE_SIZE, MAP_W, MAP_H, BIOME_FEATURES
from config import BLACK, DARK_GRAY, GREEN, BLUE, RED, ORANGE, PURPLE, CYAN, WHITE
from objects import Interactable, INTERACTABLE_MINIMAP
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

# hazard visuals + minimap colors
HAZARD_INFO = {
    "lava": {"color": ORANGE, "minimap": ORANGE},
    "ice": {"color": BLUE, "minimap": CYAN},
    "curse": {"color": PURPLE, "minimap": PURPLE},
    "conveyor": {"color": (120, 200, 200), "minimap": CYAN},
}

class Tile:
    # single tile, may be wall, floor, or hazard
    def __init__(self, solid=True, hazard_type=None, hazard_dir=(0, 0)):
        self.solid = solid
        self.hazard_type = hazard_type
        self.hazard_dir = hazard_dir

    @property
    def hazard(self):
        return self.hazard_type is not None

class Dungeon:
    # holds tilemap and biome data
    def __init__(self, rng, biome_name):
        self.w = MAP_W
        self.h = MAP_H
        self.rng = rng
        self.biome_name = biome_name
        self.tiles = [[Tile(True) for _ in range(self.h)] for _ in range(self.w)]
        self.room_centers = []
        self.interactables = []
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
                self.room_centers.append((x, y))

            dx, dy = self.rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            x = clamp(x + dx, 1, self.w - 2)
            y = clamp(y + dy, 1, self.h - 2)

        self._apply_biome_features()

    def _carve_room(self, cx, cy):
        # carves a small rectangular room around a center
        rw = self.rng.randint(3, 7)
        rh = self.rng.randint(3, 7)
        for x in range(cx - rw // 2, cx + rw // 2 + 1):
            for y in range(cy - rh // 2, cy + rh // 2 + 1):
                if 1 <= x < self.w - 1 and 1 <= y < self.h - 1:
                    self.tiles[x][y].solid = False

    def _apply_biome_features(self):
        features = BIOME_FEATURES.get(self.biome_name, BIOME_FEATURES["cavern"])
        for hazard_cfg in features.get("hazards", []):
            self._add_hazards(hazard_cfg)

        self._place_templates(features)

    def _add_hazards(self, cfg):
        # marks some floor tiles as hazard using biome config
        prob = cfg.get("prob", 0.02)
        htype = cfg.get("type", "lava")
        dirs = cfg.get("dirs")
        for x in range(2, self.w - 2):
            for y in range(2, self.h - 2):
                t = self.tiles[x][y]
                if not t.solid and self.rng.random() < prob:
                    hdir = self.rng.choice(dirs) if dirs else (0, 0)
                    self._set_hazard(x, y, htype, hdir)

    def _set_hazard(self, x, y, hazard_type, hazard_dir=(0, 0)):
        t = self.tiles[x][y]
        if t.solid:
            return
        t.hazard_type = hazard_type
        t.hazard_dir = hazard_dir

    def _place_templates(self, features):
        if not self.room_centers:
            return
        templates = features.get("templates", {"treasure": 1})
        object_probs = features.get("objects", {})
        used = set()
        count = max(2, min(6, len(self.room_centers) // 2))
        centers = self.rng.sample(self.room_centers, k=min(count, len(self.room_centers)))
        for cx, cy in centers:
            template = self._weighted_choice(templates)
            if template == "treasure":
                self._decorate_treasure(cx, cy, object_probs)
            elif template == "shrine":
                self._decorate_shrine(cx, cy, object_probs)
            elif template == "trap":
                self._decorate_trap(cx, cy, features)
            used.add((cx, cy))
        self._scatter_interactables(features, used)

    def _decorate_treasure(self, cx, cy, object_probs):
        # 2-3 chests clustered together
        self._carve_room(cx, cy)
        count = self.rng.randint(2, 3)
        for i in range(count):
            offset = self.rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)])
            ox = clamp(cx + offset[0] * 2, 1, self.w - 2)
            oy = clamp(cy + offset[1] * 2, 1, self.h - 2)
            self._place_interactable("chest", ox, oy, object_probs)

    def _decorate_shrine(self, cx, cy, object_probs):
        self._carve_room(cx, cy)
        self._place_interactable("altar", cx, cy, object_probs, force=True)
        # flanking lanterns (objects) to guide player
        for dx, dy in [(-2, 0), (2, 0)]:
            self._place_interactable("chest", cx + dx, cy + dy, object_probs, allow_hazard=False)

    def _decorate_trap(self, cx, cy, features):
        self._carve_room(cx, cy)
        hazard_choice = features.get("hazards", [{}])
        if hazard_choice:
            cfg = self.rng.choice(hazard_choice)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    tx = clamp(cx + dx, 1, self.w - 2)
                    ty = clamp(cy + dy, 1, self.h - 2)
                    if abs(dx) == 2 or abs(dy) == 2:
                        hdir = self.rng.choice(cfg.get("dirs", [(0, 0)]))
                        self._set_hazard(tx, ty, cfg.get("type", "lava"), hdir)
        self._place_interactable("chest", cx, cy, features.get("objects", {}), force=True)

    def _scatter_interactables(self, features, used=None):
        if used is None:
            used = set()
        object_probs = features.get("objects", {})
        for cx, cy in self.room_centers:
            if (cx, cy) in used:
                continue
            if not object_probs:
                continue
            choice = self._weighted_choice(object_probs)
            if self.rng.random() < object_probs.get(choice, 0):
                self._place_interactable(choice, cx, cy, object_probs)

    def _place_interactable(self, kind, tx, ty, object_probs, force=False, allow_hazard=True):
        if not force and self.rng.random() > object_probs.get(kind, 0):
            return
        if not (0 <= tx < self.w and 0 <= ty < self.h):
            return
        tile = self.tiles[tx][ty]
        if tile.solid or (tile.hazard and not allow_hazard):
            return
        wx = tx * TILE_SIZE + TILE_SIZE / 2
        wy = ty * TILE_SIZE + TILE_SIZE / 2
        self.interactables.append(Interactable(kind, wx, wy))

    def _weighted_choice(self, weights):
        total = sum(weights.values())
        if total <= 0:
            return self.rng.choice(list(weights.keys()))
        r = self.rng.random() * total
        upto = 0
        for key, value in weights.items():
            upto += value
            if r <= upto:
                return key
        return list(weights.keys())[0]

    def is_solid_world(self, wx, wy):
        # checks if world pos is solid
        tx = int(wx // TILE_SIZE)
        ty = int(wy // TILE_SIZE)
        if 0 <= tx < self.w and 0 <= ty < self.h:
            return self.tiles[tx][ty].solid
        return True

    def hazard_at(self, wx, wy):
        # returns hazard info at world pos
        tx = int(wx // TILE_SIZE)
        ty = int(wy // TILE_SIZE)
        if 0 <= tx < self.w and 0 <= ty < self.h:
            t = self.tiles[tx][ty]
            if (not t.solid) and t.hazard:
                return {"type": t.hazard_type, "dir": t.hazard_dir}
        return None

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
                            col = HAZARD_INFO.get(tile.hazard_type, {}).get("color", ORANGE)
                            inner = rect.inflate(-8, -8)
                            pygame.draw.rect(surf, col, inner)
                            if tile.hazard_type == "conveyor":
                                self._draw_conveyor_arrow(surf, inner, tile.hazard_dir)

        obj_font = pygame.font.SysFont("consolas", 14)
        for obj in self.interactables:
            obj.draw(surf, cam_x, cam_y, obj_font)

    def _draw_conveyor_arrow(self, surf, rect, direction):
        dx, dy = direction
        cx, cy = rect.center
        end_x = cx + dx * rect.width // 3
        end_y = cy + dy * rect.height // 3
        pygame.draw.line(surf, BLACK, (cx, cy), (end_x, end_y), 2)
        pygame.draw.circle(surf, BLACK, (end_x, end_y), 3)

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
                        col = HAZARD_INFO.get(t.hazard_type, {}).get("minimap", ORANGE)
                    mm.set_at((int(x * scale_x), int(y * scale_y)), col)

        for obj in self.interactables:
            ox = int(obj.x / TILE_SIZE * scale_x)
            oy = int(obj.y / TILE_SIZE * scale_y)
            col = INTERACTABLE_MINIMAP.get(obj.kind, WHITE)
            if 0 <= ox < mm_w and 0 <= oy < mm_h:
                mm.set_at((ox, oy), col)

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
