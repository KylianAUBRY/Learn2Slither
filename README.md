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
| `-board-size N`  | `10`     | Taille du plateau N×N, minimum 5 **[bonus]**         |

### Exemples

```bash
# Entraîner 1000 sessions sans affichage et sauvegarder
python3 main.py -sessions 1000 -visual off -save models/1000sess.txt

# Regarder jouer un modèle entraîné (sans continuer à apprendre)
python3 main.py -load models/10000sess.txt -dontlearn -visual on -speed fast

# Mode pas à pas pour observer la vision à chaque coup
python3 main.py -load models/10000sess.txt -dontlearn -step-by-step

# Centre de contrôle graphique (lance tous les scénarios à la souris)
python3 snake.py
```

---

## Entraînement (`train.py`)

`main.py` joue / entraîne sur **une seule** taille. Pour produire les modèles
fournis on utilise `train.py` : il entraîne **un seul** agent en continu et
sauvegarde des **instantanés** de la Q-table aux paliers demandés.

```bash
# Échelle complète, une seule taille (10×10)
python3 train.py -sessions 100000 \
                 -snapshots 1 10 100 1000 10000 100000

# Multi-tailles (bonus « taille variable ») : une seule Q-table qui
# joue ensuite sur 8×8 … 20×20 … et au-delà (~9 min)
python3 train.py -sessions 100000 -sizes 8 10 12 15 20 \
                 -snapshots 1 10 100 1000 10000 100000
```

Comme l'état encode des distances **relatives** à la taille du plateau, tirer
une taille au hasard à chaque session (`-sizes`) apprend une politique qui
**généralise** : le même `.txt` joue correctement sur n'importe quelle taille
sans ré-entraînement. Un modèle entraîné seulement en 10×10 grossit certes
beaucoup sur grande carte, mais erre (il met ~3× plus de pas par pomme) ; le
multi-tailles corrige cette navigation.

---

## Modèles fournis

Les modèles sont générés par `train.py` : **un seul** agent entraîné en
continu en **multi-tailles** (`-sizes 8 10 12 15 20`), avec un instantané
sauvegardé à chaque palier. Les distances étant relatives, le même `.txt`
joue sur n'importe quelle taille.

Mesures sur **200 sessions** par modèle (10×10, `-dontlearn`), longueur en
fin de session :

| Modèle                   | Long. moyenne | Fin ≥ 10 | Record |
|--------------------------|---------------|----------|--------|
| `models/1sess.txt`       | 3.1           | 0 %      | 5      |
| `models/10sess.txt`      | 3.1           | 0 %      | 5      |
| `models/100sess.txt`     | 3.2           | 0 %      | 5      |
| `models/1000sess.txt`    | 4.1           | 0 %      | 9      |
| `models/10000sess.txt`   | 15.8          | 80 %     | 37     |
| `models/100000sess.txt`  | **23.5**      | **99.5 %** | **38** |

Cible du sujet : longueur 10 en fin de session (critère d'évaluation :
plus de 50 % des parties) — le modèle final y est à 99.5 %. La politique
ne devient performante qu'à partir de `~10000sess` ; `100000sess` est le
**sweet spot** (au-delà, la Q-table dérive, voir Hyperparamètres).

**Sur grande carte**, le même `100000sess.txt` sans réentraînement :
moyenne 31.6 en 15×15 (record 60), 38.9 en 20×20 (record 61), 53.8 en
30×30 (record 88). Le serpent grossit davantage (plus de place) mais
**erre** : avec la vision en croix, les 2 pommes d'un plateau 30×30 sont
hors des 4 rayons ~87 % du temps, donc invisibles. Il cherche à l'aveugle
et meurt surtout en se mordant. C'est le plafond intrinsèque de la vision
en croix, pas un défaut d'entraînement — l'entraînement multi-tailles ne
change pas l'efficacité (mesuré) ; il sert à valider le bonus « taille
variable ».

---

## Architecture

| Fichier          | Rôle                                                          |
|------------------|---------------------------------------------------------------|
| `main.py`        | Point d'entrée CLI, boucle de jeu / entraînement (1 taille)   |
| `train.py`       | Entraînement headless : snapshots progressifs + multi-tailles |
| `environment.py` | Plateau, serpent, pommes, vision, règles, récompenses         |
| `agent.py`       | Agent Q-learning (Q-table sparse, ε-greedy, save/load JSON)   |
| `display.py`     | Affichage graphique Pygame du plateau + statistiques          |
| `snake.py`       | Centre de contrôle GUI Pygame (bonus, voir ci-dessous)        |

### État (vision → 16 bits)

Pour chacune des 4 directions (haut, droite, bas, gauche), **4 bits** :

- **bits 0-1 — distance à l'obstacle** (mur ou corps le plus proche), en
  seau proportionnel à la taille : `00` collé, `01` proche (≤ 30 %),
  `10` moyen (≤ 60 %), `11` dégagé ;
- **bits 2-3 — distance à la pomme verte** la plus proche visible
  (`00` = aucune), même découpage en seaux.

Encoder des **distances graduées** (et non juste « visible / pas visible »)
permet au serpent de viser la pomme la plus proche et d'anticiper les
obstacles 2-3 coups à l'avance. Les distances étant **relatives** à la
taille du plateau, un modèle entraîné en 10×10 fonctionne sur n'importe
quelle taille. Les pommes rouges sont **volontairement absentes** de
l'état : une variante 24 bits les encodant a été entraînée et mesurée
moins bonne (espace d'états ×7 — 62 k états contre 9 k —, apprentissage
fragmenté pour un bénéfice marginal).

### Récompenses

| Événement              | Récompense |
|------------------------|------------|
| Pomme verte            | +20        |
| Pomme rouge            | −10        |
| Déplacement            | −1         |
| Game over (mur / soi)  | −100       |
| Timeout (boucle)       | −50        |

Anti-boucle : une session s'arrête si plus de `100 × longueur` pas
s'écoulent sans manger de pomme verte.

### Hyperparamètres

`alpha=0.1`, `gamma=0.95`, `epsilon` 1.0 → 0.01 (decay 0.9998 par session).

> Le decay lent (0.9998) maintient l'exploration : epsilon n'atteint son
> plancher (0.01) que vers ~23 000 sessions. Un plancher bas compte pour
> les grandes longueurs : à ε = 0.1, un coup sur dix est aléatoire et tue
> le serpent avant qu'il n'atteigne (donc n'apprenne) les états de
> longueur 30+. Les petits modèles (`1`…`1000sess`) explorent encore
> beaucoup ; la politique ne devient performante qu'à partir de
> `~10000sess`. Au-delà de ~100 000 sessions la performance **redescend**
> lentement (mesuré à 200k/300k/600k : α constant + quasi-exploitation
> font dériver la Q-table) — l'échelle s'arrête donc à `100000sess`,
> le sweet spot mesuré.

---

## Bonus

- Taille de plateau variable (`-board-size`), état position-agnostique.
- Affichage soigné : grille, panneau de stats, vitesses réglables, écran de
  fin (récapitulatif sessions / longueur max / durée max / score moyen).

### Centre de contrôle (`snake.py`)

Une interface Pygame unique qui pilote `main.py` pour tous les usages du
sujet. Chaque action lance `main.py` en sous-processus avec les bons
arguments, et sa sortie défile en direct dans le journal en bas.

- **Onglet Scénarios** : boutons un-clic — entraîner 1 / 10 / 100 / 1000 /
  10000 sessions (sauvegarde dans `models/`), regarder le meilleur modèle
  jouer, mode pas-à-pas, évaluation sur 30 parties.
- **Onglet Personnalisé** : tous les flags de `main.py` (sliders,
  menus, cases à cocher) avec aperçu de la commande en temps réel.
- **Onglet Modèles** : liste de `models/*.txt` avec nombre d'états,
  epsilon et taille ; boutons *Regarder* / *Évaluer* par modèle.

```bash
python3 snake.py
```

> Si `pygame` n'est pas installé dans le Python courant (ex. Python 3.14),
> `snake.py` se relance automatiquement avec `.venv/bin/python` quand le
> venv existe ; sinon il affiche un message d'installation clair.
