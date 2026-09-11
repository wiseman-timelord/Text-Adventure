from map import CHUNK_WIDTH, CHUNK_HEIGHT, WORLD_CHUNKS_X, WORLD_CHUNKS_Y, CENTER_CHUNK_X, CENTER_CHUNK_Y
from ascii import PLAYER, WALL, COIN, SHOP, ROCK, GUARD
import time


class Player:
    def __init__(self, start_x=None, start_y=None,
                 start_chunk_x=CENTER_CHUNK_X, start_chunk_y=CENTER_CHUNK_Y):
        self.x = start_x if start_x is not None else CHUNK_WIDTH // 2
        self.y = start_y if start_y is not None else CHUNK_HEIGHT // 2
        self.chunk_x = start_chunk_x
        self.chunk_y = start_chunk_y
        self.symbol = PLAYER

        # Inventory
        self.coins = 0
        self.doughnuts = 0
        self.cola = 0
        self.health = 100.0
        self.max_health = 100.0

        # Lifetime stats
        self.doughnuts_eaten = 0
        self.cola_drunk = 0
        self.shops_visited = 0
        self.coins_collected = 0
        self.start_time = time.time()

        self.inside_shop = False

    def move(self, dx, dy, world_map):
        new_x = self.x + dx
        new_y = self.y + dy
        new_chunk_x = self.chunk_x
        new_chunk_y = self.chunk_y

        if new_x < 0:
            if self.chunk_x <= 0:
                return False
            new_chunk_x -= 1
            new_x = CHUNK_WIDTH - 1
        elif new_x >= CHUNK_WIDTH:
            if self.chunk_x >= WORLD_CHUNKS_X - 1:
                return False
            new_chunk_x += 1
            new_x = 0

        if new_y < 0:
            if self.chunk_y <= 0:
                return False
            new_chunk_y -= 1
            new_y = CHUNK_HEIGHT - 1
        elif new_y >= CHUNK_HEIGHT:
            if self.chunk_y >= WORLD_CHUNKS_Y - 1:
                return False
            new_chunk_y += 1
            new_y = 0

        chunk = world_map.get_chunk(new_chunk_x, new_chunk_y)
        tile = chunk[new_y][new_x]

        if tile == WALL or tile == ROCK:
            return False

        if tile == GUARD:
            self.health = max(0.0, self.health - 8.0)
            return "guard"

        if self.inside_shop and tile != SHOP:
            self.inside_shop = False

        self.x = new_x
        self.y = new_y
        self.chunk_x = new_chunk_x
        self.chunk_y = new_chunk_y

        if tile == COIN:
            self.coins += 1
            self.coins_collected += 1
            world_map.remove_tile(self.chunk_x, self.chunk_y, new_x, new_y)
            world_map.mark_poi_discovered(
                self.chunk_x, self.chunk_y, "coin", new_x, new_y
            )
            return "coin"

        if tile == SHOP:
            world_map.mark_poi_discovered(
                self.chunk_x, self.chunk_y, "shop", new_x, new_y
            )
            return "shop"

        return True

    def try_buy(self, item):
        prices = {"doughnut": 1, "cola": 2}
        if item not in prices:
            return False, "Unknown item."
        cost = prices[item]
        if self.coins < cost:
            return False, f"Not enough coins! Need £{cost}."
        self.coins -= cost
        if item == "doughnut":
            self.doughnuts += 1
            return True, "Bought a Doughnut for £1! (use it from Inventory)"
        if item == "cola":
            self.cola += 1
            return True, "Bought a Cola for £2! (use it from Inventory)"
        return False, "Error."

    def use_item(self, item):
        if item == "doughnut":
            if self.doughnuts <= 0:
                return False, "No Doughnuts left."
            self.doughnuts -= 1
            self.doughnuts_eaten += 1
            restore = 12.0
            self.health = min(self.max_health, self.health + restore)
            return True, f"Ate a Doughnut! (+{restore:.0f} health)"
        if item == "cola":
            if self.cola <= 0:
                return False, "No Cola left."
            self.cola -= 1
            self.cola_drunk += 1
            restore = 12.0 * 1.75
            self.health = min(self.max_health, self.health + restore)
            return True, f"Drank a Cola! (+{restore:.0f} health)"
        return False, "Unknown item."

    def decay_health(self, amount=0.12):
        self.health = max(0.0, self.health - amount)
        return self.health <= 0.0

    def time_survived(self):
        return time.time() - self.start_time
