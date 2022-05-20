# Cockroaches.py
# Adds little critters to the desktop that hide behind windows

# find visible windows and their rects
# spawn cockroaches randomly from outside the screen
# have them crawl behind any open window
# check if window rect changed
# if cockroach outside window rect, scurry to another window
# if cockroach is clicked, squish

import win32api, win32con, win32gui
from ctypes import windll, wintypes
import pygame
import sys, os
from screeninfo import get_monitors
import ctypes
import random
import math
from pynput import mouse

class Roach(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = get_image('new_roach.png')
        self.rect = self.image.get_rect()
        self.position = pygame.math.Vector2(0, 0)
        self.speed = 10
        self.update_target(new_target=True)
        self.dead = False
        self.frame_died = None

    def update(self):
        if self.dead:
            return

        global valid_windows

        # update rect in case window has moved
        self.update_target()

        # not hidden yet and moving towards target
        if not self.hidden:
            if contains(self.target_rect, self.rect):
                self.hidden = True
                play_sound('scuttle.mp3', stop=True)
            else:
                self.rotate()
                self.hunt_window()

        # was hidden and is now exposed
        if self.target_name is not None:
            if not contains(getWindowRectFromName(self.target_name), self.target_rect):
                self.update_target(new_target=True)
        elif valid_windows:
            self.update_target(new_target=True)

    def squish(self):
        play_sound('scuttle.mp3', stop=True)
        play_sound(random.choice(squish_sounds))
        self.image = get_image(random.choice(splatters))
        self.dead = True
        self.frame_died = framecount

    def hunt_window(self):
        window_position = self.target_rect.center
        direction = window_position - self.position
        velocity = direction.normalize() * self.speed

        self.position += velocity
        self.rect.center = self.position

    def rotate(self):
        rel_x, rel_y = self.target_rect.x - self.rect.x, self.target_rect.y - self.rect.y
        angle = (180 / math.pi) * -math.atan2(rel_y, rel_x)
        self.image = pygame.transform.rotate(original_image, int(angle))
        self.rect = self.image.get_rect(center=(self.rect.center))

    def update_target(self, new_target=False):
        global valid_windows
        if new_target:
            valid_windows = get_visible_windows()
            self.hidden = False
            play_sound('scuttle.mp3')
            if valid_windows:
                self.target_name = random.choice(valid_windows)
                window_rect = getWindowRectFromName(self.target_name)
                try:
                    x = random.randint(window_rect.x, window_rect.x + window_rect.w - self.rect.w)
                    y = random.randint(window_rect.y, window_rect.y + window_rect.h - self.rect.h)
                    self.target_rect = pygame.Rect(x, y, 300, 300)
                except Exception:  # idk, apparently randrange has empty value after minimizing a window with roaches behind it sometimes
                    self.target_name = None
                    self.target_rect = pygame.Rect(-1000, -1000, 500, 500)        
            else:
                self.target_name = None
                self.target_rect = pygame.Rect(-1000, -1000, 500, 500)

def contains(r1, r2):  # determines if rect1 is inside of rect2
   return r1.x < r2.x < r2.x+r2.w < r1.x+r1.w and r1.y < r2.y < r2.y+r2.h < r1.y+r1.h

def get_visible_windows():
    class TITLEBARINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.wintypes.DWORD), ("rcTitleBar", ctypes.wintypes.RECT),
                ("rgstate", ctypes.wintypes.DWORD * 6)]
    visible_windows = []
    def callback(hwnd, _):
        # Title Info Initialization
        title_info = TITLEBARINFO()
        title_info.cbSize = ctypes.sizeof(title_info)
        ctypes.windll.user32.GetTitleBarInfo(hwnd, ctypes.byref(title_info))

        # DWM Cloaked Check
        isCloaked = ctypes.c_int(0)
        ctypes.WinDLL("dwmapi").DwmGetWindowAttribute(hwnd, 14, ctypes.byref(isCloaked), ctypes.sizeof(isCloaked))

        # Variables
        title = win32gui.GetWindowText(hwnd)

        # Append title to list
        if not win32gui.IsIconic(hwnd) and win32gui.IsWindowVisible(hwnd) and title != '' and isCloaked.value == 0:
            if not (title_info.rgstate[0] & win32con.STATE_SYSTEM_INVISIBLE):
                if title not in invalid_windows:
                    #print(f'Title: {title}\nRect: {getWindowRectFromName(title)}\n\n')
                    visible_windows.append(title)
    win32gui.EnumWindows(callback, None)
    return visible_windows

def getWindowRectFromName(name:str)-> tuple:
    hwnd = windll.user32.FindWindowW(0, name)
    rect = wintypes.RECT()
    windll.user32.GetWindowRect(hwnd, ctypes.pointer(rect))
    return pygame.Rect(rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top)

def on_click(x, y, button, pressed):
    if button == mouse.Button.left:
        for roach in roaches:
            if roach.rect.collidepoint(x, y) and not roach.dead and not roach.hidden:
                roach.squish()

_image_library = {}
def get_image(path):
    global _image_library
    image = _image_library.get(path)
    if image == None:
        canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
        image = pygame.image.load('Assets/' + canonicalized_path)
        _image_library[path] = image
    return image

_sound_library = {}
def play_sound(path, stop=False):
    global _sound_library
    sound = _sound_library.get(path)
    if sound == None:
        canonicalized_path = path.replace('/', os.sep).replace('\\', os.sep)
        sound = pygame.mixer.Sound('Assets/' + canonicalized_path)
        _sound_library[path] = sound
    if stop:
        sound.stop()
    else:
        sound.play()


monitor = get_monitors()[0]
SCREEN_WIDTH = monitor.width
SCREEN_HEIGHT = monitor.height

# Init pygame and display
pygame.init()
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0, 0)  # set starting position
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption('Cockroaches')
clock = pygame.time.Clock()

SetWindowPos = windll.user32.SetWindowPos
SetWindowPos(
        pygame.display.get_wm_info()['window'], 1, 0, 0, 0, 0, 0x0001  # first int is z order
        )

# Set window transparency color
fuchsia = (255, 0, 128)
hwnd = win32gui.FindWindow(None, "Cockroaches")
lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
lExStyle |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, lExStyle)
win32gui.SetLayeredWindowAttributes(hwnd,
                                    win32api.RGB(*fuchsia), 0,
                                    win32con.LWA_COLORKEY)

invalid_windows = ['Setup', '*IDLE Shell 3.10.0*', 'Cockroaches', 'Microsoft Text Input Application', 'Paint 3D', 'NVIDIA GeForce Overlay', 'Untitled ‎- Paint 3D', 'Program Manager', 'Settings']
valid_windows = get_visible_windows()
#print(valid_windows)
squish_sounds = ['squish1.mp3', 'squish2.mp3']
splatters = ['splatter1.png', 'splatter2.png']
original_image = get_image('new_roach.png')  # base image for rotation
roaches = []
for x in range(5):
    roaches.append(Roach())

listener = mouse.Listener(on_click=on_click)
listener.start()

state_left = win32api.GetKeyState(0x01)
framecount = 0

while True:
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    for roach in roaches:
        roach.update()

        if roach.dead:
            if framecount - roach.frame_died >= 60*3:
                roaches.remove(roach)
                roaches.append(Roach())

    if framecount % 60*5 == 0:
        valid_windows = get_visible_windows()

    screen.fill(fuchsia)

    for roach in roaches:
        screen.blit(roach.image, (roach.rect.x, roach.rect.y))#, special_flags=pygame.BLEND_RGB_MULT)

    pygame.display.flip()
    clock.tick(60)
    framecount += 1
