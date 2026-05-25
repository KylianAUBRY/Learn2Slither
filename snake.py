#!/usr/bin/python3
"""
Learn2Slither - Launcher GUI (Pygame).
Lancer : /usr/bin/python3 snake.py
Necessite : pygame  ->  pip install pygame
"""

import os
import subprocess
import sys

import pygame

C_BG = (14, 15, 35)
C_PANEL = (20, 25, 55)
C_WIDGET = (30, 40, 90)
C_WIDGET_HOV = (45, 60, 120)
C_ACCENT = (233, 69, 96)
C_ACCENT_HOV = (255, 100, 120)
C_ACCENT2 = (83, 216, 251)
C_FG = (234, 234, 234)
C_DIM = (120, 120, 160)
C_QUIT = (40, 40, 75)
C_QUIT_HOV = (70, 70, 110)

W, H = 720, 762
FPS = 60

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption('Learn2Slither - Launcher')
clock = pygame.time.Clock()


def _font(size, bold=False):
    for name in ('Courier New', 'Courier', 'DejaVu Sans Mono'):
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)


F_TITLE = _font(26, bold=True)
F_SUB = _font(11, bold=True)
F_BODY = _font(10)
F_SMALL = _font(9)
F_BTN = _font(12, bold=True)
F_BTN_LG = _font(14, bold=True)
F_MONO = _font(11)


def draw_rect(surf, color, rect, radius=6):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def blit_text(surf, txt, font, color, x, y, anchor='topleft'):
    s = font.render(str(txt), True, color)
    r = s.get_rect(**{anchor: (x, y)})
    surf.blit(s, r)
    return r


def hline(surf, y, color=None, thickness=1):
    col = color if color else C_WIDGET
    pygame.draw.line(surf, col, (30, y), (W - 30, y), thickness)


class Button:
    def __init__(self, rect, label, color=C_WIDGET,
                 hover=C_WIDGET_HOV, font=F_BTN, fg=C_FG,
                 radius=7):
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
                  self.rect.centerx, self.rect.centery,
                  anchor='center')

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


class Slider:
    def __init__(self, x, y, w, lo, hi, value):
        self.x = x
        self.y = y
        self.w = w
        self.lo = lo
        self.hi = hi
        self.value = value
        self._drag = False
        self.h = 6
        self.track = pygame.Rect(x, y, w, self.h)

    def _val_to_x(self):
        frac = (self.value - self.lo) / (self.hi - self.lo)
        return int(self.x + frac * self.w)

    def update(self, events, mx, my, buttons):
        if buttons[0]:
            tx = self._val_to_x()
            thumb = pygame.Rect(tx - 8, self.y - 7, 16, 20)
            if self._drag or thumb.collidepoint(mx, my):
                self._drag = True
                frac = max(0, min(1, (mx - self.x) / self.w))
                self.value = int(
                    self.lo + frac * (self.hi - self.lo)
                )
        else:
            self._drag = False

    def draw(self, surf):
        pygame.draw.rect(surf, C_WIDGET, self.track,
                         border_radius=3)
        fill_w = self._val_to_x() - self.x
        if fill_w > 0:
            pygame.draw.rect(surf, C_ACCENT2,
                             (self.x, self.y, fill_w, self.h),
                             border_radius=3)
        tx = self._val_to_x()
        draw_rect(surf, C_ACCENT, (tx - 7, self.y - 6, 14, 18),
                  radius=4)
        blit_text(surf, str(self.value), F_SMALL, C_FG,
                  tx, self.y - 14, anchor='center')


class Dropdown:
    def __init__(self, x, y, w, choices, value=None):
        self.x = x
        self.y = y
        self.w = w
        self.choices = choices
        self.idx = choices.index(value) if value in choices else 0
        self.open = False
        self.h = 26
        self.rect = pygame.Rect(x, y, w, self.h)

    @property
    def value(self):
        return self.choices[self.idx]

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
            elif self.open:
                for i, _ in enumerate(self.choices):
                    ry = self.y + self.h * (i + 1)
                    item = pygame.Rect(self.x, ry, self.w, self.h)
                    if item.collidepoint(event.pos):
                        self.idx = i
                        self.open = False
                        return
                self.open = False

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hov = self.rect.collidepoint(mx, my)
        col = C_WIDGET_HOV if hov else C_WIDGET
        draw_rect(surf, col, self.rect, radius=5)
        blit_text(surf, self.value, F_BODY, C_FG,
                  self.x + 8, self.y + 13, anchor='midleft')
        arrow = u'▲' if self.open else u'▼'
        blit_text(surf, arrow, F_SMALL, C_ACCENT2,
                  self.x + self.w - 14, self.y + 13,
                  anchor='midright')
        if self.open:
            for i, ch in enumerate(self.choices):
                ry = self.y + self.h * (i + 1)
                item = pygame.Rect(self.x, ry, self.w, self.h)
                hov_i = item.collidepoint(mx, my)
                if hov_i or i == self.idx:
                    item_col = C_WIDGET_HOV
                else:
                    item_col = (25, 35, 70)
                draw_rect(surf, item_col, item, radius=0)
                txt_col = C_ACCENT2 if i == self.idx else C_FG
                blit_text(surf, ch, F_BODY, txt_col,
                          self.x + 8, ry + 13, anchor='midleft')


class Checkbox:
    def __init__(self, x, y, label, checked=False):
        self.x = x
        self.y = y
        self.label = label
        self.checked = checked
        self.box = pygame.Rect(x, y, 16, 16)

    def handle(self, event):
        if (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.box.collidepoint(event.pos)):
            self.checked = not self.checked

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hov = self.box.collidepoint(mx, my)
        col = C_WIDGET_HOV if hov else C_WIDGET
        draw_rect(surf, col, self.box, radius=3)
        if self.checked:
            blit_text(surf, u'✓', F_BODY, (80, 220, 120),
                      self.box.centerx, self.box.centery,
                      anchor='center')
        blit_text(surf, self.label, F_BODY, C_FG,
                  self.x + 22, self.y + 8, anchor='midleft')


class TextInput:
    def __init__(self, x, y, w, placeholder=''):
        self.rect = pygame.Rect(x, y, w, 24)
        self.ph = placeholder
        self.value = ''
        self.active = False

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            elif event.unicode and event.unicode.isprintable():
                self.value += event.unicode

    def draw(self, surf):
        col = C_ACCENT2 if self.active else C_WIDGET
        draw_rect(surf, C_WIDGET, self.rect, radius=4)
        pygame.draw.rect(surf, col, self.rect, 1,
                         border_radius=4)
        display = self.value if self.value else self.ph
        txt_col = C_FG if self.value else C_DIM
        max_w = self.rect.w - 10
        s = F_SMALL.render(display, True, txt_col)
        if s.get_width() > max_w:
            trimmed = display
            while F_SMALL.size(trimmed)[0] > max_w and trimmed:
                trimmed = trimmed[1:]
            s = F_SMALL.render(trimmed, True, txt_col)
        surf.blit(s, (self.rect.x + 6, self.rect.y + 6))
        if self.active:
            cx = self.rect.x + 6 + F_SMALL.size(self.value)[0]
            if pygame.time.get_ticks() % 1000 < 500:
                pygame.draw.line(surf, C_FG,
                                 (cx, self.rect.y + 4),
                                 (cx, self.rect.y + 18), 1)


class App:

    def __init__(self):
        self.sl_sessions = Slider(44, 210, 240, 1, 10000, 100)
        self.dd_visual = Dropdown(
            44, 252, 130, ['on', 'off'], 'on'
        )
        self.dd_speed = Dropdown(
            44, 307, 130,
            ['slow', 'normal', 'fast', 'max'], 'normal'
        )
        self.sl_board = Slider(44, 363, 210, 5, 50, 10)

        self.ti_load = TextInput(
            380, 155, 228, 'models/modele.txt'
        )
        self.btn_load_pick = Button(
            (614, 153, 72, 26), 'Ouvrir...', font=F_SMALL
        )

        self.ti_save = TextInput(
            380, 218, 228, 'models/nouveau.txt'
        )
        self.btn_save_pick = Button(
            (614, 216, 72, 26), 'Enreg...', font=F_SMALL
        )

        self.cb_show_viz = Checkbox(
            44, 530,
            'Afficher la visualisation pendant l\'entrainement',
            checked=False
        )
        self.cb_dontlearn = Checkbox(
            44, 558, '-dontlearn  (pas d\'apprentissage)'
        )
        self.cb_step = Checkbox(
            390, 558, '-step-by-step'
        )

        self.btn_launch = Button(
            (W // 2 - 160, 688, 145, 46),
            u'▶  LANCER', C_ACCENT, C_ACCENT_HOV, F_BTN_LG
        )
        self.btn_quit = Button(
            (W // 2 + 20, 688, 145, 46),
            u'✕  QUITTER', C_QUIT, C_QUIT_HOV, F_BTN_LG
        )

        self._msg = ''
        self._msg_ok = True

    def _pick_file(self, target, save=False):
        try:
            import tkinter as _tk
            from tkinter import filedialog as _fd
            root = _tk.Tk()
            root.withdraw()
            if save:
                p = _fd.asksaveasfilename(
                    title='Sauvegarder le modele',
                    initialdir='models',
                    defaultextension='.txt',
                    filetypes=[
                        ('Texte', '*.txt'), ('Tous', '*.*')
                    ]
                )
            else:
                p = _fd.askopenfilename(
                    title='Charger un modele',
                    initialdir='models',
                    filetypes=[
                        ('Modeles', '*.txt *.json'),
                        ('Tous', '*.*')
                    ]
                )
            root.destroy()
            if p:
                target.value = p
        except Exception:
            target.active = True

    def _build_cmd(self):
        exe = sys.executable
        if os.path.exists('main.py'):
            parts = [exe, 'main.py']
        elif os.path.exists('./snake') and os.access('./snake', os.X_OK):
            parts = ['./snake']
        else:
            parts = [exe, 'main.py']
        parts += ['-sessions', str(self.sl_sessions.value)]
        if self.cb_show_viz.checked:
            parts += ['-visual', self.dd_visual.value]
            parts += ['-speed', self.dd_speed.value]
        else:
            parts += ['-visual', 'off']
        parts += ['-board-size', str(self.sl_board.value)]
        load = self.ti_load.value.strip()
        if load:
            parts += ['-load', load]
        save = self.ti_save.value.strip()
        if save:
            parts += ['-save', save]
        if self.cb_dontlearn.checked:
            parts.append('-dontlearn')
        if self.cb_step.checked:
            parts.append('-step-by-step')
        return parts

    def _launch(self):
        cmd = self._build_cmd()
        target = cmd[1] if cmd[0] == sys.executable else cmd[0]
        if not os.path.exists(target):
            self._msg = "'{}' introuvable !".format(
                os.path.basename(target)
            )
            self._msg_ok = False
            return
        try:
            subprocess.Popen(cmd)
            self._msg = 'Lance: ' + ' '.join(cmd[:4]) + ' ...'
            self._msg_ok = True
        except Exception as exc:
            self._msg = str(exc)
            self._msg_ok = False

    def run(self):
        running = True
        while running:
            mx, my = pygame.mouse.get_pos()
            buttons = pygame.mouse.get_pressed()
            events = pygame.event.get()

            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False
                was = self.cb_show_viz.checked
                self.cb_show_viz.handle(ev)
                if was and not self.cb_show_viz.checked:
                    self.dd_visual.open = False
                    self.dd_speed.open = False
                if self.cb_show_viz.checked:
                    self.dd_visual.handle(ev)
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
                    self._launch()
                if self.btn_quit.clicked(ev):
                    running = False

            self.sl_sessions.update(events, mx, my, buttons)
            self.sl_board.update(events, mx, my, buttons)
            for b in (self.btn_launch, self.btn_quit,
                      self.btn_load_pick, self.btn_save_pick):
                b.update(mx, my)

            self._draw()
            clock.tick(FPS)

        pygame.quit()

    def _section(self, x, y, w, h, title):
        draw_rect(screen, C_PANEL, (x, y, w, h), radius=8)
        pygame.draw.rect(screen, C_WIDGET,
                         (x, y, w, h), 1, border_radius=8)
        blit_text(screen, title, F_SUB, C_ACCENT2, x + 14, y + 10)
        hline(screen, y + 26, C_WIDGET)

    def _lbl(self, text, x, y):
        blit_text(screen, text, F_BODY, C_DIM, x, y)

    def _draw(self):
        screen.fill(C_BG)

        blit_text(screen, 'LEARN2SLITHER', F_TITLE, C_ACCENT,
                  W // 2, 32, anchor='center')
        blit_text(
            screen,
            'Reinforcement Learning  *  Snake Launcher',
            F_SMALL, C_DIM, W // 2, 68, anchor='center'
        )
        hline(screen, 88, C_ACCENT, 2)

        self._section(28, 100, 330, 275, 'TRAINING')

        self._lbl('-sessions   nombre de parties', 44, 138)
        self.sl_sessions.draw(screen)

        viz_on = self.cb_show_viz.checked
        lbl_col = C_DIM if viz_on else (55, 55, 80)
        blit_text(screen, '-visual   affichage graphique',
                  F_BODY, lbl_col, 44, 238)
        self.dd_visual.draw(screen)

        blit_text(screen, '-speed   vitesse  (defaut: normal)',
                  F_BODY, lbl_col, 44, 293)
        self.dd_speed.draw(screen)

        if not viz_on:
            ovl = pygame.Surface((312, 110), pygame.SRCALPHA)
            ovl.fill((14, 15, 35, 210))
            screen.blit(ovl, (30, 232))

        self._lbl('-board-size   grille  (defaut:10) [BONUS]',
                  44, 348)
        self.sl_board.draw(screen)

        self._section(365, 100, 330, 275, 'MODEL')

        self._lbl('-load   charger un modele', 380, 138)
        self.ti_load.draw(screen)
        self.btn_load_pick.draw(screen)

        self._lbl('-save   sauvegarder apres', 380, 205)
        self.ti_save.draw(screen)
        self.btn_save_pick.draw(screen)

        self._section(28, 497, 665, 88, 'OPTIONS')
        self.cb_show_viz.draw(screen)
        self.cb_dontlearn.draw(screen)
        self.cb_step.draw(screen)

        hline(screen, 603, C_WIDGET)
        blit_text(screen, 'COMMAND PREVIEW', F_SMALL, C_DIM,
                  35, 611)
        cmd_str = ' '.join(self._build_cmd())
        max_w = W - 70
        rendered = F_MONO.render(cmd_str, True, C_ACCENT2)
        if rendered.get_width() > max_w:
            while F_MONO.size(cmd_str + '...')[0] > max_w:
                cmd_str = cmd_str[:-1]
            cmd_str += '...'
        draw_rect(screen, C_PANEL, (30, 623, W - 60, 28),
                  radius=5)
        blit_text(screen, cmd_str, F_MONO, C_ACCENT2,
                  40, 637, anchor='midleft')

        self.btn_launch.draw(screen)
        self.btn_quit.draw(screen)

        if self._msg:
            col = (60, 200, 100) if self._msg_ok else C_ACCENT
            blit_text(screen, self._msg, F_SMALL, col,
                      W // 2, 744, anchor='center')

        if viz_on and self.dd_visual.open:
            self.dd_visual.draw(screen)
        if viz_on and self.dd_speed.open:
            self.dd_speed.draw(screen)

        pygame.display.flip()


if __name__ == '__main__':
    App().run()
