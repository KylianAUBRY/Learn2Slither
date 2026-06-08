# Learn2Slither

Un serpent qui apprend à jouer tout seul par **apprentissage par renforcement**
(Q-learning). Le serpent ne perçoit que sa **vision en croix** (4 directions
depuis sa tête) et doit apprendre à manger les pommes vertes, éviter les rouges,
les murs et son propre corps.

Projet 42.

---

## Installation

Le mode d'entraînement *headless* (`-visual off`) ne dépend de rien d'autre que
Python 3. L'**affichage graphique** (`-visual on`) et le **launcher** ont besoin
de `pygame`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> `pygame` ne se compile pas encore sur Python 3.14 ; utilisez Python 3.12 ou
> 3.13 pour le mode visuel (`python3.12 -m venv .venv`). L'entraînement
> `-visual off` fonctionne avec n'importe quelle version de Python 3.

---

## Utilisation

```bash
python3 main.py [options]
```

| Option           | Défaut   | Description                                          |
|------------------|----------|------------------------------------------------------|
| `-sessions N`    | `100`    | Nombre de parties d'entraînement                     |
| `-visual on/off` | `on`     | Affichage graphique + vision terminal                |
| `-speed`         | `normal` | `slow` / `normal` / `fast` / `max`                   |
| `-load FILE`     | —        | Charger un modèle (Q-table)                          |
| `-save FILE`     | —        | Sauvegarder le modèle à la fin                       |
| `-dontlearn`     | off      | Désactive l'apprentissage (exploitation pure)        |
| `-step-by-step`  | off      | Avance pas à pas (SPACE)                              |
| `-board-size N`  | `10`     | Taille du plateau N×N **[bonus]**                    |

### Exemples

```bash
# Entraîner 1000 sessions sans affichage et sauvegarder
python3 main.py -sessions 1000 -visual off -save models/1000sess.txt

# Regarder jouer un modèle entraîné (sans continuer à apprendre)
python3 main.py -load models/10000sess.txt -dontlearn -visual on -speed fast

# Mode pas à pas pour observer la vision à chaque coup
python3 main.py -load models/10000sess.txt -dontlearn -step-by-step

# Launcher graphique (configure et lance tout à la souris)
python3 snake.py
```

---

## Modèles fournis

Chaque modèle est entraîné depuis zéro avec N sessions (montre la progression).

| Modèle                  | Longueur max atteinte |
|-------------------------|-----------------------|
| `models/1sess.txt`      | 3                     |
| `models/10sess.txt`     | 4                     |
| `models/100sess.txt`    | 6                     |
| `models/1000sess.txt`   | 26                    |
| `models/10000sess.txt`  | 38                    |

Cible du sujet : longueur 10. Le modèle 10000 dépasse largement (et survit
jusqu'à la limite de pas).

---

## Architecture

| Fichier          | Rôle                                                          |
|------------------|---------------------------------------------------------------|
| `main.py`        | Point d'entrée CLI, boucle d'entraînement                     |
| `environment.py` | Plateau, serpent, pommes, vision, règles, récompenses         |
| `agent.py`       | Agent Q-learning (Q-table sparse, ε-greedy, save/load JSON)   |
| `display.py`     | Affichage graphique Pygame du plateau + statistiques          |
| `snake.py`       | Launcher GUI Pygame (bonus)                                   |

### État (vision → 12 features)

Pour chacune des 4 directions (haut, droite, bas, gauche) :

- **danger** : distance au premier obstacle (mur ou corps), plafonnée à 3 ;
- **pomme verte** visible dans le rayon (0/1) ;
- **pomme rouge** visible dans le rayon (0/1).

L'état est dérivé uniquement de la vision et est **indépendant de la taille du
plateau** : un modèle entraîné en 10×10 fonctionne sur n'importe quelle taille.

### Récompenses

| Événement      | Récompense |
|----------------|------------|
| Pomme verte    | +10        |
| Pomme rouge    | −10        |
| Déplacement    | −0.1       |
| Game over      | −100       |

### Hyperparamètres

`alpha=0.1`, `gamma=0.9`, `epsilon` 1.0 → 0.05 (decay 0.995).

---

## Bonus

- Taille de plateau variable (`-board-size`), état position-agnostique.
- Launcher graphique (`snake.py`) avec aperçu de commande en direct.
- Affichage soigné : grille, panneau de stats, vitesses réglables.
