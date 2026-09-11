# Central repository for ASCII / Unicode tiles and graphics used in the game.

PLAYER = "@"
ROCK   = "o"
BUSH   = "*"
WALL   = "#"
EMPTY  = " "
WATER  = "~"
BOG    = "%"          # sticky brown ground – costs 2 presses to cross
COIN   = "£"
SHOP   = "$"
GUARD  = "G"          # Gold-Hunter – guards coins, flees zombies
ZOMBIE = "Z"          # Zombie – slow, chases player and gold-hunters

# Coin is rendered as the three-character sequence  ( £ )
COIN_LEFT  = "("
COIN_RIGHT = ")"

# Multi-line decorative art – stamped onto the map grid
BUILDINGS = {
    "small_house": [
        " /\\ ",
        "/__\\",
        "|  |",
    ],
    "shop": [
        "+----+",
        "|SHOP|",
        "+----+",
    ],
    "hut": [
        " /\\",
        "/||\\",
        " || ",
    ],
}

NATURE = {
    "pine_tree": [
        " /\\ ",
        "//\\\\",
        " || ",
    ],
    "tall_tree": [
        "  ^  ",
        " /|\\ ",
        "//|\\\\",
        "  |  ",
    ],
    "rocks_cluster": [
        " o ",
        "o o",
    ],
    "bush_cluster": [
        " * * ",
        "* * *",
    ],
    "cactus": [
        " Y ",
        " | ",
    ],
}

PEOPLE = {
    "villager": "i",
}

SHOP_DIALOG = """\
 -= The Shop =-

Cola       - £2 [Buy]
Doughnuts  - £1 [Buy]

   [Exit Shop]
"""

SHOP_DIALOG_SPECIAL = """\
 -= The Rocky Shop =-

Rocky-Road - £1 [Buy]   (1.5x doughnut heal)
Cola       - £2 [Buy]

   [Exit Shop]
"""

SHOP_SIGN = [
    ".-.",
    "|$|",
    "'-'",
]

WIN_BANNER = [
    "  *  *  *  *  *  *  *  *  *  ",
    " *  ALL COINS COLLECTED  * ",
    "  *  *  *  *  *  *  *  *  *  ",
]

if __name__ == "__main__":
    print("--- Tiles ---")
    for name in ["PLAYER", "ROCK", "BUSH", "WALL", "WATER", "BOG",
                 "COIN", "SHOP", "GUARD", "ZOMBIE"]:
        print(f"  {name:8} : {globals()[name]}")
