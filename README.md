# Contrôles anticorruption & sanctions économiques — démonstration

**Arnold LEGRE** · candidature alternance Contrôles et Conformité

## Pourquoi ce projet

L'offre d'alternance décrit des missions qui m'ont particulièrement intéressé.
Pour mieux les comprendre, j'en ai mis trois en pratique :

1. participer à la préparation des missions de contrôle ;
2. contribuer au suivi de la mise en œuvre des recommandations issues de ces missions ;
3. développer un outil de traitement des données (criblage des tiers contre les listes de sanctions).

## Données

| Réelles | Fictives |
|---|---|
| Liste consolidée des sanctions financières de l'**Union européenne** | le groupe « Énergia » et ses filiales |
| Liste **SDN de l'OFAC** (Trésor américain) | les 200 tiers (fournisseurs, clients, partenaires) |
| Indicateur « **Control of Corruption** » de la Banque mondiale (WGI) | les missions de contrôle et leurs recommandations |

Quatre tiers fictifs reprennent volontairement, avec une variante d'écriture, le nom d'une société
réellement sanctionnée, pour montrer que le criblage les détecte.

## Lancer en local

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Actualiser les données réelles : `python preparer_donnees.py`

## Organisation du code

| Fichier | Rôle |
|---|---|
| `preparer_donnees.py` | télécharge les listes de sanctions et l'indicateur de la Banque mondiale dans `data/` |
| `donnees.py` | données fictives, criblage (similarité des noms), score de priorité de contrôle |
| `streamlit_app.py` | application web |
