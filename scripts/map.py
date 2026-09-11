import random
import time
from perlin_noise import PerlinNoise

from ascii import (
    ROCK, BUSH, WALL, EMPTY, WATER, BOG, COIN, SHOP, GUARD,
    COIN_LEFT, COIN_RIGHT,
    BUILDINGS, NATURE,
)

CHUNK_WIDTH = 133
CHUNK_HEIGHT = 36

WORLD_CHUNKS_X = 10
WORLD_CHUNKS_Y = 10
CENTER_CHUNK_X = WORLD_CHUNKS_X // 2
CENTER_CHUNK_Y = WORLD_CHUNKS_Y // 2


class Map:
    """
    Finite 10×10 world – chunks are generated lazily on first visit.
    Only the starting chunk (and optionally the two shop chunks) are
    built at construction time so New Game stays responsive.
    """

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randint(0, 100_000)

        self.noise = PerlinNoise(octaves=4, seed=seed)
        self.feature_noise = PerlinNoise(octaves=8, seed=seed + 1)
        self.chunks = {}
        self.seed = seed

        self.discovered_pois = {}
        self.guards = []

        self.coins_remaining = {}   # (cx, cy) -> int
        self.total_coins = 0        # grows as chunks are generated

        self._shop_locations = self._choose_shop_locations()
        # Randomly reveal one shop on the minimap at start
        self.revealed_shop = random.Random(seed + 42).choice(list(self._shop_locations))
        self.special_shop = (self._shop_locations - {self.revealed_shop}).pop()

        # Mark revealed shop so minimap shows "$" before the player visits
        self.discovered_pois[self.revealed_shop] = {("shop", -1, -1)}

        self._last_shop_spawn_time = 0.0
        self._shop_spawn_cooldown = 30.0
        self._pending_extra_guards = {}  # (cx, cy) -> count

        # Generate ONLY the centre (start) chunk now – everything else is lazy
        self.get_chunk(CENTER_CHUNK_X, CENTER_CHUNK_Y)

    def _choose_shop_locations(self):
        rng = random.Random(self.seed + 99991)
        left_candidates = [
            (x, y)
            for x in range(1, 4)
            for y in range(WORLD_CHUNKS_Y)
            if (x, y) != (CENTER_CHUNK_X, CENTER_CHUNK_Y)
        ]
        right_candidates = [
            (x, y)
            for x in range(6, 9)
            for y in range(WORLD_CHUNKS_Y)
            if (x, y) != (CENTER_CHUNK_X, CENTER_CHUNK_Y)
        ]
        left = rng.choice(left_candidates)
        right = rng.choice(right_candidates)
        return {left, right}

    def is_special_shop(self, chunk_x, chunk_y):
        return (chunk_x, chunk_y) == self.special_shop

    def get_chunk(self, chunk_x, chunk_y):
        chunk_x = max(0, min(WORLD_CHUNKS_X - 1, chunk_x))
        chunk_y = max(0, min(WORLD_CHUNKS_Y - 1, chunk_y))
        if (chunk_x, chunk_y) not in self.chunks:
            self.chunks[(chunk_x, chunk_y)] = self._generate_chunk(chunk_x, chunk_y)
        return self.chunks[(chunk_x, chunk_y)]

    def _is_world_edge(self, chunk_x, chunk_y, local_x, local_y):
        if chunk_x == 0 and local_x == 0:
            return True
        if chunk_x == WORLD_CHUNKS_X - 1 and local_x == CHUNK_WIDTH - 1:
            return True
        if chunk_y == 0 and local_y == 0:
            return True
        if chunk_y == WORLD_CHUNKS_Y - 1 and local_y == CHUNK_HEIGHT - 1:
            return True
        return False

    def _stamp(self, chunk_data, art_lines, top_left_x, top_left_y,
               chunk_x, chunk_y, overwrite=None):
        if overwrite is None:
            overwrite = set()
        for dy, line in enumerate(art_lines):
            for dx, ch in enumerate(line):
                if ch == " ":
                    continue
                x = top_left_x + dx
                y = top_left_y + dy
                if not (0 <= x < CHUNK_WIDTH and 0 <= y < CHUNK_HEIGHT):
                    continue
                if self._is_world_edge(chunk_x, chunk_y, x, y):
                    continue
                if chunk_data[y][x] in (EMPTY, ROCK, BUSH, WATER, BOG) or ch in overwrite:
                    chunk_data[y][x] = ch

    def _generate_chunk(self, chunk_x, chunk_y):
        chunk_data = [[EMPTY for _ in range(CHUNK_WIDTH)] for _ in range(CHUNK_HEIGHT)]
        scale = 0.05
        coin_count = 0
        water_cells = []

        for y in range(CHUNK_HEIGHT):
            for x in range(CHUNK_WIDTH):
                if self._is_world_edge(chunk_x, chunk_y, x, y):
                    chunk_data[y][x] = WALL
                    continue

                global_x = (chunk_x * CHUNK_WIDTH) + x
                global_y = (chunk_y * CHUNK_HEIGHT) + y
                noise_val = self.noise([global_x * scale, global_y * scale]) + 0.5

                if noise_val < 0.32:
                    chunk_data[y][x] = WATER
                    water_cells.append((x, y))
                elif noise_val < 0.62:
                    feature_val = self.feature_noise(
                        [global_x * scale * 2, global_y * scale * 2]
                    ) + 0.5
                    if feature_val > 0.82:
                        chunk_data[y][x] = BUSH
                    else:
                        chunk_data[y][x] = EMPTY
                else:
                    chunk_data[y][x] = ROCK

        rng = random.Random(self.seed + chunk_x * 73856093 + chunk_y * 19349663)

        # ~half of water → bog
        rng.shuffle(water_cells)
        for wx, wy in water_cells[: len(water_cells) // 2]:
            chunk_data[wy][wx] = BOG

        # Nature art (3× trees)
        num_nature = rng.randint(12, 27)
        nature_keys = list(NATURE.keys())
        tree_keys = ["pine_tree", "tall_tree"]
        for _ in range(num_nature):
            if rng.random() < 0.70:
                key = rng.choice(tree_keys)
            else:
                key = rng.choice(nature_keys)
            art = NATURE[key]
            h = len(art)
            w = max(len(line) for line in art)
            sx = rng.randint(2, CHUNK_WIDTH - w - 3)
            sy = rng.randint(2, CHUNK_HEIGHT - h - 3)
            if chunk_data[sy][sx] in (EMPTY, BUSH, ROCK):
                self._stamp(chunk_data, art, sx, sy, chunk_x, chunk_y)

        # Occasional house / hut
        if (chunk_x, chunk_y) not in self._shop_locations and rng.random() < 0.35:
            key = rng.choice(["small_house", "hut"])
            art = BUILDINGS[key]
            h = len(art)
            w = max(len(line) for line in art)
            sx = rng.randint(4, CHUNK_WIDTH - w - 5)
            sy = rng.randint(3, CHUNK_HEIGHT - h - 4)
            if chunk_data[sy][sx] in (EMPTY, BUSH, ROCK):
                self._stamp(chunk_data, art, sx, sy, chunk_x, chunk_y)

        # Coins as "(£)"
        num_coins = rng.randint(3, 7)
        for _ in range(num_coins):
            cx = rng.randint(2, CHUNK_WIDTH - 4)
            cy = rng.randint(1, CHUNK_HEIGHT - 2)
            if (chunk_data[cy][cx - 1] == EMPTY
                    and chunk_data[cy][cx] == EMPTY
                    and chunk_data[cy][cx + 1] == EMPTY):
                chunk_data[cy][cx - 1] = COIN_LEFT
                chunk_data[cy][cx] = COIN
                chunk_data[cy][cx + 1] = COIN_RIGHT
                coin_count += 1

        # Base guardians 1–2
        base_guards = rng.randint(1, 2)
        for _ in range(base_guards):
            self._place_one_guard(chunk_data, chunk_x, chunk_y, rng)

        # Pending extras from shop visits
        extras = self._pending_extra_guards.pop((chunk_x, chunk_y), 0)
        for _ in range(extras):
            self._place_one_guard(chunk_data, chunk_x, chunk_y, rng)

        self.coins_remaining[(chunk_x, chunk_y)] = coin_count
        self.total_coins += coin_count

        # Shop building
        if (chunk_x, chunk_y) in self._shop_locations:
            art = BUILDINGS["shop"]
            h = len(art)
            w = max(len(line) for line in art)
            sx = rng.randint(5, CHUNK_WIDTH - w - 6)
            sy = rng.randint(4, CHUNK_HEIGHT - h - 5)
            for dy in range(-1, h + 1):
                for dx in range(-1, w + 1):
                    xx, yy = sx + dx, sy + dy
                    if (0 < xx < CHUNK_WIDTH - 1 and 0 < yy < CHUNK_HEIGHT - 1
                            and not self._is_world_edge(chunk_x, chunk_y, xx, yy)):
                        if chunk_data[yy][xx] not in (WALL,):
                            chunk_data[yy][xx] = EMPTY
            self._stamp(chunk_data, art, sx, sy, chunk_x, chunk_y,
                        overwrite={"+", "-", "|", "S", "H", "O", "P"})
            mid_x = sx + w // 2
            mid_y = sy + h // 2
            if not self._is_world_edge(chunk_x, chunk_y, mid_x, mid_y):
                chunk_data[mid_y][mid_x] = SHOP

        return chunk_data

    def _place_one_guard(self, chunk_data, chunk_x, chunk_y, rng):
        for _ in range(40):
            gx = rng.randint(1, CHUNK_WIDTH - 2)
            gy = rng.randint(1, CHUNK_HEIGHT - 2)
            if chunk_data[gy][gx] in (EMPTY, COIN):
                chunk_data[gy][gx] = GUARD
                self.guards.append({
                    "chunk_x": chunk_x,
                    "chunk_y": chunk_y,
                    "x": gx,
                    "y": gy,
                })
                return True
        return False

    def notify_shop_visit(self, player):
        """Queue one extra guardian on a neighbouring (preferably unexplored) chunk."""
        now = time.time()
        if now - self._last_shop_spawn_time < self._shop_spawn_cooldown:
            return False
        self._last_shop_spawn_time = now

        # Prefer adjacent unexplored chunks
        candidates = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx = player.chunk_x + dx
            ny = player.chunk_y + dy
            if (0 <= nx < WORLD_CHUNKS_X and 0 <= ny < WORLD_CHUNKS_Y
                    and (nx, ny) not in self.chunks):
                candidates.append((nx, ny))

        if candidates:
            target = random.choice(candidates)
            self._pending_extra_guards[target] = (
                self._pending_extra_guards.get(target, 0) + 1
            )
            return True

        # All neighbours already generated – add a guard to a nearby chunk
        nearby = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = player.chunk_x + dx
            ny = player.chunk_y + dy
            if 0 <= nx < WORLD_CHUNKS_X and 0 <= ny < WORLD_CHUNKS_Y:
                nearby.append((nx, ny))
        if nearby:
            target = random.choice(nearby)
            chunk = self.get_chunk(*target)
            rng = random.Random(self.seed + target[0] * 99 + target[1] * 77 + int(now))
            self._place_one_guard(chunk, target[0], target[1], rng)
            return True
        return False

    def mark_poi_discovered(self, chunk_x, chunk_y, kind, local_x, local_y):
        key = (chunk_x, chunk_y)
        if key not in self.discovered_pois:
            self.discovered_pois[key] = set()
        self.discovered_pois[key].add((kind, local_x, local_y))

    def remove_tile(self, chunk_x, chunk_y, x, y):
        chunk = self.get_chunk(chunk_x, chunk_y)
        if not (0 <= y < CHUNK_HEIGHT and 0 <= x < CHUNK_WIDTH):
            return
        if chunk[y][x] == COIN:
            key = (chunk_x, chunk_y)
            self.coins_remaining[key] = max(0, self.coins_remaining.get(key, 1) - 1)
            if x > 0 and chunk[y][x - 1] == COIN_LEFT:
                chunk[y][x - 1] = EMPTY
            if x < CHUNK_WIDTH - 1 and chunk[y][x + 1] == COIN_RIGHT:
                chunk[y][x + 1] = EMPTY
            chunk[y][x] = EMPTY
        else:
            chunk[y][x] = EMPTY

    def all_coins_collected(self):
        """
        Win when every chunk in the world has been generated AND
        no coins remain on any of them.
        """
        world_size = WORLD_CHUNKS_X * WORLD_CHUNKS_Y
        if len(self.chunks) < world_size:
            return False
        return self.total_coins > 0 and sum(self.coins_remaining.values()) == 0

    def move_guards(self, player, speed_factor=1.0):
        chunk = self.get_chunk(player.chunk_x, player.chunk_y)

        for g in self.guards:
            if g["chunk_x"] == player.chunk_x and g["chunk_y"] == player.chunk_y:
                if 0 <= g["y"] < CHUNK_HEIGHT and 0 <= g["x"] < CHUNK_WIDTH:
                    if chunk[g["y"]][g["x"]] == GUARD:
                        chunk[g["y"]][g["x"]] = EMPTY

        for g in self.guards:
            if g["chunk_x"] != player.chunk_x or g["chunk_y"] != player.chunk_y:
                continue

            chance = min(0.35, 0.12 + speed_factor * 0.015)
            if random.random() > chance:
                chunk[g["y"]][g["x"]] = GUARD
                continue

            if random.random() < 0.55:
                dx, dy = random.choice([
                    (1, 0), (-1, 0), (0, 1), (0, -1),
                    (1, 1), (1, -1), (-1, 1), (-1, -1), (0, 0)
                ])
            else:
                dx = dy = 0
                if g["x"] < player.x:
                    dx = 1
                elif g["x"] > player.x:
                    dx = -1
                if g["y"] < player.y:
                    dy = 1
                elif g["y"] > player.y:
                    dy = -1
                if abs(g["x"] - player.x) >= abs(g["y"] - player.y):
                    dy = 0
                else:
                    dx = 0

            nx = g["x"] + dx
            ny = g["y"] + dy

            if (0 <= nx < CHUNK_WIDTH and 0 <= ny < CHUNK_HEIGHT
                    and chunk[ny][nx] in (EMPTY, COIN, COIN_LEFT, COIN_RIGHT, BOG)):
                g["x"] = nx
                g["y"] = ny

            chunk[g["y"]][g["x"]] = GUARD
