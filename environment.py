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

REWARD_GREEN = 20.0
REWARD_RED = -10.0
REWARD_STEP = -1.0
REWARD_DEATH = -100.0
REWARD_TIMEOUT = -50.0

CLOSE_RATIO = 0.3
MEDIUM_RATIO = 0.6

# Le placement du serpent (marge de 2) tire randint(2, size - 3),
# qui doit etre non vide : size >= 5.
MIN_BOARD_SIZE = 5


def _relative_bucket(distance, size):
    """Distance -> seau 0..3 proportionnel a la taille du plateau."""
    if distance <= 1:
        return 0
    if distance <= CLOSE_RATIO * size:
        return 1
    if distance <= MEDIUM_RATIO * size:
        return 2
    return 3


def _item_bits(distance, size):
    """Pomme visible -> 2 bits de seau (00 = pas visible)."""
    if distance is None:
        return (0, 0)
    bucket = max(1, _relative_bucket(distance, size))
    return ((bucket >> 1) & 1, bucket & 1)


class Environment:
    """
    Plateau NxN avec serpent, pommes vertes (+1) et rouge (-1).

    Regles du sujet:
      2 pommes vertes, 1 rouge, serpent de longueur 3 (aleatoire).
      Mur / collision soi-meme / longueur 0 -> Game over.
    """

    def __init__(self, size=10):
        if size < MIN_BOARD_SIZE:
            raise ValueError(
                'taille de plateau minimum: {}'.format(MIN_BOARD_SIZE)
            )
        self.size = size
        self.snake = deque()
        self.green_apples = []
        self.red_apples = []
        self.direction = RIGHT
        self.done = False
        self.steps = 0
        self.steps_since_green = 0
        self.cause = None
        self.reset()

    def reset(self):
        """Demarre une nouvelle session, retourne l'etat initial."""
        self.done = False
        self.steps = 0
        self.steps_since_green = 0
        self.cause = None
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

        Recompenses: +20 pomme verte, -10 pomme rouge,
                     -1 deplacement normal, -100 game over,
                     -50 timeout (boucle sans manger).
        """
        if action == OPPOSITE[self.direction]:
            action = self.direction
        dr, dc = DELTA[action]
        hr, hc = self.snake[0]
        nr, nc = hr + dr, hc + dc

        if not (0 <= nr < self.size and 0 <= nc < self.size):
            self.done = True
            self.cause = 'wall'
            return self.get_state(), REWARD_DEATH, True

        body_no_tail = set(list(self.snake)[:-1])
        if (nr, nc) in body_no_tail:
            self.done = True
            self.cause = 'self'
            return self.get_state(), REWARD_DEATH, True

        self.snake.appendleft((nr, nc))

        if (nr, nc) in self.green_apples:
            self.green_apples.remove((nr, nc))
            cell = self._free_cell()
            if cell:
                self.green_apples.append(cell)
            reward = REWARD_GREEN
            self.steps_since_green = 0

        elif (nr, nc) in self.red_apples:
            self.red_apples.remove((nr, nc))
            cell = self._free_cell()
            if cell:
                self.red_apples.append(cell)
            self.snake.pop()
            self.snake.pop()
            if len(self.snake) == 0:
                self.done = True
                self.cause = 'length_zero'
                return self.get_state(), REWARD_DEATH, True
            reward = REWARD_RED
            self.steps_since_green += 1

        else:
            self.snake.pop()
            reward = REWARD_STEP
            self.steps_since_green += 1

        self.direction = action
        self.steps += 1

        limit = max(100, 100 * len(self.snake))
        if self.steps_since_green > limit:
            self.done = True
            self.cause = 'timeout'
            return self.get_state(), REWARD_TIMEOUT, True

        return self.get_state(), reward, False

    def get_state(self):
        """
        Etat compact derive de la vision en croix (16 bits).

        Pour chaque direction (haut, droite, bas, gauche), 4 bits :
          bits 0-1 : distance au premier obstacle (mur ou corps),
                     en seau proportionnel a la taille du plateau ;
          bits 2-3 : distance a la pomme verte la plus proche visible
                     (00 = aucune), en seau proportionnel.

        Distances relatives -> etat independant de la taille du
        plateau. Les pommes rouges sont volontairement absentes :
        une variante 24 bits les encodant a ete entrainee et mesuree
        moins bonne (espace d'etats x7, apprentissage fragmente pour
        un benefice marginal).
        """
        if not self.snake:
            return tuple([0] * 16)

        hr, hc = self.snake[0]
        body = set(list(self.snake)[1:])
        green = set(self.green_apples)
        size = self.size
        features = []

        for dr, dc in [DELTA[UP], DELTA[RIGHT], DELTA[DOWN],
                       DELTA[LEFT]]:
            obstacle_dist = None
            green_dist = None
            for dist in range(1, size + 1):
                r, c = hr + dr * dist, hc + dc * dist
                if not (0 <= r < size and 0 <= c < size):
                    if obstacle_dist is None:
                        obstacle_dist = dist
                    break
                if (r, c) in body and obstacle_dist is None:
                    obstacle_dist = dist
                if (r, c) in green and green_dist is None:
                    green_dist = dist
            if obstacle_dist is None:
                obstacle_dist = size

            ob_b = _relative_bucket(obstacle_dist, size)
            features.append((ob_b >> 1) & 1)
            features.append(ob_b & 1)
            features.extend(_item_bits(green_dist, size))

        return tuple(features)

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
