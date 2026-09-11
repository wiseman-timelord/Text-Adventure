import random
import time
from perlin_noise import PerlinNoise

from ascii import ROCK, BUSH, WALL, EMPTY, WATER, COIN, SHOP, GUARD

# Playable area (previously increased)
CHUNK_WIDTH = 133
CHUNK_HEIGHT = 36

# Finite world – 10×10 chunks
WORLD_CHUNKS_X = 10
WORLD_CHUNKS_Y = 10
CENTER_CHUNK_X = WORLD_CHUNKS_X // 2   # 5
CENTER_CHUNK_Y = WORLD_CHUNKS_Y // 2   # 5


class Map:
    """
    Finite 10×10 world.
    Walls only on the absolute outer boundary.
    Exactly two shops: one on the left side, one on the right side.
    Never on the starting (centre) chunk.
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

        # Track remaining coins per chunk for minimap
        self.coins_remaining = {}   # (cx, cy) -> int

        # Place the two shops once at world creation
        self._shop_locations = self._choose_shop_locations()

        # Shop-triggered extra guards: 30 s cooldown
        self._last_shop_spawn_time = 0.0
        self._shop_spawn_cooldown = 30.0
        # Pending extra guards to place when a chunk is first generated
        self._pending_extra_guards = {}  # (cx, cy) -> int

    def _choose_shop_locations(self):
        """
        Return two (chunk_x, chunk_y) positions:
        - one on the left half (but not column 0)
        - one on the right half (but not the last column)
        Never the centre chunk.
        """
        rng = random.Random(self.seed + 99991)
        # Left side: columns 1-3, any row except we avoid centre
        left_candidates = [
            (x, y)
            for x in range(1, 4)
            for y in range(WORLD_CHUNKS_Y)
            if (x, y) != (CENTER_CHUNK_X, CENTER_CHUNK_Y)
        ]
        # Right side: columns 6-8
        right_candidates = [
            (x, y)
            for x in range(6, 9)
            for y in range(WORLD_CHUNKS_Y)
            if (x, y) != (CENTER_CHUNK_X, CENTER_CHUNK_Y)
        ]
        left = rng.choice(left_candidates)
        right = rng.choice(right_candidates)
        return {left, right}

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

    def _generate_chunk(self, chunk_x, chunk_y):
        chunk_data = [[EMPTY for _ in range(CHUNK_WIDTH)] for _ in range(CHUNK_HEIGHT)]
        scale = 0.05
        coin_count = 0

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

        # Coins – place a modest number; fewer automatic guardians
        num_coins = rng.randint(3, 7)
        for _ in range(num_coins):
            cx = rng.randint(1, CHUNK_WIDTH - 2)
            cy = rng.randint(1, CHUNK_HEIGHT - 2)
            if chunk_data[cy][cx] == EMPTY:
                chunk_data[cy][cx] = COIN
                coin_count += 1

        # Base guardians: only 1–2 per chunk (stumbling zombies)
        base_guards = rng.randint(1, 2)
        for _ in range(base_guards):
            self._place_one_guard(chunk_data, chunk_x, chunk_y, rng)

        # Any pending extras from previous shop visits
        extras = self._pending_extra_guards.pop((chunk_x, chunk_y), 0)
        for _ in range(extras):
            self._place_one_guard(chunk_data, chunk_x, chunk_y, rng)

        self.coins_remaining[(chunk_x, chunk_y)] = coin_count

        # Place shop only if this chunk was chosen
        if (chunk_x, chunk_y) in self._shop_locations:
            sx = rng.randint(3, CHUNK_WIDTH - 4)
            sy = rng.randint(3, CHUNK_HEIGHT - 4)
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if 0 < sy + dy < CHUNK_HEIGHT - 1 and 0 < sx + dx < CHUNK_WIDTH - 1:
                        if not self._is_world_edge(chunk_x, chunk_y, sx + dx, sy + dy):
                            chunk_data[sy + dy][sx + dx] = EMPTY
            if not self._is_world_edge(chunk_x, chunk_y, sx, sy):
                chunk_data[sy][sx] = SHOP

        return chunk_data

    def _place_one_guard(self, chunk_data, chunk_x, chunk_y, rng):
        """Place a single guardian on an empty or coin tile."""
        for _ in range(40):  # limited attempts
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
        """
        Called when the player enters a shop.
        With a 30-second cooldown, queues one extra guardian for the
        *next* unexplored neighbouring chunk (so the following map
        tile tends to have 2 instead of 3+).
        """
        now = time.time()
        if now - self._last_shop_spawn_time < self._shop_spawn_cooldown:
            return False
        self._last_shop_spawn_time = now

        # Prefer an adjacent unexplored chunk; fall back to any unexplored
        candidates = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx = player.chunk_x + dx
            ny = player.chunk_y + dy
            if (0 <= nx < WORLD_CHUNKS_X and 0 <= ny < WORLD_CHUNKS_Y
                    and (nx, ny) not in self.chunks):
                candidates.append((nx, ny))
        if not candidates:
            for cy in range(WORLD_CHUNKS_Y):
                for cx in range(WORLD_CHUNKS_X):
                    if (cx, cy) not in self.chunks:
                        candidates.append((cx, cy))
        if candidates:
            target = random.choice(candidates)
            self._pending_extra_guards[target] = (
                self._pending_extra_guards.get(target, 0) + 1
            )
            return True
        return False

    def mark_poi_discovered(self, chunk_x, chunk_y, kind, local_x, local_y):
        key = (chunk_x, chunk_y)
        if key not in self.discovered_pois:
            self.discovered_pois[key] = set()
        self.discovered_pois[key].add((kind, local_x, local_y))

    def remove_tile(self, chunk_x, chunk_y, x, y):
        chunk = self.get_chunk(chunk_x, chunk_y)
        if 0 <= y < CHUNK_HEIGHT and 0 <= x < CHUNK_WIDTH:
            if chunk[y][x] == COIN:
                key = (chunk_x, chunk_y)
                self.coins_remaining[key] = max(0, self.coins_remaining.get(key, 1) - 1)
            chunk[y][x] = EMPTY

    def move_guards(self, player, speed_factor=1.0):
        """
        Stumbling-zombie movement:
        - Low base chance to take a step each tick
        - Mostly move toward the player, but with a high chance of
          random / staggered steps (stumble)
        - speed_factor increases the move chance only very gently
        """
        chunk = self.get_chunk(player.chunk_x, player.chunk_y)

        # Clear current guard tiles so we can re-place after movement
        for g in self.guards:
            if g["chunk_x"] == player.chunk_x and g["chunk_y"] == player.chunk_y:
                if 0 <= g["y"] < CHUNK_HEIGHT and 0 <= g["x"] < CHUNK_WIDTH:
                    if chunk[g["y"]][g["x"]] == GUARD:
                        chunk[g["y"]][g["x"]] = EMPTY

        for g in self.guards:
            if g["chunk_x"] != player.chunk_x or g["chunk_y"] != player.chunk_y:
                continue

            # Gentle speed-up: base ~0.12, +0.015 per coin-equivalent
            # Cap at 0.35 so they never become frantic
            chance = min(0.35, 0.12 + speed_factor * 0.015)
            if random.random() > chance:
                chunk[g["y"]][g["x"]] = GUARD
                continue

            # 55 % chance of pure random stumble, otherwise biased toward player
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
                # Prefer cardinal over diagonal
                if abs(g["x"] - player.x) >= abs(g["y"] - player.y):
                    dy = 0
                else:
                    dx = 0

            nx = g["x"] + dx
            ny = g["y"] + dy

            if (0 <= nx < CHUNK_WIDTH and 0 <= ny < CHUNK_HEIGHT
                    and chunk[ny][nx] in (EMPTY, COIN)):
                g["x"] = nx
                g["y"] = ny

            chunk[g["y"]][g["x"]] = GUARD
