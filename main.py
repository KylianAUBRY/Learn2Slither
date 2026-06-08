#!/usr/bin/python3
"""
main.py - Point d'entree Learn2Slither.

Usage:
  python3 main.py -sessions 10 -save models/10sess.txt -visual off
  python3 main.py -visual on -load models/100sess.txt -sessions 10
  python3 main.py -visual on -load models/1000sess.txt -dontlearn
"""

import argparse
import os
import sys

from environment import Environment, ACTION_NAMES
from agent import QAgent


def parse_args():
    p = argparse.ArgumentParser(
        description='Learn2Slither - Snake Reinforcement Learning'
    )
    p.add_argument(
        '-sessions', type=int, default=100,
        help='Nombre de sessions (defaut: 100)'
    )
    p.add_argument(
        '-visual', choices=['on', 'off'], default='on',
        help='Affichage graphique on/off (defaut: on)'
    )
    p.add_argument(
        '-speed',
        choices=['slow', 'normal', 'fast', 'max'],
        default='normal',
        help='Vitesse affichage (defaut: normal)'
    )
    p.add_argument(
        '-load', type=str, default=None,
        help='Charger un modele depuis ce fichier'
    )
    p.add_argument(
        '-save', type=str, default=None,
        help='Sauvegarder le modele dans ce fichier'
    )
    p.add_argument(
        '-dontlearn', action='store_true',
        help='Desactiver la mise a jour Q-table'
    )
    p.add_argument(
        '-step-by-step', dest='step_by_step', action='store_true',
        help='Mode pas a pas (SPACE pour avancer)'
    )
    p.add_argument(
        '-board-size', dest='board_size', type=int, default=10,
        help='Taille plateau NxN (defaut: 10) [BONUS]'
    )
    return p.parse_args()


def run(args):
    visual = args.visual == 'on'
    sessions = args.sessions

    env = Environment(size=args.board_size)
    agent = QAgent(learn=not args.dontlearn)

    if args.load:
        if not os.path.exists(args.load):
            print(
                'Erreur: fichier "{}" introuvable.'.format(args.load),
                file=sys.stderr
            )
            sys.exit(1)
        agent.load(args.load)

    display = None
    if visual:
        try:
            from display import GameDisplay
            display = GameDisplay(
                board_size=args.board_size, speed=args.speed
            )
        except ImportError:
            print(
                'Avertissement: pygame introuvable, affichage '
                'graphique desactive.\n'
                '  Installez-le (pip install pygame) ou utilisez '
                '-visual off.\n'
                '  La vision terminal reste affichee.',
                file=sys.stderr
            )

    max_length = 0
    max_duration = 0
    total_score = 0.0

    print('\n' + '=' * 60)
    print('  Learn2Slither - {} sessions | visual={} | speed={}'.format(
        sessions, args.visual, args.speed
    ))
    print('  board={}x{} | learn={} | step={}'.format(
        args.board_size, args.board_size,
        not args.dontlearn, args.step_by_step
    ))
    print('=' * 60 + '\n')

    for session in range(1, sessions + 1):
        state = env.reset()
        done = False
        session_score = 0.0
        action_name = ''

        while not done:
            action = agent.choose_action(state)
            action_name = ACTION_NAMES[action]

            if visual:
                env.print_vision(action_name)

            next_state, reward, done = env.step(action)
            agent.update(state, action, reward, next_state, done)
            session_score += reward
            state = next_state

            if display:
                display.render(
                    board=env.get_board(),
                    session=session,
                    max_sessions=sessions,
                    score=session_score,
                    length=env.length,
                    steps=env.steps,
                    action_name=action_name,
                    epsilon=agent.epsilon,
                    step_mode=args.step_by_step,
                )
                if args.step_by_step and not done:
                    display.wait_for_step()

        agent.decay_epsilon()
        max_length = max(max_length, env.length)
        max_duration = max(max_duration, env.steps)
        total_score += session_score

        report_every = max(1, sessions // 20)
        if session % report_every == 0 or session == sessions:
            print(
                '\r[{:>6}/{}]  length={:>3}  steps={:>4}'
                '  score={:>8.1f}  e={:.4f}  Q={}'.format(
                    session, sessions, env.length, env.steps,
                    session_score, agent.epsilon, agent.q_table_size
                )
            )
        elif not visual:
            print(
                '\r  [{:>6}/{}]  steps={:>4}  score={:>8.1f}'.format(
                    session, sessions, env.steps, session_score
                ),
                end='', flush=True
            )

    print(
        '\nGame over, max length = {}, max duration = {}'.format(
            max_length, max_duration
        )
    )
    print('Score moyen: {:.2f} | Sessions: {}'.format(
        total_score / sessions, sessions
    ))

    if args.save:
        agent.save(args.save)

    if display:
        display.close()


if __name__ == '__main__':
    run(parse_args())
