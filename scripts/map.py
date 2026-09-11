import random
import time
from perlin_noise import PerlinNoise

from ascii import (
    ROCK, BUSH, WALL, EMPTY, WATER, BOG, COIN, SHOP, GUARD, ZOMBIE,
    COIN_LEFT, COIN_RIGHT,
    BUILDINGS, NATURE,
)

CHUNK_WIDTH = 133
CHUNK_HEIGHT = 36

WORLD_CHUNKS_X = 10
WORLD_CHUNKS_Y = 10
CENTER_CHUNK_X = WORLD_CHUNKS_X // 2
CENTER_CHUNK_Y = WORLD_CHUNKS_Y // 2

# Sight / guard radii (in tiles, same chunk only)
G_COIN_RADIUS = 10
SIGHT_RANGE = 18          # Manhattan distance to "see" something
WALKABLE = (EMPTY, COIN, COIN_LEFT, COIN_RIGHT, BOG)


class Map:
    """
    Finite 10×10 world – chunks generated lazily.

    Gold-Hunter (G): 1 per chunk. Wanders until a coin is nearby, then
    stays within G_COIN_RADIUS of it. If the player takes that coin, G
    chases the player (faster than Z) until out of sight, then wanders
    again. Flees zombies; after enough chases is driven off the map.

    Zombie (Z): Starts very slow. Speeds up as the player collects coins.
    Wanders until it sees the player or a Gold-Hunter, then pursues.
    Shop visits raise global zombie count by +1 on every map tile.
    """

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randint(0, 100_000)

        self.noise = PerlinNoise(octaves=4, seed=seed)
        self.feature_noise = PerlinNoise(octaves=8, seed=seed + 1)
        self.chunks = {}
        self.seed = seed

        self.discovered_pois = {}
        self.guards = []    # Gold-Hunters
        self.zombies = []   # Zombies

        self.coins_remaining = {}
        self.total_coins = 0

        self._shop_locations = self._choose_shop_locations()
        self.revealed_shop = random.Random(seed + 42).choice(list(self._shop_locations))
        self.special_shop = (self._shop_locations - {self.revealed_shop}).pop()
        self.discovered_pois[self.revealed_shop] = {("shop", -1, -1)}

        self._last_shop_spawn_time = 0.0
        self._shop_spawn_cooldown = 30.0
        # Global zombies-per-chunk level (starts at 1; +1 each shop visit)
        self.zombie_level = 1

        self.get_chunk(CENTER_CHUNK_X, CENTER_CHUNK_Y)

    # ------------------------------------------------------------------
    def _choose_shop_locations(self):
        rng = random.Random(self.seed + 99991)
        left = [
            (x, y) for x in range(1, 4) for y in range(WORLD_CHUNKS_Y)
            if (x, y) != (CENTER_CHUNK_X, CENTER_CHUNK_Y)
        ]
        right = [
            (x, y) for x in range(6, 9) for y in range(WORLD_CHUNKS_Y)
            if (x, y) != (CENTER_CHUNK_X, CENTER_CHUNK_Y)
        ]
        return {rng.choice(left), rng.choice(right)}

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

    # ------------------------------------------------------------------
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
                    chunk_data[y][x] = BUSH if feature_val > 0.82 else EMPTY
                else:
                    chunk_data[y][x] = ROCK

        rng = random.Random(self.seed + chunk_x * 73856093 + chunk_y * 19349663)

        rng.shuffle(water_cells)
        for wx, wy in water_cells[: len(water_cells) // 2]:
            chunk_data[wy][wx] = BOG

        # Nature (3× trees)
        num_nature = rng.randint(12, 27)
        nature_keys = list(NATURE.keys())
        tree_keys = ["pine_tree", "tall_tree"]
        for _ in range(num_nature):
            key = rng.choice(tree_keys) if rng.random() < 0.70 else rng.choice(nature_keys)
            art = NATURE[key]
            h, w = len(art), max(len(line) for line in art)
            sx = rng.randint(2, CHUNK_WIDTH - w - 3)
            sy = rng.randint(2, CHUNK_HEIGHT - h - 3)
            if chunk_data[sy][sx] in (EMPTY, BUSH, ROCK):
                self._stamp(chunk_data, art, sx, sy, chunk_x, chunk_y)

        if (chunk_x, chunk_y) not in self._shop_locations and rng.random() < 0.35:
            art = BUILDINGS[rng.choice(["small_house", "hut"])]
            h, w = len(art), max(len(line) for line in art)
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

        # Exactly ONE Gold-Hunter per chunk
        self._place_entity(chunk_data, chunk_x, chunk_y, rng, kind="G")

        # Zombies: current global level (1 at start, rises with shop visits)
        for _ in range(self.zombie_level):
            self._place_entity(chunk_data, chunk_x, chunk_y, rng, kind="Z")

        self.coins_remaining[(chunk_x, chunk_y)] = coin_count
        self.total_coins += coin_count

        # Shop building
        if (chunk_x, chunk_y) in self._shop_locations:
            art = BUILDINGS["shop"]
            h, w = len(art), max(len(line) for line in art)
            sx = rng.randint(5, CHUNK_WIDTH - w - 6)
            sy = rng.randint(4, CHUNK_HEIGHT - h - 5)
            for dy in range(-1, h + 1):
                for dx in range(-1, w + 1):
                    xx, yy = sx + dx, sy + dy
                    if (0 < xx < CHUNK_WIDTH - 1 and 0 < yy < CHUNK_HEIGHT - 1
                            and not self._is_world_edge(chunk_x, chunk_y, xx, yy)):
                        if chunk_data[yy][xx] != WALL:
                            chunk_data[yy][xx] = EMPTY
            self._stamp(chunk_data, art, sx, sy, chunk_x, chunk_y,
                        overwrite={"+", "-", "|", "S", "H", "O", "P"})
            mid_x, mid_y = sx + w // 2, sy + h // 2
            if not self._is_world_edge(chunk_x, chunk_y, mid_x, mid_y):
                chunk_data[mid_y][mid_x] = SHOP

        return chunk_data

    def _place_entity(self, chunk_data, chunk_x, chunk_y, rng, kind="G"):
        symbol = GUARD if kind == "G" else ZOMBIE
        for _ in range(50):
            gx = rng.randint(1, CHUNK_WIDTH - 2)
            gy = rng.randint(1, CHUNK_HEIGHT - 2)
            if chunk_data[gy][gx] in (EMPTY, COIN):
                chunk_data[gy][gx] = symbol
                entry = {
                    "chunk_x": chunk_x,
                    "chunk_y": chunk_y,
                    "x": gx,
                    "y": gy,
                    "mode": "wander",       # wander | guard | chase | flee
                    "target_coin": None,    # (x, y) of guarded coin
                    "zombie_sights": 0,     # times this G has been chased by a Z
                    "flee_until": 0.0,
                }
                if kind == "G":
                    self.guards.append(entry)
                else:
                    self.zombies.append(entry)
                return True
        return False

    # ------------------------------------------------------------------
    def notify_shop_visit(self, player):
        """
        Each shop visit (30 s cooldown) raises the global zombie level by 1.
        Every already-generated map tile gains one extra zombie immediately;
        future tiles spawn with the new level.
        """
        now = time.time()
        if now - self._last_shop_spawn_time < self._shop_spawn_cooldown:
            return False
        self._last_shop_spawn_time = now

        self.zombie_level += 1

        # Add one zombie to every chunk that already exists
        for (cx, cy), chunk_data in list(self.chunks.items()):
            rng = random.Random(
                self.seed + cx * 99 + cy * 77 + self.zombie_level * 13 + int(now)
            )
            self._place_entity(chunk_data, cx, cy, rng, kind="Z")
        return True

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
            # Any G that was guarding this coin switches to chase
            for g in self.guards:
                if (g["chunk_x"] == chunk_x and g["chunk_y"] == chunk_y
                        and g.get("target_coin") == (x, y)):
                    g["mode"] = "chase"
                    g["target_coin"] = None
        else:
            chunk[y][x] = EMPTY

    def all_coins_collected(self):
        world_size = WORLD_CHUNKS_X * WORLD_CHUNKS_Y
        if len(self.chunks) < world_size:
            return False
        return self.total_coins > 0 and sum(self.coins_remaining.values()) == 0

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _manhattan(ax, ay, bx, by):
        return abs(ax - bx) + abs(ay - by)

    def _find_nearest_coin(self, chunk_data, x, y, radius):
        best, best_d = None, radius + 1
        for cy in range(max(0, y - radius), min(CHUNK_HEIGHT, y + radius + 1)):
            for cx in range(max(0, x - radius), min(CHUNK_WIDTH, x + radius + 1)):
                if chunk_data[cy][cx] == COIN:
                    d = self._manhattan(x, y, cx, cy)
                    if d < best_d:
                        best_d = d
                        best = (cx, cy)
        return best

    def _step_toward(self, ex, ey, tx, ty, chunk_data, allow_diagonal=False):
        """One step toward (tx,ty). Returns (nx, ny) or current pos if blocked."""
        dx = dy = 0
        if ex < tx:
            dx = 1
        elif ex > tx:
            dx = -1
        if ey < ty:
            dy = 1
        elif ey > ty:
            dy = -1
        if not allow_diagonal:
            if abs(ex - tx) >= abs(ey - ty):
                dy = 0
            else:
                dx = 0
        nx, ny = ex + dx, ey + dy
        if (0 <= nx < CHUNK_WIDTH and 0 <= ny < CHUNK_HEIGHT
                and chunk_data[ny][nx] in WALKABLE):
            return nx, ny
        # Try alternate axis
        if dx and dy:
            if (0 <= ex + dx < CHUNK_WIDTH and chunk_data[ey][ex + dx] in WALKABLE):
                return ex + dx, ey
            if (0 <= ey + dy < CHUNK_HEIGHT and chunk_data[ey + dy][ex] in WALKABLE):
                return ex, ey + dy
        return ex, ey

    def _step_away(self, ex, ey, tx, ty, chunk_data):
        """One step away from (tx,ty)."""
        dx = dy = 0
        if ex < tx:
            dx = -1
        elif ex > tx:
            dx = 1
        if ey < ty:
            dy = -1
        elif ey > ty:
            dy = 1
        if abs(ex - tx) >= abs(ey - ty):
            dy = 0
        else:
            dx = 0
        nx, ny = ex + dx, ey + dy
        if (0 <= nx < CHUNK_WIDTH and 0 <= ny < CHUNK_HEIGHT
                and chunk_data[ny][nx] in WALKABLE):
            return nx, ny
        return ex, ey

    def _random_step(self, ex, ey, chunk_data):
        opts = [(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]
        random.shuffle(opts)
        for dx, dy in opts:
            nx, ny = ex + dx, ey + dy
            if (0 <= nx < CHUNK_WIDTH and 0 <= ny < CHUNK_HEIGHT
                    and chunk_data[ny][nx] in WALKABLE):
                return nx, ny
        return ex, ey

    # ------------------------------------------------------------------
    #  Monster tick
    # ------------------------------------------------------------------
    def move_monsters(self, player, coins_collected=0):
        """
        Advance Gold-Hunters and Zombies on the player's current chunk.
        coins_collected drives zombie speed-up.
        """
        cx, cy = player.chunk_x, player.chunk_y
        chunk = self.get_chunk(cx, cy)

        # Clear old symbols
        for g in self.guards:
            if g["chunk_x"] == cx and g["chunk_y"] == cy:
                if 0 <= g["y"] < CHUNK_HEIGHT and 0 <= g["x"] < CHUNK_WIDTH:
                    if chunk[g["y"]][g["x"]] == GUARD:
                        chunk[g["y"]][g["x"]] = EMPTY
        for z in self.zombies:
            if z["chunk_x"] == cx and z["chunk_y"] == cy:
                if 0 <= z["y"] < CHUNK_HEIGHT and 0 <= z["x"] < CHUNK_WIDTH:
                    if chunk[z["y"]][z["x"]] == ZOMBIE:
                        chunk[z["y"]][z["x"]] = EMPTY

        # --- Gold-Hunters ---
        survivors = []
        for g in self.guards:
            if g["chunk_x"] != cx or g["chunk_y"] != cy:
                survivors.append(g)
                continue

            # Check for nearby zombie
            nearest_z = None
            nearest_z_d = SIGHT_RANGE + 1
            for z in self.zombies:
                if z["chunk_x"] == cx and z["chunk_y"] == cy:
                    d = self._manhattan(g["x"], g["y"], z["x"], z["y"])
                    if d < nearest_z_d:
                        nearest_z_d = d
                        nearest_z = z

            # Flee from zombie if in sight (count each new encounter once)
            if nearest_z is not None and nearest_z_d <= SIGHT_RANGE:
                if g["mode"] != "flee":
                    g["zombie_sights"] += 1
                    if g["zombie_sights"] >= 3:
                        # Driven off the map after 3 separate encounters
                        continue
                    g["mode"] = "flee"
                    g["flee_until"] = time.time() + 4.0
                nx, ny = self._step_away(g["x"], g["y"], nearest_z["x"], nearest_z["y"], chunk)
                g["x"], g["y"] = nx, ny
                chunk[g["y"]][g["x"]] = GUARD
                survivors.append(g)
                continue

            # Still in flee timer?
            if g["mode"] == "flee" and time.time() < g.get("flee_until", 0):
                nx, ny = self._random_step(g["x"], g["y"], chunk)
                g["x"], g["y"] = nx, ny
                chunk[g["y"]][g["x"]] = GUARD
                survivors.append(g)
                continue
            if g["mode"] == "flee":
                g["mode"] = "wander"

            # G move chance – starts faster than zombies
            g_chance = 0.28
            if g["mode"] == "chase":
                g_chance = 0.40   # chase a bit faster
            if random.random() > g_chance:
                chunk[g["y"]][g["x"]] = GUARD
                survivors.append(g)
                continue

            if g["mode"] == "chase":
                # Pursue player until out of sight
                d_player = self._manhattan(g["x"], g["y"], player.x, player.y)
                if d_player > SIGHT_RANGE:
                    g["mode"] = "wander"
                else:
                    nx, ny = self._step_toward(g["x"], g["y"], player.x, player.y, chunk)
                    g["x"], g["y"] = nx, ny
                chunk[g["y"]][g["x"]] = GUARD
                survivors.append(g)
                continue

            # Guard or seek coin
            coin = None
            if g["mode"] == "guard" and g.get("target_coin"):
                tx, ty = g["target_coin"]
                if (0 <= ty < CHUNK_HEIGHT and 0 <= tx < CHUNK_WIDTH
                        and chunk[ty][tx] == COIN):
                    coin = (tx, ty)
                else:
                    g["mode"] = "wander"
                    g["target_coin"] = None

            if coin is None:
                coin = self._find_nearest_coin(chunk, g["x"], g["y"], G_COIN_RADIUS)

            if coin is not None:
                g["mode"] = "guard"
                g["target_coin"] = coin
                d = self._manhattan(g["x"], g["y"], coin[0], coin[1])
                if d > G_COIN_RADIUS:
                    # Too far – move closer
                    nx, ny = self._step_toward(g["x"], g["y"], coin[0], coin[1], chunk)
                    g["x"], g["y"] = nx, ny
                elif d < 2:
                    # Too close – step away a bit / orbit
                    nx, ny = self._step_away(g["x"], g["y"], coin[0], coin[1], chunk)
                    g["x"], g["y"] = nx, ny
                else:
                    # Orbit randomly within radius
                    nx, ny = self._random_step(g["x"], g["y"], chunk)
                    if self._manhattan(nx, ny, coin[0], coin[1]) <= G_COIN_RADIUS:
                        g["x"], g["y"] = nx, ny
            else:
                g["mode"] = "wander"
                nx, ny = self._random_step(g["x"], g["y"], chunk)
                g["x"], g["y"] = nx, ny

            chunk[g["y"]][g["x"]] = GUARD
            survivors.append(g)

        self.guards = survivors

        # --- Zombies ---
        # Speed scales with coins collected: very slow at 0, ramps up
        z_chance = min(0.32, 0.06 + coins_collected * 0.012)

        for z in self.zombies:
            if z["chunk_x"] != cx or z["chunk_y"] != cy:
                continue
            if random.random() > z_chance:
                chunk[z["y"]][z["x"]] = ZOMBIE
                continue

            # Prefer chasing a Gold-Hunter in sight, else the player
            target = None
            best_d = SIGHT_RANGE + 1
            for g in self.guards:
                if g["chunk_x"] == cx and g["chunk_y"] == cy:
                    d = self._manhattan(z["x"], z["y"], g["x"], g["y"])
                    if d < best_d:
                        best_d = d
                        target = (g["x"], g["y"])
            d_player = self._manhattan(z["x"], z["y"], player.x, player.y)
            if target is None or d_player < best_d:
                if d_player <= SIGHT_RANGE:
                    target = (player.x, player.y)

            if target is not None:
                nx, ny = self._step_toward(z["x"], z["y"], target[0], target[1], chunk)
                z["x"], z["y"] = nx, ny
            else:
                nx, ny = self._random_step(z["x"], z["y"], chunk)
                z["x"], z["y"] = nx, ny

            chunk[z["y"]][z["x"]] = ZOMBIE
