#!/usr/bin/python3
"""
agent.py - Agent Q-learning avec Q-table dictionnaire.
"""

import ast
import json
import os
import random
from collections import defaultdict

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
ACTIONS = [UP, RIGHT, DOWN, LEFT]
ACTION_NAMES = {UP: 'UP', RIGHT: 'RIGHT', DOWN: 'DOWN', LEFT: 'LEFT'}


class QAgent:
    """
    Agent Q-learning avec Q-table sparse (dictionnaire).

    Parametres:
      alpha        taux d'apprentissage
      gamma        facteur de decompte
      epsilon      exploration initiale (decroit vers epsilon_min)
      learn        False = mode dontlearn (pas de mise a jour)
    """

    def __init__(
        self,
        alpha=0.1,
        gamma=0.9,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.995,
        learn=True,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.learn = learn
        self.q = defaultdict(lambda: defaultdict(float))

    def choose_action(self, state):
        """
        Selection epsilon-greedy.
        En mode dontlearn, on exploite toujours.
        """
        if self.learn and random.random() < self.epsilon:
            return random.choice(ACTIONS)
        q_vals = [self.q[state][a] for a in ACTIONS]
        max_q = max(q_vals)
        best = [a for a, v in zip(ACTIONS, q_vals) if v == max_q]
        return random.choice(best)

    def update(self, state, action, reward, next_state, done):
        """
        Mise a jour Bellman.
        Aucune mise a jour en mode dontlearn.
        """
        if not self.learn:
            return
        if done:
            target = reward
        else:
            next_max = max(self.q[next_state][a] for a in ACTIONS)
            target = reward + self.gamma * next_max
        self.q[state][action] += self.alpha * (
            target - self.q[state][action]
        )

    def decay_epsilon(self):
        """Reduit epsilon a la fin de chaque session."""
        if self.learn:
            self.epsilon = max(
                self.epsilon_min, self.epsilon * self.epsilon_decay
            )

    def save(self, path):
        """Exporte la Q-table et les hyperparametres en JSON."""
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        data = {
            'alpha': self.alpha,
            'gamma': self.gamma,
            'epsilon': self.epsilon,
            'epsilon_min': self.epsilon_min,
            'epsilon_decay': self.epsilon_decay,
            'q_table': {
                str(state): {str(a): v for a, v in actions.items()}
                for state, actions in self.q.items()
            },
        }
        with open(path, 'w') as f:
            json.dump(data, f, separators=(',', ':'))
        print(
            'Save learning state in {}  ({} etats, e={:.4f})'.format(
                path, len(self.q), self.epsilon
            )
        )

    def load(self, path):
        """Importe une Q-table depuis un fichier JSON."""
        with open(path, 'r') as f:
            data = json.load(f)
        self.alpha = data.get('alpha', self.alpha)
        self.gamma = data.get('gamma', self.gamma)
        self.epsilon = data.get('epsilon', self.epsilon)
        self.epsilon_min = data.get('epsilon_min', self.epsilon_min)
        self.epsilon_decay = data.get(
            'epsilon_decay', self.epsilon_decay
        )
        self.q = defaultdict(lambda: defaultdict(float))
        for state_str, actions in data.get('q_table', {}).items():
            state = ast.literal_eval(state_str)
            for a_str, v in actions.items():
                self.q[state][int(a_str)] = float(v)
        print(
            'Load trained model from {}  ({} etats, e={:.4f})'.format(
                path, len(self.q), self.epsilon
            )
        )

    @property
    def q_table_size(self):
        return len(self.q)
