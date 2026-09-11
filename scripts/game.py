#!/usr/bin/env python3
"""
Text-Adventure – Qt GUI version
"""

import sys
import time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QLabel, QPushButton, QFrame, QDialog, QProgressBar,
    QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeyEvent, QTextCursor, QFontMetrics

from map import (
    Map, CHUNK_WIDTH, CHUNK_HEIGHT,
    WORLD_CHUNKS_X, WORLD_CHUNKS_Y, CENTER_CHUNK_X, CENTER_CHUNK_Y
)
from player import Player
from ascii import (
    SHOP_DIALOG, SHOP_DIALOG_SPECIAL,
    WATER, BOG, ROCK, BUSH, WALL, EMPTY, COIN, SHOP, GUARD,
    COIN_LEFT, COIN_RIGHT,
)


def monospace_font(size=11):
    font = QFont("Consolas")
    if not font.exactMatch():
        font = QFont("Courier New")
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    font.setFixedPitch(True)
    font.setPointSize(size)
    return font


TILE_COLORS = {
    WATER:      "#58a6ff",   # blue
    BOG:        "#8B5A2B",   # brown
    ROCK:       "#8b949e",   # light grey
    BUSH:       "#3fb950",   # green
    WALL:       "#484f58",
    EMPTY:      "#c9d1d9",
    COIN:       "#e3b341",   # gold
    COIN_LEFT:  "#e3b341",
    COIN_RIGHT: "#e3b341",
    SHOP:       "#010409",
    GUARD:      "#f85149",
    "@":        "#ffffff",
    "/":        "#3fb950",
    "\\":       "#3fb950",
    "|":        "#8b949e",
    "+":        "#d29922",
    "-":        "#d29922",
    "^":        "#3fb950",
    "Y":        "#3fb950",
    "S":        "#e3b341",
    "H":        "#e3b341",
    "O":        "#e3b341",
    "P":        "#e3b341",
    "_":        "#8b949e",
    "%":        "#8B5A2B",
}


def colorize_char(ch: str) -> str:
    color = TILE_COLORS.get(ch, "#c9d1d9")
    safe = ch.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if ch == " ":
        return "&nbsp;"
    return f'<span style="color:{color}">{safe}</span>'


# ---------------------------------------------------------------------------
#  Startup / Help Popup
# ---------------------------------------------------------------------------
class StartDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Text-Adventure")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.result_action = "quit"

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("Gameplay Map")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        help_text = QLabel(
            "Collect coins (£), avoid the Guardians (G).\n"
            "Find shops ($) to buy food and drink.\n"
            "One shop is already marked on the minimap –\n"
            "find the other for Rocky-Road (better value).\n"
            "Brown bogs (%) require two presses to cross.\n\n"
            "Collect EVERY coin in the world to win!\n\n"
            "Arrow keys move · R restarts · Q quits"
        )
        help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_text.setFont(QFont("Segoe UI", 11))
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        btn_row = QHBoxLayout()
        btn_new = QPushButton("[ New Game ]")
        btn_quit = QPushButton("[ Quit Game ]")
        btn_new.setMinimumHeight(36)
        btn_quit.setMinimumHeight(36)
        btn_new.clicked.connect(self._new_game)
        btn_quit.clicked.connect(self._quit_game)
        btn_row.addWidget(btn_new)
        btn_row.addWidget(btn_quit)
        layout.addLayout(btn_row)

        self._apply_style()

    def _new_game(self):
        self.result_action = "new"
        self.accept()

    def _quit_game(self):
        self.result_action = "quit"
        self.reject()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #c9d1d9; }
            QLabel { color: #e6edf3; }
            QPushButton {
                background-color: #21262d; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 6px; padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #30363d; }
            QPushButton:pressed { background-color: #1f6feb; }
        """)


# ---------------------------------------------------------------------------
#  Death / Stats Popup
# ---------------------------------------------------------------------------
class DeathDialog(QDialog):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Over")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.result_action = "quit"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("You collapsed from exhaustion...")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        secs = int(player.time_survived())
        mins, secs = divmod(secs, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"

        stats = QLabel(
            f"Time survived   : {time_str}\n"
            f"Coins collected : {player.coins_collected}\n"
            f"Doughnuts eaten : {player.doughnuts_eaten}\n"
            f"Rocky-Road eaten: {player.rocky_road_eaten}\n"
            f"Cola drunk      : {player.cola_drunk}\n"
            f"Shops visited   : {player.shops_visited}"
        )
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats.setFont(monospace_font(12))
        layout.addWidget(stats)

        btn_row = QHBoxLayout()
        btn_new = QPushButton("[ New Game ]")
        btn_quit = QPushButton("[ Quit Game ]")
        btn_new.setMinimumHeight(36)
        btn_quit.setMinimumHeight(36)
        btn_new.clicked.connect(self._new_game)
        btn_quit.clicked.connect(self._quit_game)
        btn_row.addWidget(btn_new)
        btn_row.addWidget(btn_quit)
        layout.addLayout(btn_row)

        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #c9d1d9; }
            QLabel { color: #e6edf3; }
            QPushButton {
                background-color: #21262d; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 6px; padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #30363d; }
            QPushButton:pressed { background-color: #1f6feb; }
        """)

    def _new_game(self):
        self.result_action = "new"
        self.accept()

    def _quit_game(self):
        self.result_action = "quit"
        self.reject()


# ---------------------------------------------------------------------------
#  Win Popup
# ---------------------------------------------------------------------------
class WinDialog(QDialog):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.setWindowTitle("You Win!")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.result_action = "quit"

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("★  VICTORY  ★")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        msg = QLabel(
            "Well done gamer, you have collected all the coins,\n"
            "WiseMan-TimeLord is impressed, not that not having\n"
            "done this would be unimpressive, but good job\n"
            "none the less."
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setFont(QFont("Segoe UI", 12))
        msg.setWordWrap(True)
        layout.addWidget(msg)

        secs = int(player.time_survived())
        mins, secs = divmod(secs, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"

        stats = QLabel(
            f"Time survived   : {time_str}\n"
            f"Coins collected : {player.coins_collected}\n"
            f"Doughnuts eaten : {player.doughnuts_eaten}\n"
            f"Rocky-Road eaten: {player.rocky_road_eaten}\n"
            f"Cola drunk      : {player.cola_drunk}\n"
            f"Shops visited   : {player.shops_visited}"
        )
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats.setFont(monospace_font(12))
        layout.addWidget(stats)

        btn_row = QHBoxLayout()
        btn_new = QPushButton("[ New Game ]")
        btn_quit = QPushButton("[ Quit Game ]")
        btn_new.setMinimumHeight(36)
        btn_quit.setMinimumHeight(36)
        btn_new.clicked.connect(self._new_game)
        btn_quit.clicked.connect(self._quit_game)
        btn_row.addWidget(btn_new)
        btn_row.addWidget(btn_quit)
        layout.addLayout(btn_row)

        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #c9d1d9; }
            QLabel { color: #e6edf3; }
            QPushButton {
                background-color: #21262d; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 6px; padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #30363d; }
            QPushButton:pressed { background-color: #1f6feb; }
        """)

    def _new_game(self):
        self.result_action = "new"
        self.accept()

    def _quit_game(self):
        self.result_action = "quit"
        self.reject()


# ---------------------------------------------------------------------------
#  Shop Popup
# ---------------------------------------------------------------------------
class ShopDialog(QDialog):
    def __init__(self, player, special=False, parent=None):
        super().__init__(parent)
        self.player = player
        self.special = special
        self.setWindowTitle("The Rocky Shop" if special else "The Shop")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        dialog_text = SHOP_DIALOG_SPECIAL if special else SHOP_DIALOG
        info = QLabel(dialog_text)
        info.setFont(monospace_font(12))
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label)

        if special:
            btn_rocky = QPushButton("Buy Rocky-Road (£1)")
            btn_rocky.clicked.connect(lambda: self._buy("rocky_road"))
            layout.addWidget(btn_rocky)
        else:
            btn_doughnut = QPushButton("Buy Doughnuts (£1)")
            btn_doughnut.clicked.connect(lambda: self._buy("doughnut"))
            layout.addWidget(btn_doughnut)

        btn_cola = QPushButton("Buy Cola (£2)")
        btn_cola.clicked.connect(lambda: self._buy("cola"))
        layout.addWidget(btn_cola)

        btn_exit = QPushButton("Exit Shop")
        btn_exit.clicked.connect(self.reject)
        layout.addWidget(btn_exit)

        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #c9d1d9; }
            QLabel { color: #e6edf3; }
            QPushButton {
                background-color: #21262d; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 4px; padding: 8px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)

    def _buy(self, item):
        success, msg = self.player.try_buy(item, special_shop=self.special)
        self.result_label.setText(msg)


# ---------------------------------------------------------------------------
#  Main Window
# ---------------------------------------------------------------------------
class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text-Adventure")
        self.resize(1680, 960)
        self.setMinimumSize(900, 600)

        self.world_map = None
        self.player = None
        self.status_message = ""
        self.shop_dialog_open = False
        self.game_active = False
        self._map_font_size = 10
        self._won = False

        self._build_ui()

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self._game_tick)

        # Show the main window immediately so it is visible behind the dialog
        self.show()
        # Process events so the window actually paints before the modal dialog
        QApplication.processEvents()

        self._show_start_dialog()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Text-Adventure")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_layout.addWidget(title)

        self.world_view = QTextEdit()
        self.world_view.setReadOnly(True)
        self.world_view.setFont(monospace_font(10))
        self.world_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.world_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.world_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.world_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.world_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.world_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.world_view, stretch=1)

        self.status_bar = QLabel()
        self.status_bar.setWordWrap(True)
        self.status_bar.setStyleSheet(
            "background:#1e1e1e; color:#d4d4d4; padding:6px; border-radius:4px;"
        )
        left_layout.addWidget(self.status_bar)

        health_row = QHBoxLayout()
        health_row.addWidget(QLabel("Health:"))
        self.health_bar = QProgressBar()
        self.health_bar.setRange(0, 100)
        self.health_bar.setValue(100)
        self.health_bar.setTextVisible(True)
        self.health_bar.setFormat("%v / 100")
        health_row.addWidget(self.health_bar, stretch=1)
        left_layout.addLayout(health_row)

        main_layout.addWidget(left_frame, stretch=5)

        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.Shape.StyledPanel)
        right_frame.setMinimumWidth(220)
        right_frame.setMaximumWidth(320)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(6)

        map_box = QVBoxLayout()
        map_label = QLabel("World Map")
        map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        map_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        map_box.addWidget(map_label)

        self.minimap = QTextEdit()
        self.minimap.setReadOnly(True)
        self.minimap.setFont(monospace_font(10))
        self.minimap.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.minimap.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.minimap.setStyleSheet("background:#0d1117; color:#c9d1d9;")
        self.minimap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.minimap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        map_box.addWidget(self.minimap)
        right_layout.addLayout(map_box, stretch=1)

        char_box = QVBoxLayout()
        char_label = QLabel("CHARACTER")
        char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        char_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        char_box.addWidget(char_label)

        self.char_view = QTextEdit()
        self.char_view.setReadOnly(True)
        self.char_view.setFont(monospace_font(10))
        self.char_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.char_view.setStyleSheet("background:#161b22; color:#e6edf3;")
        self.char_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        char_box.addWidget(self.char_view)
        right_layout.addLayout(char_box, stretch=1)

        inv_box = QVBoxLayout()
        inv_label = QLabel("INVENTORY  (click to use)")
        inv_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inv_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        inv_box.addWidget(inv_label)

        self.inventory_list = QListWidget()
        self.inventory_list.setFont(monospace_font(10))
        self.inventory_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.inventory_list.setStyleSheet("""
            QListWidget {
                background:#161b22; color:#e6edf3;
                border: 1px solid #30363d; border-radius: 4px;
            }
            QListWidget::item:hover { background:#30363d; }
            QListWidget::item:selected { background:#1f6feb; }
        """)
        self.inventory_list.itemClicked.connect(self._on_inventory_click)
        self.inventory_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        inv_box.addWidget(self.inventory_list)

        btn_box = QHBoxLayout()
        self.btn_restart = QPushButton("Restart (R)")
        self.btn_quit = QPushButton("Quit (Q)")
        self.btn_restart.clicked.connect(self._restart)
        self.btn_quit.clicked.connect(self.close)
        btn_box.addWidget(self.btn_restart)
        btn_box.addWidget(self.btn_quit)
        inv_box.addLayout(btn_box)

        right_layout.addLayout(inv_box, stretch=1)
        main_layout.addWidget(right_frame, stretch=1)

        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0d1117; color: #c9d1d9; }
            QFrame { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }
            QPushButton {
                background-color: #21262d; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 4px; padding: 6px;
            }
            QPushButton:hover { background-color: #30363d; }
            QPushButton:pressed { background-color: #1f6feb; }
            QTextEdit { border: none; }
            QLabel { color: #8b949e; }
            QProgressBar {
                border: 1px solid #30363d; border-radius: 4px;
                text-align: center; background: #21262d; color: #e6edf3;
            }
            QProgressBar::chunk { background-color: #238636; border-radius: 3px; }
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_map_font()
        if self.player:
            self._refresh_all()

    def _adjust_map_font(self):
        if not hasattr(self, "world_view"):
            return
        viewport = self.world_view.viewport()
        avail_w = max(100, viewport.width() - 8)
        avail_h = max(80, viewport.height() - 8)

        lo, hi = 4, 28
        best = 6
        while lo <= hi:
            mid = (lo + hi) // 2
            font = monospace_font(mid)
            fm = QFontMetrics(font)
            char_w = fm.horizontalAdvance("M")
            line_h = fm.lineSpacing()
            if char_w * CHUNK_WIDTH <= avail_w and line_h * CHUNK_HEIGHT <= avail_h:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        if best != self._map_font_size:
            self._map_font_size = best
            self.world_view.setFont(monospace_font(best))

    def _show_start_dialog(self):
        dlg = StartDialog(self)
        result = dlg.exec()
        if dlg.result_action == "new":
            self._start_new_game()
        else:
            self.close()

    def _show_death_dialog(self):
        self.tick_timer.stop()
        self.game_active = False
        dlg = DeathDialog(self.player, self)
        result = dlg.exec()
        if dlg.result_action == "new":
            self._start_new_game()
        else:
            self.close()

    def _show_win_dialog(self):
        self.tick_timer.stop()
        self.game_active = False
        self._won = True
        dlg = WinDialog(self.player, self)
        result = dlg.exec()
        if dlg.result_action == "new":
            self._start_new_game()
        else:
            self.close()

    def _start_new_game(self):
        self.world_map = Map()
        self.player = Player()
        self.world_map.get_chunk(self.player.chunk_x, self.player.chunk_y)
        self.status_message = (
            "Good luck! Explore the world and collect every coin to win. "
            "One shop is marked on the minimap."
        )
        self.shop_dialog_open = False
        self.game_active = True
        self._won = False
        self._adjust_map_font()
        self._refresh_all()
        self.setFocus()
        self.tick_timer.start(250)

    def _refresh_all(self):
        if not self.player:
            return
        self._draw_world()
        self._draw_minimap()
        self._draw_character()
        self._draw_inventory()
        self._update_status_and_health()

    def _draw_world(self):
        chunk = self.world_map.get_chunk(self.player.chunk_x, self.player.chunk_y)
        html_lines = []
        for y, row in enumerate(chunk):
            parts = []
            for x, tile in enumerate(row):
                if x == self.player.x and y == self.player.y:
                    parts.append(colorize_char("@"))
                else:
                    parts.append(colorize_char(tile))
            html_lines.append("".join(parts))
        body = "<br>".join(html_lines)
        html = (
            f'<div style="font-family:Consolas,Courier New,monospace;'
            f'font-size:{self._map_font_size}pt; line-height:1.0;'
            f'white-space:pre; text-align:center;">'
            f'{body}</div>'
        )
        self.world_view.setHtml(html)
        cursor = self.world_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.world_view.setTextCursor(cursor)

    def _draw_minimap(self):
        lines = []
        for cy in range(WORLD_CHUNKS_Y):
            row = []
            for cx in range(WORLD_CHUNKS_X):
                if (cx, cy) not in self.world_map.chunks:
                    row.append(".")
                    continue
                symbol = "."
                if (cx, cy) == (CENTER_CHUNK_X, CENTER_CHUNK_Y):
                    symbol = "S"
                if (cx, cy) == (self.player.chunk_x, self.player.chunk_y):
                    symbol = "X"
                pois = self.world_map.discovered_pois.get((cx, cy), set())
                has_shop = any(p[0] == "shop" for p in pois)
                coins_left = self.world_map.coins_remaining.get((cx, cy), 0)
                has_coin = any(p[0] == "coin" for p in pois) and coins_left > 0
                if has_shop:
                    symbol = "$"
                elif has_coin and symbol not in ("X", "S"):
                    symbol = "£"
                row.append(symbol)
            lines.append("  ".join(row))
        grid = "\n".join(lines)
        remaining = sum(self.world_map.coins_remaining.values())
        header = (
            f"S=Start  X=You  $=Shop  £=Coin\n"
            f"Coins left: {remaining} / {self.world_map.total_coins}\n\n"
        )
        self.minimap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minimap.setPlainText(header + grid)

    def _draw_character(self):
        remaining = sum(self.world_map.coins_remaining.values())
        text = (
            f"Pos   : ({self.player.x}, {self.player.y})\n"
            f"Chunk : ({self.player.chunk_x}, {self.player.chunk_y})\n"
            f"\n"
            f"  £ Coins : {self.player.coins}\n"
            f"  Collected : {self.player.coins_collected}\n"
            f"  Remaining : {remaining}\n"
        )
        self.char_view.setPlainText(text)

    def _draw_inventory(self):
        self.inventory_list.clear()
        if self.player.doughnuts > 0:
            item = QListWidgetItem(f"  Doughnut    : {self.player.doughnuts}   [click to eat]")
            item.setData(Qt.ItemDataRole.UserRole, "doughnut")
            self.inventory_list.addItem(item)
        else:
            self.inventory_list.addItem(QListWidgetItem("  Doughnut    : 0"))
        if self.player.rocky_road > 0:
            item = QListWidgetItem(f"  Rocky-Road  : {self.player.rocky_road}   [click to eat]")
            item.setData(Qt.ItemDataRole.UserRole, "rocky_road")
            self.inventory_list.addItem(item)
        else:
            self.inventory_list.addItem(QListWidgetItem("  Rocky-Road  : 0"))
        if self.player.cola > 0:
            item = QListWidgetItem(f"  Cola        : {self.player.cola}   [click to drink]")
            item.setData(Qt.ItemDataRole.UserRole, "cola")
            self.inventory_list.addItem(item)
        else:
            self.inventory_list.addItem(QListWidgetItem("  Cola        : 0"))

    def _on_inventory_click(self, item: QListWidgetItem):
        kind = item.data(Qt.ItemDataRole.UserRole)
        if not kind or not self.game_active:
            return
        success, msg = self.player.use_item(kind)
        self.status_message = msg
        self._refresh_all()
        self.setFocus()

    def _update_status_and_health(self):
        self.status_bar.setText(self.status_message)
        hp = int(self.player.health)
        self.health_bar.setValue(hp)
        if hp > 60:
            color = "#238636"
        elif hp > 30:
            color = "#d29922"
        else:
            color = "#da3633"
        self.health_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #30363d; border-radius: 4px;
                text-align: center; background: #21262d; color: #e6edf3;
            }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}
        """)

    def _game_tick(self):
        if not self.game_active or self.shop_dialog_open or self._won:
            return
        dead = self.player.decay_health(0.10)
        if dead:
            self._show_death_dialog()
            return
        speed = 1.0 + self.player.coins * 0.08
        self.world_map.move_guards(self.player, speed_factor=speed)
        self._refresh_all()

    def keyPressEvent(self, event: QKeyEvent):
        if not self.game_active or self.shop_dialog_open or self._won:
            return
        key = event.key()
        result = None

        if key == Qt.Key.Key_Up:
            result = self.player.move(0, -1, self.world_map)
        elif key == Qt.Key.Key_Down:
            result = self.player.move(0, 1, self.world_map)
        elif key == Qt.Key.Key_Left:
            result = self.player.move(-1, 0, self.world_map)
        elif key == Qt.Key.Key_Right:
            result = self.player.move(1, 0, self.world_map)
        elif key == Qt.Key.Key_R:
            self._restart()
            return
        elif key == Qt.Key.Key_Q:
            self.close()
            return
        else:
            super().keyPressEvent(event)
            return

        if result == "coin":
            remaining = sum(self.world_map.coins_remaining.values())
            self.status_message = (
                f"Picked up a pound coin!  "
                f"(Held: £{self.player.coins}  Left in world: {remaining})"
            )
            if self.world_map.all_coins_collected():
                self._refresh_all()
                self._show_win_dialog()
                return
        elif result == "shop":
            if not self.player.inside_shop:
                self.player.inside_shop = True
                self.player.shops_visited += 1
                spawned = self.world_map.notify_shop_visit(self.player)
                if spawned:
                    self.status_message = "Shop visited – a new guardian stirs somewhere nearby…"
                else:
                    self.status_message = "Shop visited."
                self._open_shop()
            else:
                self.status_message = "You are in the shop."
        elif result == "guard":
            self.status_message = "Ouch! A guardian hit you. (-8 health)"
        elif result == "bog":
            self.status_message = "Squelch… the bog is sticky. Press again the same way to push through."
        elif result is False:
            self.status_message = "Blocked (wall or edge of the world)."
        else:
            self.status_message = (
                f"Pos ({self.player.x},{self.player.y})  "
                f"Chunk ({self.player.chunk_x},{self.player.chunk_y})"
            )
        self._refresh_all()

    def _open_shop(self):
        self.shop_dialog_open = True
        special = self.world_map.is_special_shop(
            self.player.chunk_x, self.player.chunk_y
        )
        dlg = ShopDialog(self.player, special=special, parent=self)
        dlg.exec()
        self.shop_dialog_open = False
        self.setFocus()
        self._refresh_all()

    def _restart(self):
        self.tick_timer.stop()
        self._start_new_game()

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GameWindow()
    # window already shown inside __init__ before the start dialog
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
