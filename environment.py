#!/usr/bin/python3
"""
environment.py - Plateau de jeu, serpent, pommes, vision, regles.
"""

import random
from collections import deque

EMPTY = '0'
WALL = 'W'
HEAD = 'H'
BODY = 'S'
GREEN = 'G'
RED = 'R'

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
DELTA = {
    UP: (-1, 0),
    RIGHT: (0, 1),
    DOWN: (1, 0),
    LEFT: (0, -1),
}
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
ACTION_NAMES = {UP: 'UP', RIGHT: 'RIGHT', DOWN: 'DOWN', LEFT: 'LEFT'}
ACTIONS = [UP, RIGHT, DOWN, LEFT]


class Environment:
    """
    Plateau NxN avec serpent, pommes vertes (+1) et rouge (-1).

    Regles du sujet:
      2 pommes vertes, 1 rouge, serpent de longueur 3 (aleatoire).
      Mur / collision soi-meme / longueur 0 -> Game over.
    """

    def __init__(self, size=10):
        self.size = size
        self.max_steps = size * size * 10
        self.snake = deque()
        self.green_apples = []
        self.red_apples = []
        self.direction = RIGHT
        self.done = False
        self.steps = 0
        self.reset()

    def reset(self):
        """Demarre une nouvelle session, retourne l'etat initial."""
        self.done = False
        self.steps = 0
        self._place_snake()
        self._place_apples()
        return self.get_state()

    def _place_snake(self):
        """Serpent de 3 segments, place aleatoirement loin des bords."""
        margin = 2
        while True:
            move_dir = random.choice(ACTIONS)
            opp_dr, opp_dc = DELTA[OPPOSITE[move_dir]]
            r = random.randint(margin, self.size - margin - 1)
            c = random.randint(margin, self.size - margin - 1)
            segs = [
                (r + opp_dr * i, c + opp_dc * i) for i in range(3)
            ]
            valid = all(
                0 <= sr < self.size and 0 <= sc < self.size
                for sr, sc in segs
            )
            if valid:
                self.snake = deque(segs)
                self.direction = move_dir
                break

    def _free_cell(self):
        """Retourne une cellule libre au hasard."""
        occupied = (
            set(self.snake)
            | set(self.green_apples)
            | set(self.red_apples)
        )
        free = [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if (r, c) not in occupied
        ]
        return random.choice(free) if free else None

    def _place_apples(self):
        """Place 2 pommes vertes et 1 rouge."""
        self.green_apples = []
        self.red_apples = []
        for _ in range(2):
            cell = self._free_cell()
            if cell:
                self.green_apples.append(cell)
        cell = self._free_cell()
        if cell:
            self.red_apples.append(cell)

    def step(self, action):
        """
        Deplace le serpent dans la direction action.
        Retourne (next_state, reward, done).

        Recompenses: +10 pomme verte, -10 pomme rouge,
                     -0.1 deplacement normal, -100 game over.
        """
        if action == OPPOSITE[self.direction]:
            action = self.direction
        dr, dc = DELTA[action]
        hr, hc = self.snake[0]
        nr, nc = hr + dr, hc + dc

        if not (0 <= nr < self.size and 0 <= nc < self.size):
            self.done = True
            return self.get_state(), -100.0, True

        body_no_tail = set(list(self.snake)[:-1])
        if (nr, nc) in body_no_tail:
            self.done = True
            return self.get_state(), -100.0, True

        self.snake.appendleft((nr, nc))

        if (nr, nc) in self.green_apples:
            self.green_apples.remove((nr, nc))
            cell = self._free_cell()
            if cell:
                self.green_apples.append(cell)
            reward = 10.0

        elif (nr, nc) in self.red_apples:
            self.red_apples.remove((nr, nc))
            cell = self._free_cell()
            if cell:
                self.red_apples.append(cell)
            self.snake.pop()
            self.snake.pop()
            if len(self.snake) == 0:
                self.done = True
                return tuple([1, 0, 0] * 4), -100.0, True
            reward = -10.0

        else:
            self.snake.pop()
            reward = -0.1

        self.direction = action
        self.steps += 1
        if self.steps >= self.max_steps:
            return self.get_state(), 0.0, True
        return self.get_state(), reward, False

    def get_state(self):
        """
        Etat compact derive des rayons visuels.

        Pour chaque direction (N, E, S, W):
          danger : distance au premier obstacle (mur ou corps),
                   plafonnee a 3  (1=immediat, 2=proche, 3=loin)
          has_g  : 1 si pomme verte dans le rayon
          has_r  : 1 si pomme rouge dans le rayon

        12 elements normalises par rapport a la taille du plateau,
        ce qui rend l'etat independant de la taille du plateau.
        """
        hr, hc = self.snake[0]
        snake_set = frozenset(self.snake)
        green_set = frozenset(self.green_apples)
        red_set = frozenset(self.red_apples)
        enc = []

        for dr, dc in [DELTA[UP], DELTA[RIGHT], DELTA[DOWN], DELTA[LEFT]]:
            has_g = 0
            has_r = 0
            body_dist = 0
            r, c = hr + dr, hc + dc
            dist = 1
            while 0 <= r < self.size and 0 <= c < self.size:
                if body_dist == 0 and (r, c) in snake_set:
                    body_dist = dist
                if (r, c) in green_set:
                    has_g = 1
                if (r, c) in red_set:
                    has_r = 1
                r += dr
                c += dc
                dist += 1
            wall_dist = dist
            danger = body_dist if body_dist > 0 else wall_dist
            enc.extend([min(danger, 3), has_g, has_r])

        return tuple(enc)

    def get_vision_rays(self):
        """Rayons visuels complets pour l'affichage terminal."""
        hr, hc = self.snake[0]
        snake_set = set(self.snake)
        green_set = set(self.green_apples)
        red_set = set(self.red_apples)
        rays = {}

        for name, action in [
            ('up', UP), ('right', RIGHT), ('down', DOWN), ('left', LEFT)
        ]:
            dr, dc = DELTA[action]
            ray = []
            r, c = hr + dr, hc + dc
            while 0 <= r < self.size and 0 <= c < self.size:
                if (r, c) in snake_set:
                    ray.append(BODY)
                elif (r, c) in green_set:
                    ray.append(GREEN)
                elif (r, c) in red_set:
                    ray.append(RED)
                else:
                    ray.append(EMPTY)
                r += dr
                c += dc
            ray.append(WALL)
            rays[name] = ray

        return rays

    def print_vision(self, action_name=''):
        """
        Affiche la vision 4-directions dans le terminal.
        Format identique a la figure du sujet.
        """
        rays = self.get_vision_rays()
        up_ray = rays['up']
        down_ray = rays['down']
        left_ray = rays['left']
        right_ray = rays['right']

        indent = len(left_ray)
        left_str = ''.join(reversed(left_ray))
        right_str = ''.join(right_ray)

        for cell in reversed(up_ray):
            print(' ' * indent + cell)

        print(left_str + HEAD + right_str)

        for cell in down_ray:
            print(' ' * indent + cell)

        if action_name:
            print('\n' + action_name + '\n')

    def get_board(self):
        """Grille 2D pour l'affichage graphique."""
        board = [[EMPTY] * self.size for _ in range(self.size)]
        for i, (r, c) in enumerate(self.snake):
            board[r][c] = HEAD if i == 0 else BODY
        for r, c in self.green_apples:
            board[r][c] = GREEN
        for r, c in self.red_apples:
            board[r][c] = RED
        return board

    @property
    def length(self):
        return len(self.snake)
