"""Démo de candidature — trois missions de l'offre mises en pratique.

Accueil compréhensible en 10 secondes sans notion de conformité (recruteur RH).
Données réelles : listes de sanctions UE et OFAC, risque pays Banque mondiale.
Données fictives : le groupe « Énergia », ses tiers et ses contrôles.
"""
import io
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from donnees import (AUJOURDHUI, SEUIL_SIMILARITE, charger_reel, cribler, generer_recommandations,
                     generer_tiers, priorites)

ICI = Path(__file__).parent
CV_PDF = ICI / "assets" / "CV_Arnold_LEGRE.pdf"
COULEURS_PRIORITE = {"Haute": "#B91C1C", "Moyenne": "#D97706", "Faible": "#9CA3AF"}
COULEURS_STATUT = {"Mise en œuvre": "#15803D", "En cours": "#93A3B8", "En retard": "#B91C1C"}

st.set_page_config(page_title="Candidature contrôles et conformité — Arnold LEGRE",
                   page_icon=":material/verified_user:", layout="wide")


@st.cache_data(show_spinner="Criblage des tiers contre les listes de sanctions…")
def calculer():
    sanctions, pays, sources = charger_reel()
    criblage = cribler(generer_tiers(sanctions), sanctions)
    reco = generer_recommandations()
    return criblage, reco, priorites(pays, criblage, reco), sources, len(sanctions)


@st.cache_data
def fichier_power_bi(criblage, reco, prio):
    tampon = io.BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as xl:
        prio.to_excel(xl, sheet_name="Priorites", index=False)
        reco.to_excel(xl, sheet_name="Recommandations", index=False)
        criblage.to_excel(xl, sheet_name="Criblage", index=False)
    return tampon.getvalue()


def citation(texte):
    """Phrase de l'offre, citée mot pour mot."""
    st.markdown(f"<div style='border-left:3px solid #D9472B;padding-left:.7rem;color:#4B5563;"
                f"font-style:italic;margin-bottom:.8rem'>« {texte} »</div>", unsafe_allow_html=True)


def grand_chiffre(valeur, legende, couleur="#1F2328"):
    st.markdown(f"<p style='font-size:2rem;font-weight:700;color:{couleur};margin:0'>{valeur}</p>"
                f"<p style='color:#4B5563;margin-top:0'>{legende}</p>", unsafe_allow_html=True)


criblage, reco, prio, sources, nb_noms = calculer()
alertes = criblage[criblage.alerte].sort_values("similarite", ascending=False)
date_listes = pd.Timestamp(sources["date_extraction"]).strftime("%d/%m/%Y")

# =============================================================================
#  Accueil — compréhensible en 10 secondes, sans jargon
# =============================================================================
st.caption("Candidature · Alternance Contrôles et Conformité Anticorruption & Sanctions Économiques — TotalEnergies")
st.markdown("## Pourquoi cette page ?")
st.markdown(
    "<p style='font-size:1.15rem;line-height:1.6;max-width:56rem'>"
    "Votre offre décrit des missions qui m'ont particulièrement intéressé. Pour mieux les comprendre, "
    "<b>j'en ai mis trois en pratique</b>, en m'appuyant sur les <b>vraies listes officielles de sanctions</b>. "
    "Voici le résultat.</p>", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3, gap="medium")

with m1, st.container(border=True):
    st.markdown("**MISSION 1**")
    st.caption("Votre offre :")
    citation("Participer à la préparation des missions de contrôle")
    st.markdown("**Ce que j'ai fait :** un classement qui indique **quelles filiales contrôler en premier**, "
                "selon le risque de corruption de leur pays et les alertes détectées.")
    barres = alt.Chart(prio).mark_bar(cornerRadius=3, height=16).encode(
        y=alt.Y("entite:N", sort=None, title=None, axis=alt.Axis(labelLimit=150)),
        x=alt.X("score:Q", title=None, axis=None, scale=alt.Scale(domain=[0, 110])),
        color=alt.Color("priorite:N", title=None, legend=alt.Legend(orient="bottom"),
                        scale=alt.Scale(domain=list(COULEURS_PRIORITE), range=list(COULEURS_PRIORITE.values()))),
        tooltip=[alt.Tooltip("entite:N", title="Filiale"), alt.Tooltip("pays:N", title="Pays"),
                 alt.Tooltip("score:Q", title="Score de priorité"), alt.Tooltip("alertes:Q", title="Alertes"),
                 alt.Tooltip("retards:Q", title="Recommandations en retard")])
    textes = barres.mark_text(align="left", dx=4, fontWeight="bold").encode(text="score:Q", color=alt.value("#1F2328"))
    st.altair_chart((barres + textes).configure_view(stroke=None), height=260)
    st.caption("Filiales d'un groupe fictif. Le risque pays vient d'une donnée réelle de la Banque mondiale.")

with m2, st.container(border=True):
    st.markdown("**MISSION 2**")
    st.caption("Votre offre :")
    citation("Contribuer au suivi de la mise en oeuvre des recommandations issues de ces missions")
    st.markdown("**Ce que j'ai fait :** un suivi qui montre, pour chaque filiale, **ce qui a été corrigé** "
                "après un contrôle, et **ce qui prend du retard**.")
    taux = (reco.statut == "Mise en œuvre").mean()
    gauche, droite = st.columns(2)
    with gauche:
        grand_chiffre(f"{taux:.0%}".replace("%", " %"), "des recommandations mises en œuvre", "#15803D")
    with droite:
        grand_chiffre(int((reco.statut == "En retard").sum()), "recommandations en retard", "#B91C1C")
    empile = alt.Chart(reco).mark_bar(height=14).encode(
        y=alt.Y("entite:N", sort=prio.entite.tolist(), title=None, axis=alt.Axis(labelLimit=150)),
        x=alt.X("count():Q", title=None, axis=None),
        color=alt.Color("statut:N", title=None, legend=alt.Legend(orient="bottom"),
                        scale=alt.Scale(domain=list(COULEURS_STATUT), range=list(COULEURS_STATUT.values()))),
        order=alt.Order("statut:N", sort="descending"),
        tooltip=[alt.Tooltip("entite:N", title="Filiale"), alt.Tooltip("statut:N", title="Statut"),
                 alt.Tooltip("count():Q", title="Nombre")])
    st.altair_chart(empile.configure_view(stroke=None), height=230)

with m3, st.container(border=True):
    st.markdown("**MISSION 3**")
    st.caption("Votre offre :")
    citation("Développer un outil Power BI de traitement des données statistiques")
    st.markdown(f"**Ce que j'ai fait :** un outil qui compare automatiquement **{len(criblage)} fournisseurs et "
                f"partenaires** aux **{nb_noms:,} noms** des listes officielles de sanctions (Union européenne "
                "et États-Unis), et signale ceux qui se ressemblent.".replace(",", " "))
    grand_chiffre(f"{len(alertes)} alertes", f"sur {len(criblage)} tiers, à vérifier par un analyste", "#B91C1C")
    st.dataframe(
        alertes[["tiers", "nom_liste", "similarite"]], hide_index=True, width="stretch",
        column_config={"tiers": "Tiers (fictif)", "nom_liste": "Nom sur la liste officielle",
                       "similarite": st.column_config.ProgressColumn("Ressemblance", format="%d %%",
                                                                     min_value=0, max_value=100)})
    st.caption("Une alerte n'est pas une preuve : « Nordel Marine » ressemble à « Nord Marine » "
               "sans être la même société. C'est à l'analyste de trancher.")
    st.download_button("Les données prêtes pour Power BI", fichier_power_bi(criblage, reco, prio),
                       file_name="Donnees_controles_conformite_demo.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       icon=":material/table_view:", width="stretch")

st.write("")
with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
    if CV_PDF.exists():
        st.download_button("Télécharger mon CV", CV_PDF.read_bytes(), file_name="CV_Arnold_LEGRE.pdf",
                           mime="application/pdf", icon=":material/description:", type="primary")
    st.markdown("**Arnold LEGRE** · :material/mail: legrearnold@gmail.com · "
                ":material/call: +33 7 59 34 19 07 · "
                ":material/code: [github.com/LegreArnold](https://github.com/LegreArnold)")
st.caption(f":material/info: **Données réelles** : listes de sanctions UE et OFAC (extraites le {date_listes}), "
           f"indicateur « Control of Corruption » de la Banque mondiale ({sources['annee_wgi']}). "
           "**Données fictives** : le groupe « Énergia », ses filiales, ses tiers et ses contrôles.")

# =============================================================================
#  Méthode — pour l'équipe conformité
# =============================================================================
with st.expander("Méthode et sources, pour l'équipe conformité", icon=":material/fact_check:"):
    st.markdown(
        f"- **Criblage** : noms normalisés (casse, accents, ponctuation, formes juridiques), puis similarité "
        f"*token sort ratio* avec chaque entité des listes ; alerte à partir de **{SEUIL_SIMILARITE} %**. "
        "Quatre tiers reprennent volontairement, avec une variante d'écriture, le nom d'une société réellement "
        "sanctionnée ; les deux autres alertes sont de vrais faux positifs, à écarter après analyse.\n"
        "- **Priorité de contrôle** (0 à 100) : 60 % du risque pays (100 − score « Control of Corruption ») "
        "+ 20 points par alerte sanctions + 5 points par recommandation en retard, plafonné à 100.\n"
        f"- **Recommandations** : statut au {AUJOURDHUI:%d/%m/%Y} ; « en retard » = échéance dépassée sans mise en œuvre.\n"
        "- **Sources** : [liste consolidée des sanctions financières de l'UE]"
        "(https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions), "
        "[liste SDN de l'OFAC](https://sanctionslist.ofac.treas.gov/), "
        "[Worldwide Governance Indicators, Banque mondiale](https://www.worldbank.org/en/publication/worldwide-governance-indicators)."
    )
    onglet_prio, onglet_reco, onglet_crib = st.tabs(["Priorités de contrôle", "Recommandations", "Criblage complet"])
    with onglet_prio:
        st.dataframe(prio, hide_index=True, column_config={
            "entite": "Filiale", "pays": "Pays", "risque_pays": "Risque pays", "alertes": "Alertes sanctions",
            "retards": "Reco. en retard", "score": "Score", "priorite": "Priorité"})
    with onglet_reco:
        st.dataframe(reco.sort_values(["statut", "echeance"]), hide_index=True, column_config={
            "entite": "Filiale", "theme": "Thème", "echeance": st.column_config.DateColumn("Échéance", format="DD/MM/YYYY"),
            "statut": "Statut"})
    with onglet_crib:
        st.dataframe(criblage.sort_values("similarite", ascending=False), hide_index=True, column_config={
            "tiers": "Tiers", "entite": "Filiale", "categorie": "Catégorie", "similarite": "Ressemblance (%)",
            "nom_liste": "Nom le plus proche", "liste": "Liste", "programme": "Programme", "alerte": "Alerte"})
