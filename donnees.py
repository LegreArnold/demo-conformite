"""Données de la démo.

Réelles (dossier data/, voir preparer_donnees.py) : listes de sanctions UE et OFAC,
score « Control of Corruption » de la Banque mondiale.
Fictives (générées ici) : le groupe « Énergia », ses entités, leurs tiers,
les missions de contrôle et leurs recommandations.
"""
import json
import random
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

DATA = Path(__file__).parent / "data"
AUJOURDHUI = date(2026, 10, 20)
SEUIL_SIMILARITE = 90   # au-delà, le nom est signalé pour vérification

# Entités du groupe fictif : (nom, code pays ISO3)
ENTITES = [
    ("Énergia France", "FRA"), ("Énergia Nigeria", "NGA"), ("Énergia Angola", "AGO"),
    ("Énergia Brasil", "BRA"), ("Énergia Mozambique", "MOZ"), ("Énergia Kazakhstan", "KAZ"),
    ("Énergia India", "IND"), ("Énergia Gulf", "ARE"),
]

PREFIXES = ["Atlas", "Boréal", "Kerlan", "Solvane", "Meridia", "Orvane", "Talvik", "Nordel", "Castelor",
            "Vireo", "Arkane", "Belmonte", "Cyrano", "Duvalis", "Estrella", "Falcor", "Galena", "Horizonte",
            "Ivora", "Jaspe", "Kaliko", "Lumen", "Marbella", "Novaro", "Opaline", "Pradera", "Quartzia"]
METIERS = ["Logistique", "Forage", "Ingénierie", "Maintenance", "Transport", "Services", "Équipements",
           "Câblage", "Conseil", "Sécurité", "Énergie", "Industrie", "Marine", "Travaux"]
FORMES = ["SARL", "SA", "Ltd", "SAS", "Lda", "Group"]
STATUTS = ["Mise en œuvre", "En cours", "En retard"]
THEMES = ["Cadeaux et invitations", "Évaluation des tiers", "Paiements de facilitation", "Conflits d'intérêts",
          "Clauses anticorruption des contrats", "Formation des collaborateurs", "Criblage sanctions des clients",
          "Contrôle des exportations"]

_FORMES_JURIDIQUES = r"\b(LLC|LTD|LIMITED|SARL|SAS|SA|JSC|OJSC|PJSC|OOO|CO|COMPANY|INC|CORP|GROUP|LDA|FZE|FZCO)\b"


def normaliser(nom):
    """Majuscules, sans accents, ponctuation ni forme juridique : pour comparer les noms."""
    nom = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode().upper()
    nom = re.sub(r"[^A-Z0-9 ]", " ", nom)
    nom = re.sub(_FORMES_JURIDIQUES, " ", nom)
    return re.sub(r"\s+", " ", nom).strip()


def charger_reel():
    sanctions = pd.read_csv(DATA / "listes_sanctions.csv", dtype=str).fillna("")
    pays = pd.read_csv(DATA / "risque_pays.csv")
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    return sanctions, pays, sources


def generer_tiers(sanctions, graine=2026):
    """200 tiers fictifs ; 4 d'entre eux reprennent volontairement, avec une petite variante
    d'écriture, le nom d'une entité réellement sanctionnée, pour montrer que le criblage les détecte."""
    rng = random.Random(graine)
    noms = set()
    while len(noms) < 196:
        noms.add(f"{rng.choice(PREFIXES)} {rng.choice(METIERS)} {rng.choice(FORMES)}")
    # pièges choisis parmi des sociétés sanctionnées pour des motifs commerciaux (Russie, Iran)
    entites_listees = sanctions[(sanctions.type == "Entité") & sanctions.nom.str.len().between(14, 32)
                                & sanctions.nom.str.match(r"^[A-Za-z0-9 .,&-]+$")
                                & sanctions.programme.str.contains(r"RUSSIA|IRAN", regex=True)
                                & sanctions.nom.str.contains(r"LLC|LTD|LIMITED|COMPANY|TRADING|JSC", regex=True)]
    pieges = entites_listees.sample(4, random_state=graine).nom.tolist()
    # petite variante d'écriture (casse, ponctuation), comme dans une vraie base fournisseurs
    variantes = [p.title() for p in pieges[:2]] + [p.replace(",", "").replace(".", "").title() for p in pieges[2:]]
    tiers = pd.DataFrame({"tiers": sorted(noms) + variantes})
    tiers["entite"] = [rng.choice(ENTITES)[0] for _ in range(len(tiers))]
    tiers["categorie"] = [rng.choice(["Fournisseur", "Sous-traitant", "Client", "Partenaire"]) for _ in range(len(tiers))]
    return tiers


def cribler(tiers, sanctions):
    """Compare chaque tiers à toutes les entités des listes de sanctions (similarité de 0 à 100)."""
    cible = sanctions[sanctions.type == "Entité"].reset_index(drop=True)
    choix = cible.nom.map(normaliser).tolist()
    resultats = []
    for nom in tiers.tiers:
        meilleur = process.extractOne(normaliser(nom), choix, scorer=fuzz.token_sort_ratio)
        nom_liste, score, i = meilleur
        resultats.append({"similarite": round(score), "nom_liste": cible.nom[i],
                          "liste": cible.liste[i], "programme": cible.programme[i]})
    out = pd.concat([tiers.reset_index(drop=True), pd.DataFrame(resultats)], axis=1)
    out["alerte"] = out.similarite >= SEUIL_SIMILARITE
    return out


def generer_recommandations(graine=2026):
    """Recommandations fictives issues des missions de contrôle des 12 derniers mois."""
    rng = random.Random(graine)
    lignes = []
    for entite, _ in ENTITES:
        for k in range(rng.randint(4, 8)):
            echeance = date(2026, rng.randint(3, 12), rng.randint(1, 28))
            if echeance > AUJOURDHUI:
                statut = rng.choices(["Mise en œuvre", "En cours"], weights=[3, 7])[0]
            else:
                statut = rng.choices(["Mise en œuvre", "En retard"], weights=[7, 3])[0]
            lignes.append({"entite": entite, "theme": rng.choice(THEMES), "echeance": echeance, "statut": statut})
    return pd.DataFrame(lignes)


def priorites(pays, criblage, reco):
    """Score de priorité de contrôle par entité, de 0 à 100 :
    60 % risque pays (100 − score Banque mondiale) + 20 points par alerte sanctions
    + 5 points par recommandation en retard, plafonné à 100."""
    risque = pays.set_index("iso3").score_controle_corruption
    lignes = []
    for entite, iso3 in ENTITES:
        risque_pays = 100 - risque[iso3]
        alertes = int(criblage[(criblage.entite == entite) & criblage.alerte].shape[0])
        retards = int(reco[(reco.entite == entite) & (reco.statut == "En retard")].shape[0])
        score = min(100, 0.6 * risque_pays + 20 * alertes + 5 * retards)
        lignes.append({"entite": entite, "pays": pays.set_index("iso3").pays[iso3],
                       "risque_pays": round(risque_pays), "alertes": alertes, "retards": retards,
                       "score": round(score)})
    df = pd.DataFrame(lignes).sort_values("score", ascending=False).reset_index(drop=True)
    df["priorite"] = pd.cut(df.score, [-1, 35, 55, 101], labels=["Faible", "Moyenne", "Haute"]).astype(str)
    return df
