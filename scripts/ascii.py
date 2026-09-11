# Central repository for ASCII / Unicode tiles and graphics used in the game.

PLAYER = "@"
ROCK   = "o"
BUSH   = "*"
WALL   = "#"
EMPTY  = " "
WATER  = "~"
COIN   = "£"
SHOP   = "$"
GUARD  = "G"          # coin guardian

# Multi-line decorative art
BUILDINGS = {
    "small_house": [
        " /\\ ",
        "/__\\",
    ],
    "shop": [
        "+----+",
        "|SHOP|",
        "+----+",
    ],
}

NATURE = {
    "pine_tree": [
        " /\\ ",
        "//\\\\",
    ],
    "rocks_cluster": [
        " o",
        "o o",
    ],
}

PEOPLE = {
    "villager": "i",
}

# Shop dialog graphic (exactly as requested)
SHOP_DIALOG = """\
 -= The Shop =-

Cola      - £2 [Buy]

Doughnuts - £1 [Buy]

   [Exit Shop]
"""

if __name__ == "__main__":
    print("--- Tiles ---")
    for name in ["PLAYER", "ROCK", "BUSH", "WALL", "WATER", "COIN", "SHOP", "GUARD"]:
        print(f"  {name:8} : {globals()[name]}")
    print("\n--- Shop Dialog ---")
    print(SHOP_DIALOG)
