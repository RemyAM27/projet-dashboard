# Dashboard : Accidents de la route en France (2024)

Ce projet est un tableau de bord interactif (dashboard) qui présente une analyse complète des accidents corporels de la route survenus en France en 2024, à partir des données officielles de la Sécurité routière.

## Objectif

Ce tableau de bord présente une analyse complète des accidents corporels de la route survenus en France en 2024, à partir des données officielles de la Sécurité routière.

L'objectif est de visualiser et de comprendre la répartition spatiale et temporelle des accidents, ainsi que les profils les plus concernés.


* **Ce dashboard contient plusieurs visualisations de données interactives** : 

    * Une carte choroplèthe d'intensité d'accident par département
    * Une liste déroulante / Recherche précise par département
    * Un histogramme des accidents par âge
    * Un diagramme en anneau (donut) illustrant la gravité des victimes (Indemne, Léger, Hospitalisé, Tué), avec un filtre par profil
    * Un graphique en courbe montrant l'évolution du nombre d'accidents mois par mois.
    
## Data

Les données utilisées proviennent de la page :

[Bases de données annuelles des accidents corporels de la circulation routière - Années de 2005 à 2024](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024)

Pour ce projet, nous nous sommes concentrés sur le jeu de données de l'année 2024.

Voici un aperçu de la structure du code du projet :

```
projet-dashboard
|-- .gitignore
|-- .venv
|   |-- *
|-- config.py                                   # fichier de configuration
|-- main.py                                     # fichier principal permettant de lancer le dashboard
|-- requirements.txt                            # liste des packages additionnels requis
|-- README.md
|-- data                                        # les données
│   |-- cleaned
│   |-- raw
│   |-- geo
|-- src                                         # le code source du dashboard
|   |-- components                              # les composants du dashboard
|   |   |-- __init__.py
|   |   |-- component1.py
|   |   |-- component2.py
|   |   |-- footer.py
|   |   |-- header.py
|   |   |-- navbar.py
|   |-- utils                                   # les fonctions utilitaires
|   |   |-- get_data.py                         # script de récupération des données
|   |   |-- clean_data.py                       # script de nettoyage des données
|   |   |-- data_utils.py                      
|   |   |-- sqlite_utils.py                     
|   |   |-- to_sqlite.py                        # script de conversion des CSV en SQLite
|-- video.mp4

```
## User Guide

Suivez ces étapes pour lancer le projet en local :

1.  **Clonez le dépôt :**
    ```bash
    git clone https://github.com/Remy-AbdoulMazidou/projet-dashboard.git
    cd projet-dashboard
    ```

2.  **Créez un environnement virtuel (recommandé) :**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

3.  **Installez les dépendances :**
    ```bash
    python.exe -m pip install --upgrade pip
    pip install -r requirements.txt 
    ```

4.  **Lancez le dashboard :**
    ```bash
    python main.py
    ```

5.  **Ouvrez votre navigateur :**
    Rendez-vous à l'adresse indiquée par le terminal.
     ```bash
     Dash is running on http://127.0.0.1:8050/
     ```
## Developer Guide : Ajout d'un composant au dashboard

1. **Création d'un nouveau composant** :
   - Créez un nouveau fichier Python dans le dossier approprié (par exemple, `nouveaugraphique.py`).
   - Définissez une fonction qui génère un graphique à l'aide de **Plotly** (par exemple, `build_nouveaugraphique()`).
   - Intégrez ce graphique dans la mise en page du dashboard en utilisant `dash` dans le fichier `main.py`.

2. **Ajouter un graphique à la mise en page** :
   - Dans le fichier `main.py`, ajoutez une nouvelle entrée dans la fonction `layout()` pour afficher votre graphique.

3. **Ajouter un callback** :
   - Si votre graphique nécessite une interaction utilisateur, créez un callback dans le fichier correspondant pour connecter les entrées et les sorties des composants interactifs.
   - 
## Rapport d'analyse et Conclusions

Ce tableau de bord permet de dégager plusieurs tendances et conclusions claires concernant l'accidentologie en France :

Une forte disparité géographique : L'analyse spatiale (via la carte choroplèthe) montre une concentration d'accidents très élevée dans les départements à forte densité urbaine. Paris (75) se détache par exemple avec un nombre d'accidents (4 191) et une intensité "Très élevée", représentant à lui seul 7.8% du total national. Cela suggère que la densité de trafic et la complexité de l'environnement urbain sont des facteurs de risque majeurs.

Les jeunes conducteurs, une population à risque : L'histogramme par âge est sans équivoque. La tranche d'âge des 20-25 ans est la plus impliquée dans les accidents, avec un pic de plus de 12 656 accidents. La courbe décroît ensuite régulièrement avec l'âge, indiquant que les conducteurs plus jeunes et potentiellement moins expérimentés sont surreprésentés.

Une saisonnalité marquée : Le graphique linéaire de l'évolution mensuelle révèle un facteur saisonnier. Le nombre d'accidents est au plus bas en début d'année (février) puis augmente continuellement pour atteindre un pic au cœur de l'été (juin et juillet). Cette tendance coïncide avec les départs en vacances et l'augmentation des déplacements de loisir.

Majorité de blessés légers, mais une part de gravité non négligeable : Le donut de gravité montre que la grande majorité des victimes parmis les majeurs s'en sortent indemnes (42.5%) ou avec des blessures légères (39.2%). Cependant, près d'une victime sur cinq subit des conséquences plus graves : 15.3% sont hospitalisées et 3.0% sont tuées. Cela met en lumière le lourd bilan humain, même si la plupart des accidents ne sont pas mortels.

En conclusion, le dashboard met en évidence que le risque d'accident n'est pas uniforme. Il dépend fortement du lieu (privilégiant les zones urbaines denses), de l'âge (les jeunes étant plus à risque) et de la période de l'année (pics estivaux).

## Copyright

Nous déclarons que l'architecture, la logique principale, l'analyse de ce projet et la majorité du code ont été produits par nous-mêmes.

Nous avons eu recours à des outils d'Intelligence Artificielle Générative (tels que GitHub Copilot et ChatGPT) pour nous aider lors de certains blocages.

L'essentiel du code et les choix de conception demeurent notre propre travail.

## Auteur

* **Rémy ABDOUL MAZIDOU**
* **Antoine LI**   
