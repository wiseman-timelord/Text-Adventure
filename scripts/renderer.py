import blessed


class Renderer:
    """
    Handles all rendering tasks for the game, drawing the map, player,
    and UI elements to the terminal.
    """

    def __init__(self, term: blessed.Terminal):
        """
        Initializes the renderer with a blessed.Terminal instance.

        Args:
            term (blessed.Terminal): The blessed terminal object.
        """
        self.term = term

    def draw(self, player, world_map):
        """
        Draws the entire game state to the screen.

        This method should be called on every frame of the game loop. It clears
        the screen, draws the current map chunk, the player, and any UI.

        Args:
            player (Player): The player object.
            world_map (Map): The world map object.
        """
        # Build a single large string and print it once for better performance.
        output = self.term.home + self.term.clear

        # Get the current map chunk that the player is in.
        chunk_data = world_map.get_chunk(player.chunk_x, player.chunk_y)

        # Draw the map chunk.
        for y, row in enumerate(chunk_data):
            output += self.term.move_xy(0, y) + "".join(row)

        # Draw the player on top of the map.
        output += self.term.move_xy(player.x, player.y) + self.term.bold(player.symbol)

        # Draw a simple UI with debug information at the bottom of the screen.
        height, width = self.term.height, self.term.width
        ui_text = (
            f"Coords: ({player.x}, {player.y}) | "
            f"Chunk: ({player.chunk_x}, {player.chunk_y}) | "
            f"Press 'k' for keys / 'q' to quit"
        )
        # Ensure text doesn't wrap
        if len(ui_text) >= width:
            ui_text = ui_text[: width - 1]

        output += self.term.move_xy(0, height - 1) + self.term.on_black(ui_text)

        # Print the composed frame to the screen.
        print(output, end="", flush=True)

    def draw_map_screen(self, player, world_map):
        """
        Draws a high-level map showing visited chunks.
        """
        output = self.term.home + self.term.clear

        visited_chunks = list(world_map.chunks.keys())
        if not visited_chunks:
            text = "You haven't explored yet. Press 'm' to return."
            x = (self.term.width - len(text)) // 2
            y = self.term.height // 2
            output += self.term.move_xy(x, y) + text
            print(output, end="", flush=True)
            return

        # Determine the boundaries of the map to draw
        min_x = min(cx for cx, cy in visited_chunks)
        max_x = max(cx for cx, cy in visited_chunks)
        min_y = min(cy for cx, cy in visited_chunks)
        max_y = max(cy for cx, cy in visited_chunks)

        # Center the map display on the screen
        map_render_width = (max_x - min_x + 1) * 4
        map_render_height = (max_y - min_y + 1) * 2
        offset_x = (self.term.width - map_render_width) // 2
        offset_y = (self.term.height - map_render_height) // 2

        # Draw each visited chunk
        for r_y, chunk_y in enumerate(range(min_y, max_y + 1)):
            for r_x, chunk_x in enumerate(range(min_x, max_x + 1)):
                if (chunk_x, chunk_y) in visited_chunks:
                    screen_x = offset_x + r_x * 4
                    screen_y = offset_y + r_y * 2

                    symbol = "[ ]"
                    if (chunk_x, chunk_y) == (0, 0):  # Start chunk
                        symbol = "[S]"
                    if (chunk_x, chunk_y) == (player.chunk_x, player.chunk_y):  # Current chunk
                        symbol = self.term.bold("[X]")

                    output += self.term.move_xy(screen_x, screen_y) + symbol

                    # Draw connections to adjacent visited chunks
                    if (chunk_x + 1, chunk_y) in visited_chunks:
                        output += self.term.move_xy(screen_x + 3, screen_y) + "-"
                    if (chunk_x, chunk_y + 1) in visited_chunks:
                        output += self.term.move_xy(screen_x + 1, screen_y + 1) + "|"

        # Draw UI
        height, width = self.term.height, self.term.width
        ui_text = "MAP VIEW | 'S' = Start, 'X' = Current | Press 'm' to return to game."
        if len(ui_text) >= width:
            ui_text = ui_text[: width - 1]
        output += self.term.move_xy(0, height - 1) + self.term.on_black(ui_text)

        print(output, end="", flush=True)

    def draw_keys_screen(self):
        """
        Draws a screen displaying the game's keybindings.
        """
        output = self.term.home + self.term.clear

        # Define the content to be displayed
        title = "--- KEYBINDINGS ---"
        keys = [
            " k : Toggle this Keys Screen",
            " m : Toggle World Map",
            " r : Restart the Game",
            " q : Quit the Game",
            "",
            " Arrow Keys : Move Player",
        ]

        # Center the content block on the screen
        start_y = (self.term.height - len(keys) - 2) // 2

        # Draw the title
        title_x = (self.term.width - len(title)) // 2
        output += self.term.move_xy(title_x, start_y) + self.term.bold(title)

        # Draw each keybinding line
        for i, line in enumerate(keys):
            line_x = (self.term.width - len(line)) // 2
            output += self.term.move_xy(line_x, start_y + 2 + i) + line

        # Draw a UI hint at the bottom
        height, width = self.term.height, self.term.width
        ui_text = "Press 'k' to return to the game."
        if len(ui_text) >= width:
            ui_text = ui_text[: width - 1]
        output += self.term.move_xy(0, height - 1) + self.term.on_black(ui_text)

        print(output, end="", flush=True)


# This file is a module and is not intended to be run directly.
if __name__ == "__main__":
    print("This is the renderer module. It should be imported, not run directly.")
