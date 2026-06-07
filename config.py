"""Game configuration constants."""

SCREEN_W = 1024
SCREEN_H = 768
FPS = 60

GRID_CELL = 48

TARGET_W = 6
TARGET_H = 4

# Cakes vary in size: some smaller than a layer (24 cells), some larger.
# 9 cakes for 8 layers means 1 spare. Range is configurable for tuning.
CAKE_SIZE_MIN = 16
CAKE_SIZE_MAX = 28

TOTAL_CAKES = 9
LAYERS_NEEDED = 8

TARGET_ORIGIN = (320, 140)

INVENTORY_Y = 600
INVENTORY_SLOT_W = 96
INVENTORY_SLOT_H = 96
INVENTORY_PADDING = 8
INVENTORY_MARGIN = 16          # left/right gap between bar edge and the slot viewport
INVENTORY_SCROLLBAR_H = 10     # height of the horizontal scrollbar track
INVENTORY_WHEEL_STEP = 104     # px scrolled per mouse-wheel notch (~one slot)

STACK_ORIGIN = (40, 140)
STACK_SLOT_H = 24
STACK_SLOT_W = 220

DISCARD_RECT = (880, 380, 110, 100)

COLOR_BG = (245, 230, 200)
COLOR_TARGET_BG = (255, 248, 220)
COLOR_TARGET_BORDER = (180, 140, 80)
COLOR_GRID = (220, 200, 160)
COLOR_CAKE_FILL = (235, 195, 120)
COLOR_CAKE_BORDER = (140, 90, 30)
COLOR_CAKE_HOVER = (250, 215, 140)
COLOR_PLACED_FILL = (210, 165, 90)
COLOR_INVENTORY_BG = (220, 200, 170)
COLOR_INVENTORY_SLOT = (200, 180, 150)
COLOR_STACK_LAYER_DONE = (200, 150, 80)
COLOR_STACK_LAYER_EMPTY = (210, 200, 180)
COLOR_BUTTON = (180, 130, 60)
COLOR_BUTTON_HOVER = (210, 160, 80)
COLOR_BUTTON_TEXT = (255, 255, 255)
COLOR_TEXT = (60, 40, 20)
COLOR_DISCARD = (200, 100, 100)
COLOR_DISCARD_HOVER = (230, 120, 120)
COLOR_CUT_HINT = (255, 80, 80)
COLOR_CUT_VALID = (80, 200, 80)
COLOR_SCROLLBAR_TRACK = (200, 180, 150)
COLOR_SCROLLBAR_THUMB = (160, 120, 60)
COLOR_SCROLLBAR_THUMB_HOVER = (190, 145, 75)

# --- Cake breaking (cuts can crack) ---
# Break chance is interpolated by the cut piece's cell count between two anchors;
# smaller pieces are more fragile.
BREAK_SMALL_SIZE = 4       # <= this many cells -> BREAK_CHANCE_SMALL
BREAK_LARGE_SIZE = 24      # >= this many cells -> BREAK_CHANCE_LARGE
BREAK_CHANCE_SMALL = 0.6   # fragile small offcuts
BREAK_CHANCE_LARGE = 0.1   # sturdier big cakes
BREAK_JAGGEDNESS = 2       # max per-line deviation of a cracked cut (cells)
BREAK_CRUMB_CHANCE = 0.5   # given a break, chance that cells also crumble away
BREAK_CRUMB_MAX = 2        # max cells lost to crumbs

COLOR_CRUMB = (120, 70, 30)  # crumb flash color
CRUMB_FLASH_MS = 800
CUT_MESSAGE_MS = 2000

# --- Crumbs resource (decorate the napoleon top) ---
CRUMB_GOAL = TARGET_W * TARGET_H   # 24 crumb units fully decorate the napoleon top
COLOR_DECOR = (180, 120, 60)       # HUD color for crumb / decoration readout
