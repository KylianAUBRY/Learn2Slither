#!/usr/bin/python3
"""
snake.py - Learn2Slither, centre de controle graphique (Pygame).

Interface unique pour tous les "executables" du sujet :
  - onglet SCENARIOS   : boutons un-clic (entrainer 1/10/100/1000/10000
                         sessions, regarder un modele, pas-a-pas, evaluer)
  - onglet PERSONNALISE: configuration fine de main.py (tous les flags)
  - onglet MODELES     : parcourir models/*.txt, regarder / evaluer

Chaque action lance `main.py` en sous-processus avec les bons arguments ;
la sortie s'affiche en direct dans le journal en bas de la fenetre.

Lancer :  .venv/bin/python snake.py   (pygame requis)
"""

import collections
import glob
import json
import os
import subprocess
import sys
import threading

try:
    import pygame
except ModuleNotFoundError:
    # pygame absent du Python courant (ex: 3.14) : on relance avec le
    # Python du venv s'il existe, sinon message clair.
    _venv = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '.venv', 'bin', 'python')
    if (os.path.exists(_venv)
            and os.path.realpath(_venv)
            != os.path.realpath(sys.executable)):
        os.execv(_venv, [_venv] + sys.argv)
    sys.exit(
        'pygame introuvable. Lancez :  .venv/bin/python snake.py\n'
        'ou installez-le :  pip install pygame  '
        '(Python 3.12 ou 3.13 recommande).')

# --- Palette -----------------------------------------------------------
C_BG = (13, 14, 28)
C_BG2 = (18, 20, 38)
C_PANEL = (22, 25, 48)
C_CARD = (28, 33, 62)
C_CARD_HOV = (42, 50, 92)
C_WIDGET = (32, 38, 74)
C_WIDGET_HOV = (50, 58, 108)
C_ACCENT = (233, 69, 96)
C_ACCENT_HOV = (255, 99, 124)
C_CYAN = (83, 216, 251)
C_GREEN = (80, 220, 120)
C_AMBER = (255, 200, 80)
C_FG = (236, 238, 248)
C_DIM = (132, 136, 170)
C_LINE = (40, 45, 82)
C_QUIT = (44, 44, 78)
C_QUIT_HOV = (74, 74, 116)

W, H = 900, 828
PAD = 24
FPS = 60

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption('Learn2Slither - Centre de controle')
clock = pygame.time.Clock()


def _font(size, bold=False, mono=False):
    if mono:
        names = ('Menlo', 'Monaco', 'Courier New', 'DejaVu Sans Mono')
    else:
        names = ('Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans')
    for name in names:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)


F_TITLE = _font(30, bold=True)
F_SUB = _font(13)
F_TAB = _font(15, bold=True)
F_SEC = _font(13, bold=True)
F_H = _font(17, bold=True)
F_BODY = _font(13)
F_SMALL = _font(11)
F_BTN = _font(13, bold=True)
F_BTN_LG = _font(16, bold=True)
F_MONO = _font(12, mono=True)
F_MONO_SM = _font(11, mono=True)


def draw_rect(surf, color, rect, radius=8):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def blit_text(surf, txt, font, color, x, y, anchor='topleft'):
    s = font.render(str(txt), True, color)
    r = s.get_rect(**{anchor: (x, y)})
    surf.blit(s, r)
    return r


def hline(surf, y, x0, x1, color=C_LINE, thick=1):
    pygame.draw.line(surf, color, (x0, y), (x1, y), thick)


def find_best_model():
    """Meilleur modele disponible (le plus entraine)."""
    prefer = [
        'models/10000sess.txt', 'models/1000sess.txt',
        'models/100sess.txt', 'models/10sess.txt', 'models/1sess.txt',
    ]
    for p in prefer:
        if os.path.exists(p):
            return p
    rest = sorted(glob.glob('models/*.txt'))
    return rest[0] if rest else 'models/10000sess.txt'


def model_info(path):
    """(nb_etats, epsilon, kilo-octets) ou None si illisible."""
    try:
        with open(path) as f:
            data = json.load(f)
        states = len(data.get('q_table', {}))
        eps = float(data.get('epsilon', 0.0))
        kb = os.path.getsize(path) / 1024.0
        return states, eps, kb
    except Exception:
        return None


# --- Widgets -----------------------------------------------------------
class Button:
    def __init__(self, rect, label, color=C_WIDGET, hover=C_WIDGET_HOV,
                 font=F_BTN, fg=C_FG, radius=7):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.hover = hover
        self.font = font
        self.fg = fg
        self.radius = radius
        self._hov = False

    def update(self, mx, my):
        self._hov = self.rect.collidepoint(mx, my)

    def draw(self, surf):
        col = self.hover if self._hov else self.color
        draw_rect(surf, col, self.rect, self.radius)
        blit_text(surf, self.label, self.font, self.fg,
                  self.rect.centerx, self.rect.centery, anchor='center')

    def clicked(self, ev):
        return (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.rect.collidepoint(ev.pos))


class Slider:
    def __init__(self, x, y, w, lo, hi, value):
        self.x, self.y, self.w = x, y, w
        self.lo, self.hi, self.value = lo, hi, value
        self._drag = False
        self.h = 6

    def _val_to_x(self):
        frac = (self.value - self.lo) / (self.hi - self.lo)
        return int(self.x + frac * self.w)

    def update(self, mx, my, buttons):
        if buttons[0]:
            tx = self._val_to_x()
            thumb = pygame.Rect(tx - 8, self.y - 8, 16, 22)
            if self._drag or thumb.collidepoint(mx, my):
                self._drag = True
                frac = max(0, min(1, (mx - self.x) / self.w))
                self.value = int(self.lo + frac * (self.hi - self.lo))
        else:
            self._drag = False

    def draw(self, surf):
        draw_rect(surf, C_WIDGET, (self.x, self.y, self.w, self.h), 3)
        fill = self._val_to_x() - self.x
        if fill > 0:
            draw_rect(surf, C_CYAN, (self.x, self.y, fill, self.h), 3)
        tx = self._val_to_x()
        draw_rect(surf, C_ACCENT, (tx - 7, self.y - 7, 14, 20), 4)
        blit_text(surf, str(self.value), F_SMALL, C_CYAN,
                  self.x + self.w, self.y - 14, anchor='midright')


class Dropdown:
    def __init__(self, x, y, w, choices, value=None):
        self.x, self.y, self.w = x, y, w
        self.choices = choices
        self.idx = choices.index(value) if value in choices else 0
        self.open = False
        self.h = 28
        self.rect = pygame.Rect(x, y, w, self.h)

    @property
    def value(self):
        return self.choices[self.idx]

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.open = not self.open
            elif self.open:
                for i in range(len(self.choices)):
                    ry = self.y + self.h * (i + 1)
                    if pygame.Rect(self.x, ry, self.w,
                                   self.h).collidepoint(ev.pos):
                        self.idx = i
                        self.open = False
                        return
                self.open = False

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hov = self.rect.collidepoint(mx, my)
        draw_rect(surf, C_WIDGET_HOV if hov else C_WIDGET, self.rect, 5)
        blit_text(surf, self.value, F_BODY, C_FG, self.x + 10,
                  self.y + 14, anchor='midleft')
        cx = self.x + self.w - 16
        cy = self.y + self.h // 2
        if self.open:
            pts = [(cx - 5, cy + 2), (cx + 5, cy + 2), (cx, cy - 4)]
        else:
            pts = [(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy + 4)]
        pygame.draw.polygon(surf, C_CYAN, pts)

    def draw_open(self, surf):
        if not self.open:
            return
        mx, my = pygame.mouse.get_pos()
        for i, ch in enumerate(self.choices):
            ry = self.y + self.h * (i + 1)
            item = pygame.Rect(self.x, ry, self.w, self.h)
            hov = item.collidepoint(mx, my)
            col = C_WIDGET_HOV if (hov or i == self.idx) else (25, 30, 60)
            draw_rect(surf, col, item, 0)
            tc = C_CYAN if i == self.idx else C_FG
            blit_text(surf, ch, F_BODY, tc, self.x + 10, ry + 14,
                      anchor='midleft')


class Checkbox:
    def __init__(self, x, y, label, checked=False):
        self.x, self.y, self.label = x, y, label
        self.checked = checked
        self.box = pygame.Rect(x, y, 18, 18)

    def handle(self, ev):
        if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.box.collidepoint(ev.pos)):
            self.checked = not self.checked

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hov = self.box.collidepoint(mx, my)
        draw_rect(surf, C_WIDGET_HOV if hov else C_WIDGET, self.box, 3)
        if self.checked:
            cx, cy = self.box.x, self.box.y
            pygame.draw.lines(surf, C_GREEN, False, [
                (cx + 4, cy + 9), (cx + 8, cy + 13), (cx + 14, cy + 4),
            ], 2)
        blit_text(surf, self.label, F_BODY, C_FG, self.x + 26,
                  self.y + 9, anchor='midleft')


class TextInput:
    def __init__(self, x, y, w, placeholder=''):
        self.rect = pygame.Rect(x, y, w, 26)
        self.ph = placeholder
        self.value = ''
        self.active = False

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(ev.pos)
        if self.active and ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif ev.key == pygame.K_RETURN:
                self.active = False
            elif ev.unicode and ev.unicode.isprintable():
                self.value += ev.unicode

    def draw(self, surf):
        draw_rect(surf, C_WIDGET, self.rect, 4)
        border = C_CYAN if self.active else C_LINE
        pygame.draw.rect(surf, border, self.rect, 1, border_radius=4)
        disp = self.value if self.value else self.ph
        col = C_FG if self.value else C_DIM
        max_w = self.rect.w - 12
        while F_SMALL.size(disp)[0] > max_w and len(disp) > 1:
            disp = disp[1:]
        blit_text(surf, disp, F_SMALL, col, self.rect.x + 7,
                  self.rect.centery, anchor='midleft')
        if self.active and pygame.time.get_ticks() % 1000 < 500:
            cx = self.rect.x + 7 + F_SMALL.size(disp)[0]
            pygame.draw.line(surf, C_FG, (cx, self.rect.y + 5),
                             (cx, self.rect.y + 21), 1)


# --- Sous-processus + journal -----------------------------------------
class Runner:
    """Lance main.py et capture sa sortie en direct (thread)."""

    def __init__(self):
        self.proc = None
        self.log = collections.deque(maxlen=6)
        self.lock = threading.Lock()
        self.status = 'Pret.'
        self.ok = True

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def launch(self, cmd, label):
        if self.is_running():
            self.status = 'Un processus tourne deja (Arreter d\'abord).'
            self.ok = False
            return
        try:
            with self.lock:
                self.log.clear()
            env = dict(os.environ, PYTHONUNBUFFERED='1')
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
            self.status = 'Lance : ' + label
            self.ok = True
            t = threading.Thread(target=self._reader,
                                 args=(self.proc,), daemon=True)
            t.start()
        except Exception as exc:
            self.status = str(exc)
            self.ok = False

    def _reader(self, proc):
        for raw in iter(proc.stdout.readline, ''):
            line = raw.rstrip('\n').rsplit('\r', 1)[-1].strip()
            if line:
                with self.lock:
                    self.log.append(line)
        proc.stdout.close()
        code = proc.wait()
        with self.lock:
            self.log.append('--- termine (code {}) ---'.format(code))

    def stop(self):
        if self.is_running():
            self.proc.terminate()
            self.status = 'Processus arrete.'
            self.ok = True
        else:
            self.status = 'Aucun processus en cours.'

    def snapshot(self):
        with self.lock:
            return list(self.log)


# --- Application -------------------------------------------------------
TABS = ['Scenarios', 'Personnalise', 'Modeles']

TRAIN_PRESETS = [1, 10, 100, 1000, 10000]
DEMOS = [
    ('watch', 'Regarder', 'Le meilleur modele joue\n(-dontlearn, visuel)',
     C_CYAN),
    ('step', 'Pas a pas', 'Avance coup par coup\n(SPACE, vision)', C_AMBER),
    ('eval', 'Evaluer x30', '30 parties sans apprendre\n(stats finales)',
     C_GREEN),
]


class App:

    def __init__(self):
        self.tab = 0
        self.runner = Runner()
        self.models = []
        exe = sys.executable

        # onglets
        self.tab_rects = [
            pygame.Rect(PAD + i * 156, 88, 150, 34)
            for i in range(len(TABS))
        ]

        # --- scenarios : rects ---
        self.train_rects = []
        for i in range(5):
            self.train_rects.append(
                pygame.Rect(24 + i * 173, 168, 160, 108))
        self.demo_rects = []
        for i in range(3):
            self.demo_rects.append(
                pygame.Rect(24 + i * 289, 326, 273, 120))

        # --- personnalise : widgets ---
        self.sl_sessions = Slider(44, 210, 360, 1, 10000, 100)
        self.dd_visual = Dropdown(44, 264, 150, ['on', 'off'], 'on')
        self.dd_speed = Dropdown(
            230, 264, 180, ['slow', 'normal', 'fast', 'max'], 'normal')
        self.sl_board = Slider(44, 348, 360, 5, 50, 10)
        self.ti_load = TextInput(470, 198, 320, 'models/10000sess.txt')
        self.btn_load_pick = Button((796, 196, 68, 26), 'Ouvrir',
                                    font=F_SMALL)
        self.ti_save = TextInput(470, 270, 320, 'models/nouveau.txt')
        self.btn_save_pick = Button((796, 268, 68, 26), 'Enreg',
                                    font=F_SMALL)
        self.cb_dontlearn = Checkbox(44, 460, '-dontlearn  (exploite)')
        self.cb_step = Checkbox(320, 460, '-step-by-step')
        self.btn_launch = Button((700, 524, 176, 46), 'LANCER',
                                 C_ACCENT, C_ACCENT_HOV, F_BTN_LG)

        # --- modeles ---
        self.btn_refresh = Button((740, 138, 136, 30), 'Rafraichir',
                                  font=F_SMALL)
        self.model_btns = []

        # --- barre du bas ---
        self.btn_stop = Button((736, 734, 140, 36), 'Arreter',
                               C_QUIT, C_QUIT_HOV, F_BTN)
        self.btn_quit = Button((736, 776, 140, 40), 'Quitter',
                               C_QUIT, C_QUIT_HOV, F_BTN)

        self.exe = exe
        self.refresh_models()

    # ---- modeles ----
    def refresh_models(self):
        self.models = []
        for path in sorted(glob.glob('models/*.txt')):
            self.models.append((path, model_info(path)))
        self.model_btns = []
        for i in range(len(self.models)):
            y = 184 + i * 86
            self.model_btns.append((
                Button((596, y + 24, 116, 38), 'Regarder',
                       C_WIDGET, C_WIDGET_HOV, F_BTN),
                Button((724, y + 24, 132, 38), 'Evaluer x30',
                       C_WIDGET, C_WIDGET_HOV, F_BTN),
            ))

    # ---- commandes ----
    def _cmd(self, *extra):
        return [self.exe, 'main.py'] + list(extra)

    def _run(self, cmd, label):
        if not os.path.exists('main.py'):
            self.runner.status = "main.py introuvable !"
            self.runner.ok = False
            return
        self.runner.launch(cmd, label)

    def run_train(self, n):
        path = 'models/{}sess.txt'.format(n)
        self._run(self._cmd('-sessions', str(n), '-visual', 'off',
                            '-save', path),
                  'Entrainement {} sessions -> {}'.format(n, path))

    def run_demo(self, kind):
        best = find_best_model()
        if not os.path.exists(best):
            self.runner.status = 'Aucun modele : entraine d\'abord.'
            self.runner.ok = False
            return
        if kind == 'watch':
            self._run(self._cmd('-load', best, '-dontlearn', '-visual',
                                'on', '-speed', 'fast', '-sessions', '3'),
                      'Demo : ' + best)
        elif kind == 'step':
            self._run(self._cmd('-load', best, '-dontlearn', '-visual',
                                'on', '-speed', 'slow', '-step-by-step',
                                '-sessions', '2'),
                      'Pas a pas : ' + best)
        elif kind == 'eval':
            self._run(self._cmd('-load', best, '-dontlearn', '-visual',
                                'off', '-sessions', '30'),
                      'Evaluation x30 : ' + best)

    def run_model(self, path, watch):
        if watch:
            self._run(self._cmd('-load', path, '-dontlearn', '-visual',
                                'on', '-speed', 'fast', '-sessions', '3'),
                      'Regarder : ' + path)
        else:
            self._run(self._cmd('-load', path, '-dontlearn', '-visual',
                                'off', '-sessions', '30'),
                      'Evaluer : ' + path)

    def build_custom(self):
        parts = self._cmd('-sessions', str(self.sl_sessions.value))
        parts += ['-visual', self.dd_visual.value]
        if self.dd_visual.value == 'on':
            parts += ['-speed', self.dd_speed.value]
        parts += ['-board-size', str(self.sl_board.value)]
        if self.ti_load.value.strip():
            parts += ['-load', self.ti_load.value.strip()]
        if self.ti_save.value.strip():
            parts += ['-save', self.ti_save.value.strip()]
        if self.cb_dontlearn.checked:
            parts.append('-dontlearn')
        if self.cb_step.checked:
            parts.append('-step-by-step')
        return parts

    def _models_dir(self):
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'models')

    def _pick_file(self, target, save=False):
        # tkinter cohabite mal avec pygame sur macOS (et n'est pas
        # toujours installe) : on prend le dialogue natif osascript,
        # avec repli tkinter en sous-processus sur les autres OS.
        if sys.platform == 'darwin':
            path = self._pick_macos(save)
        else:
            path = self._pick_tk(save)
        if path:
            target.value = path
        else:
            target.active = True  # annule/echec -> saisie manuelle

    def _pick_macos(self, save):
        loc = self._models_dir()
        if save:
            script = (
                'POSIX path of (choose file name'
                ' with prompt "Sauvegarder le modele"'
                ' default name "nouveau.txt"'
                ' default location (POSIX file "' + loc + '"))')
        else:
            script = (
                'POSIX path of (choose file'
                ' with prompt "Charger un modele"'
                ' default location (POSIX file "' + loc + '"))')
        try:
            out = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=120)
            return out.stdout.strip() or None
        except Exception:
            return None

    def _pick_tk(self, save):
        code = (
            'import tkinter as tk\n'
            'from tkinter import filedialog as fd\n'
            'r = tk.Tk(); r.withdraw()\n'
            'kw = {"initialdir": "models"}\n'
            'p = (fd.asksaveasfilename(**kw) if %s'
            ' else fd.askopenfilename(**kw))\n'
            'print(p or "")\n' % bool(save))
        try:
            out = subprocess.run(
                [sys.executable, '-c', code],
                capture_output=True, text=True, timeout=120)
            return out.stdout.strip() or None
        except Exception:
            return None

    # ---- evenements ----
    def handle(self, ev):
        for i, r in enumerate(self.tab_rects):
            if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                    and r.collidepoint(ev.pos)):
                self.tab = i
                self.dd_visual.open = self.dd_speed.open = False
        if self.btn_stop.clicked(ev):
            self.runner.stop()
        if self.btn_quit.clicked(ev):
            return False
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            return False
        if self.tab == 0:
            self._handle_scenarios(ev)
        elif self.tab == 1:
            self._handle_custom(ev)
        else:
            self._handle_models(ev)
        return True

    def _handle_scenarios(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(self.train_rects):
                if r.collidepoint(ev.pos):
                    self.run_train(TRAIN_PRESETS[i])
            for i, r in enumerate(self.demo_rects):
                if r.collidepoint(ev.pos):
                    self.run_demo(DEMOS[i][0])

    def _handle_custom(self, ev):
        self.dd_visual.handle(ev)
        if self.dd_visual.value == 'on':
            self.dd_speed.handle(ev)
        self.cb_dontlearn.handle(ev)
        self.cb_step.handle(ev)
        self.ti_load.handle(ev)
        self.ti_save.handle(ev)
        if self.btn_load_pick.clicked(ev):
            self._pick_file(self.ti_load, save=False)
        if self.btn_save_pick.clicked(ev):
            self._pick_file(self.ti_save, save=True)
        if self.btn_launch.clicked(ev):
            self._run(self.build_custom(), 'Configuration personnalisee')

    def _handle_models(self, ev):
        if self.btn_refresh.clicked(ev):
            self.refresh_models()
        for i, (b_watch, b_eval) in enumerate(self.model_btns):
            if i >= len(self.models):
                break
            path = self.models[i][0]
            if b_watch.clicked(ev):
                self.run_model(path, watch=True)
            if b_eval.clicked(ev):
                self.run_model(path, watch=False)

    # ---- boucle ----
    def run(self):
        running = True
        while running:
            mx, my = pygame.mouse.get_pos()
            buttons = pygame.mouse.get_pressed()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                if not self.handle(ev):
                    running = False
            if self.tab == 1:
                self.sl_sessions.update(mx, my, buttons)
                self.sl_board.update(mx, my, buttons)
            for b in self._active_buttons():
                b.update(mx, my)
            self._draw()
            clock.tick(FPS)
        pygame.quit()

    def _active_buttons(self):
        bts = [self.btn_stop, self.btn_quit]
        if self.tab == 1:
            bts += [self.btn_load_pick, self.btn_save_pick,
                    self.btn_launch]
        elif self.tab == 2:
            bts.append(self.btn_refresh)
            for bw, be in self.model_btns:
                bts += [bw, be]
        return bts

    # ---- dessin ----
    def _panel(self, x, y, w, h, title=None):
        draw_rect(screen, C_PANEL, (x, y, w, h), 10)
        pygame.draw.rect(screen, C_LINE, (x, y, w, h), 1, border_radius=10)
        if title:
            blit_text(screen, title, F_SEC, C_CYAN, x + 14, y + 12)
            hline(screen, y + 32, x + 14, x + w - 14)

    def _draw(self):
        screen.fill(C_BG)
        # header
        blit_text(screen, 'LEARN2SLITHER', F_TITLE, C_ACCENT, 28, 18)
        blit_text(screen, 'Centre de controle  *  Reinforcement Learning',
                  F_SUB, C_DIM, 30, 52)
        run_col = C_GREEN if self.runner.is_running() else C_DIM
        run_txt = 'EN COURS' if self.runner.is_running() else 'INACTIF'
        blit_text(screen, u'● ' + run_txt, F_SMALL, run_col,
                  W - 28, 30, anchor='midright')
        hline(screen, 78, 24, W - 24, C_ACCENT, 2)
        # tabs
        for i, (r, name) in enumerate(zip(self.tab_rects, TABS)):
            active = (i == self.tab)
            mx, my = pygame.mouse.get_pos()
            hov = r.collidepoint(mx, my)
            col = C_PANEL if active else C_BG2
            if hov and not active:
                col = C_WIDGET
            draw_rect(screen, col, r, 6)
            blit_text(screen, name, F_TAB,
                      C_CYAN if active else C_DIM,
                      r.centerx, r.centery, anchor='center')
            if active:
                pygame.draw.line(screen, C_CYAN, (r.x + 8, r.bottom - 3),
                                 (r.right - 8, r.bottom - 3), 3)
        # content
        if self.tab == 0:
            self._draw_scenarios()
        elif self.tab == 1:
            self._draw_custom()
        else:
            self._draw_models()
        self._draw_bottom()
        # overlays dropdown (par-dessus tout)
        if self.tab == 1:
            self.dd_visual.draw_open(screen)
            if self.dd_visual.value == 'on':
                self.dd_speed.draw_open(screen)
        pygame.display.flip()

    def _card(self, rect, accent, title, desc, hov):
        draw_rect(screen, C_CARD_HOV if hov else C_CARD, rect, 10)
        pygame.draw.rect(screen, accent if hov else C_LINE, rect, 1,
                         border_radius=10)
        draw_rect(screen, accent, (rect.x, rect.y, rect.w, 4), 2)
        blit_text(screen, title, F_H, C_FG, rect.x + 14, rect.y + 16)
        for j, line in enumerate(desc.split('\n')):
            blit_text(screen, line, F_SMALL, C_DIM, rect.x + 14,
                      rect.y + 44 + j * 16)
        if hov:
            blit_text(screen, 'Lancer', F_SMALL, accent,
                      rect.right - 14, rect.bottom - 12,
                      anchor='bottomright')
            tw = F_SMALL.size('Lancer')[0]
            lx = rect.right - 14 - tw - 11
            ly = rect.bottom - 17
            pygame.draw.polygon(screen, accent, [
                (lx, ly - 4), (lx, ly + 4), (lx + 7, ly)])

    def _draw_scenarios(self):
        mx, my = pygame.mouse.get_pos()
        blit_text(screen, '1 · ENTRAINEMENT  (depuis zero, -visual off,'
                  ' sauvegarde dans models/)', F_SEC, C_FG, 28, 142)
        for i, n in enumerate(TRAIN_PRESETS):
            r = self.train_rects[i]
            self._card(r, C_ACCENT, '{} sess'.format(n),
                       'entraine puis\nmodels/{}sess.txt'.format(n),
                       r.collidepoint(mx, my))
        blit_text(screen, '2 · DEMONSTRATION  (charge le meilleur '
                  'modele entraine)', F_SEC, C_FG, 28, 300)
        for i, (_, title, desc, accent) in enumerate(DEMOS):
            r = self.demo_rects[i]
            self._card(r, accent, title, desc, r.collidepoint(mx, my))
        best = find_best_model()
        exists = os.path.exists(best)
        msg = ('Meilleur modele : {}'.format(best) if exists
               else 'Aucun modele entraine (lance un entrainement ci-dessus)')
        blit_text(screen, msg, F_SMALL, C_GREEN if exists else C_AMBER,
                  28, 470)
        blit_text(screen, 'Astuce : la sortie de chaque commande '
                  's\'affiche dans le journal en bas.', F_SMALL, C_DIM,
                  28, 492)

    def _draw_custom(self):
        self._panel(24, 134, 410, 270, 'ENTRAINEMENT')
        blit_text(screen, '-sessions   nombre de parties', F_BODY, C_DIM,
                  44, 178)
        self.sl_sessions.draw(screen)
        blit_text(screen, '-visual', F_BODY, C_DIM, 44, 246)
        blit_text(screen, '-speed', F_BODY, C_DIM, 230, 246)
        self.dd_visual.draw(screen)
        if self.dd_visual.value == 'on':
            self.dd_speed.draw(screen)
        else:
            draw_rect(screen, C_BG2, self.dd_speed.rect, 5)
            blit_text(screen, '(visuel off)', F_SMALL, C_DIM, 240,
                      self.dd_speed.y + 14, anchor='midleft')
        blit_text(screen, '-board-size   grille NxN   [BONUS]', F_BODY,
                  C_DIM, 44, 322)
        self.sl_board.draw(screen)

        self._panel(454, 134, 422, 270, 'MODELE')
        blit_text(screen, '-load   charger un modele', F_BODY, C_DIM,
                  470, 176)
        self.ti_load.draw(screen)
        self.btn_load_pick.draw(screen)
        blit_text(screen, '-save   sauvegarder a la fin', F_BODY, C_DIM,
                  470, 248)
        self.ti_save.draw(screen)
        self.btn_save_pick.draw(screen)

        self._panel(24, 416, 852, 82, 'OPTIONS')
        self.cb_dontlearn.draw(screen)
        self.cb_step.draw(screen)

        blit_text(screen, 'COMMANDE', F_SMALL, C_DIM, 28, 510)
        parts = self.build_custom()[1:]
        cmd = 'python ' + ' '.join(parts)
        max_w = 656
        while F_MONO.size(cmd + '...')[0] > max_w and len(cmd) > 10:
            cmd = cmd[:-1]
        if F_MONO.size('python ' + ' '.join(parts))[0] > max_w:
            cmd += '...'
        draw_rect(screen, C_PANEL, (24, 530, 660, 32), 6)
        blit_text(screen, cmd, F_MONO, C_CYAN, 36, 546, anchor='midleft')
        self.btn_launch.draw(screen)
        tw = F_BTN_LG.size('LANCER')[0]
        tx = self.btn_launch.rect.centerx - tw // 2 - 16
        ty = self.btn_launch.rect.centery
        pygame.draw.polygon(screen, C_FG, [
            (tx, ty - 7), (tx, ty + 7), (tx + 11, ty)])
        # dropdowns par-dessus
        self.dd_visual.draw(screen)
        if self.dd_visual.value == 'on':
            self.dd_speed.draw(screen)

    def _draw_models(self):
        blit_text(screen, 'MODELES DISPONIBLES  (models/*.txt)', F_SEC,
                  C_FG, 28, 144)
        self.btn_refresh.draw(screen)
        if not self.models:
            blit_text(screen, 'Aucun modele. Entraine-en un dans '
                      'l\'onglet Scenarios.', F_BODY, C_AMBER, 28, 190)
            return
        mx, my = pygame.mouse.get_pos()
        for i, (path, info) in enumerate(self.models):
            if i >= 6:
                break
            y = 184 + i * 86
            row = pygame.Rect(24, y, 852, 74)
            hov = row.collidepoint(mx, my)
            draw_rect(screen, C_CARD_HOV if hov else C_CARD, row, 9)
            pygame.draw.rect(screen, C_LINE, row, 1, border_radius=9)
            blit_text(screen, os.path.basename(path), F_H, C_CYAN,
                      44, y + 18)
            if info:
                states, eps, kb = info
                txt = ('etats: {}     epsilon: {:.3f}     '
                       '{:.0f} Ko').format(states, eps, kb)
            else:
                txt = 'fichier illisible'
            blit_text(screen, txt, F_SMALL, C_DIM, 44, y + 46)
            bw, be = self.model_btns[i]
            bw.draw(screen)
            be.draw(screen)

    def _draw_bottom(self):
        hline(screen, 702, 24, W - 24, C_LINE)
        col = C_GREEN if self.runner.ok else C_ACCENT
        blit_text(screen, self.runner.status, F_BODY, col, 28, 716)
        draw_rect(screen, C_BG2, (24, 734, 696, 80), 8)
        pygame.draw.rect(screen, C_LINE, (24, 734, 696, 80), 1,
                         border_radius=8)
        lines = self.runner.snapshot()
        if not lines:
            blit_text(screen, '(journal vide)', F_MONO_SM, C_DIM, 36, 748)
        for j, line in enumerate(lines):
            disp = line
            while F_MONO_SM.size(disp)[0] > 672 and len(disp) > 4:
                disp = disp[:-1]
            blit_text(screen, disp, F_MONO_SM, C_FG, 36, 744 + j * 12)
        self.btn_stop.draw(screen)
        self.btn_quit.draw(screen)


if __name__ == '__main__':
    App().run()
