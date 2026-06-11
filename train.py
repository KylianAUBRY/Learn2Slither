#!/usr/bin/python3
"""
train.py - Entrainement headless avec snapshots et multi-tailles.

Entraine UN seul agent en continu et sauvegarde des instantanes de la
Q-table a des paliers de sessions (1, 10, 100, ...). Comme l'encodage
d'etat utilise des distances *relatives* a la taille du plateau, on
peut tirer une taille au hasard a chaque session (-sizes) : le modele
apprend alors une politique qui generalise a toutes les tailles, et
le meme fichier .txt joue correctement en 8x8 comme en 30x30.

Exemples :
  python3 train.py -sessions 100000 -sizes 8 10 12 15 20
  python3 train.py -sessions 100000 -size 10
"""

import argparse
import os
import random
import time

from environment import Environment, OPPOSITE, MIN_BOARD_SIZE
from agent import QAgent


def board_size_type(value):
    """Valide -size / -sizes : entier >= MIN_BOARD_SIZE."""
    size = int(value)
    if size < MIN_BOARD_SIZE:
        raise argparse.ArgumentTypeError(
            'taille minimum: {}'.format(MIN_BOARD_SIZE)
        )
    return size


def sessions_type(value):
    """Valide -sessions : entier >= 1."""
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError('minimum 1 session')
    return n


def play_one(env, agent):
    """Joue une session complete et apprend ; retourne (max_len, cause)."""
    state = env.reset()
    last_action = env.direction
    done = False
    max_len = env.length
    while not done:
        action = agent.choose_action(state)
        if action == OPPOSITE[last_action]:
            action = last_action
        last_action = action
        next_state, reward, done = env.step(action)
        agent.update(state, action, reward, next_state, done)
        state = next_state
        if env.length > max_len:
            max_len = env.length
    return max_len, env.cause


def parse_args():
    parser = argparse.ArgumentParser(
        description='Entrainement Learn2Slither (snapshots, multi-tailles).',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-sessions', type=sessions_type, default=100000)
    parser.add_argument('-snapshots', type=int, nargs='+',
                        default=[1, 10, 100, 1000, 10000, 100000])
    parser.add_argument('-out', type=str, default='models')
    parser.add_argument('-size', type=board_size_type, default=10)
    parser.add_argument('-sizes', type=board_size_type, nargs='+',
                        default=None,
                        help='Tire une taille au hasard a chaque session.')
    parser.add_argument('-load', type=str, default=None,
                        help='Reprend l\'entrainement depuis un modele.')
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    total = args.sessions
    snapshots = sorted(s for s in set(args.snapshots) if s <= total)
    sizes_pool = args.sizes if args.sizes else [args.size]
    print('Tailles d\'entrainement : {}'.format(sizes_pool))

    agent = QAgent()
    if args.load:
        agent.load(args.load)
        print('Reprise depuis {}'.format(args.load))

    envs = {s: Environment(size=s) for s in sizes_pool}
    start = time.time()
    window = []
    report_every = max(1000, total // 200)

    for s in range(1, total + 1):
        env = envs[random.choice(sizes_pool)]
        length, _ = play_one(env, agent)
        agent.decay_epsilon()
        window.append(length)
        if len(window) > 100:
            window.pop(0)

        if s in snapshots:
            path = os.path.join(args.out, '{}sess.txt'.format(s))
            agent.save(path)
        if s in snapshots or s % report_every == 0:
            avg = sum(window) / len(window)
            print('[{:>7}/{}]  avg_len(100)={:5.2f}  eps={:.3f}'
                  '  elapsed={:.0f}s'.format(
                      s, total, avg, agent.epsilon, time.time() - start))

    if total not in snapshots:
        path = os.path.join(args.out, '{}sess.txt'.format(total))
        agent.save(path)
        print('[{:>7}/{}] (final) -> {}'.format(total, total, path))
    print('Entrainement termine en {:.0f}s.'.format(time.time() - start))


if __name__ == '__main__':
    main()
