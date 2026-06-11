#!/usr/bin/python3
"""
display.py - Affichage graphique Pygame du plateau de jeu.
"""

import sys
import pygame

C_BG = (18, 18, 30)
C_GRID = (35, 35, 55)
C_EMPTY = (28, 28, 45)
C_HEAD = (100, 170, 255)
C_BODY = (55, 105, 195)
C_GREEN = (70, 215, 80)
C_RED = (220, 55, 55)
C_PANEL = (12, 12, 22)
C_TEXT = (220, 220, 220)
C_DIM = (110, 110, 150)
C_ACCENT2 = (83, 216, 251)
C_STEP = (255, 215, 0)

SPEED_FPS = {'slow': 4, 'normal': 10, 'fast': 30, 'max': 0}

CELL_PX = 52
PADDING = 18
INFO_H = 84


class GameDisplay:
    """Fenetre Pygame affichant le plateau et les statistiques."""

    def __init__(self, board_size=10, speed='normal'):
        pygame.init()
        self.board_size = board_size
        self.fps = SPEED_FPS.get(speed, 10)
        board_px = board_size * CELL_PX
        w = board_px + 2 * PADDING
        h = board_px + 2 * PADDING + INFO_H
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption('Snake Game - Learn2Slither')
        self.clock = pygame.time.Clock()
        self.f_sm = self._font(11)
        self.f_md = self._font(13, bold=True)
        self.f_lg = self._font(16, bold=True)
        self.f_ttl = self._font(11, bold=True)
        self.f_xl = self._font(24, bold=True)

    @staticmethod
    def _font(size, bold=False):
        for name in ('Courier New', 'Courier', 'DejaVu Sans Mono'):
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                pass
        return pygame.font.Font(None, size)

    def _txt(self, text, font, color, x, y, anchor='topleft'):
        surf = font.render(str(text), True, color)
        rect = surf.get_rect(**{anchor: (x, y)})
        self.screen.blit(surf, rect)

    def render(
        self,
        board,
        session=0,
        max_sessions=0,
        score=0,
        length=0,
        steps=0,
        action_name='',
        epsilon=0.0,
        step_mode=False,
    ):
        """Dessine la grille et la barre d'informations."""
        self._pump_events()
        self.screen.fill(C_BG)

        for row in range(self.board_size):
            for col in range(self.board_size):
                x = PADDING + col * CELL_PX
                y = PADDING + row * CELL_PX
                rect = pygame.Rect(x, y, CELL_PX - 1, CELL_PX - 1)
                cell = board[row][col]
                if cell == 'H':
                    color = C_HEAD
                elif cell == 'S':
                    color = C_BODY
                elif cell == 'G':
                    color = C_GREEN
                elif cell == 'R':
                    color = C_RED
                else:
                    color = C_EMPTY
                pygame.draw.rect(self.screen, color, rect,
                                 border_radius=5)

        grid_rect = pygame.Rect(
            PADDING - 1, PADDING - 1,
            self.board_size * CELL_PX + 1,
            self.board_size * CELL_PX + 1,
        )
        pygame.draw.rect(self.screen, C_GRID, grid_rect, 1,
                         border_radius=3)

        bar_y = PADDING + self.board_size * CELL_PX + 6
        pygame.draw.rect(
            self.screen, C_PANEL,
            pygame.Rect(0, bar_y, self.screen.get_width(), INFO_H)
        )
        pygame.draw.line(
            self.screen, C_GRID,
            (0, bar_y), (self.screen.get_width(), bar_y), 1
        )

        col_w = self.screen.get_width() // 4
        by = bar_y + 10

        top = [
            ('SESSION', '{}/{}'.format(session, max_sessions)),
            ('LENGTH', str(length)),
            ('STEPS', str(steps)),
            ('ACTION', action_name or '-'),
        ]
        bot = [
            ('SCORE', '{:.1f}'.format(score)),
            ('EPSILON', '{:.4f}'.format(epsilon)),
        ]
        for i, (label, value) in enumerate(top):
            bx = PADDING + i * col_w
            self._txt(label, self.f_ttl, C_DIM, bx, by)
            self._txt(value, self.f_lg, C_TEXT, bx, by + 16)

        for i, (label, value) in enumerate(bot):
            bx = PADDING + i * col_w
            self._txt(label, self.f_ttl, C_DIM, bx, by + 40)
            self._txt(value, self.f_md, C_ACCENT2, bx, by + 54)

        if step_mode:
            msg = '[ SPACE = suivant ]'
            sw = self.screen.get_width() - PADDING
            self._txt(msg, self.f_sm, C_STEP, sw,
                      bar_y + INFO_H - 16, anchor='bottomright')

        pygame.display.flip()
        if self.fps > 0:
            self.clock.tick(self.fps)

    def wait_for_step(self):
        """Bloque jusqu'a SPACE ou ENTREE (mode pas a pas)."""
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.close()
                    sys.exit(0)
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                        return

    def show_game_over(
        self, sessions, max_length, max_duration, avg_score
    ):
        """Ecran de fin : recapitulatif du run, attend une touche."""
        w = self.screen.get_width()
        h = self.screen.get_height()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 215))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(0, 0, min(380, w - 32), 236)
        card.center = (w // 2, h // 2)
        pygame.draw.rect(self.screen, C_PANEL, card, border_radius=10)
        pygame.draw.rect(self.screen, C_GRID, card, 1,
                         border_radius=10)

        self._txt('GAME OVER', self.f_xl, C_RED,
                  card.centerx, card.top + 34, anchor='center')

        rows = [
            ('SESSIONS', str(sessions), C_TEXT),
            ('LONGUEUR MAX', str(max_length), C_TEXT),
            ('DUREE MAX', '{} pas'.format(max_duration), C_TEXT),
            ('SCORE MOYEN', '{:.1f}'.format(avg_score), C_ACCENT2),
        ]
        y = card.top + 78
        for label, value, color in rows:
            self._txt(label, self.f_ttl, C_DIM,
                      card.left + 24, y, anchor='midleft')
            self._txt(value, self.f_lg, color,
                      card.right - 24, y, anchor='midright')
            y += 32

        self._txt('[ une touche pour fermer ]', self.f_sm, C_STEP,
                  card.centerx, card.bottom - 20, anchor='center')

        pygame.display.flip()
        self._wait_any_key()

    @staticmethod
    def _wait_any_key():
        """Bloque jusqu'a une touche, un clic ou la fermeture."""
        while True:
            ev = pygame.event.wait()
            if ev.type in (
                pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN
            ):
                return

    def _pump_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.close()
                sys.exit(0)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.close()
                    sys.exit(0)

    def close(self):
        pygame.quit()
