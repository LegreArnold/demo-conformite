"""Télécharge les données publiques réelles et les enregistre, allégées, dans data/.

- Liste consolidée des sanctions financières de l'Union européenne
- Liste SDN de l'OFAC (Trésor américain)
- Indicateur « Control of Corruption » (score 0-100) de la Banque mondiale (WGI)

L'application lit ces fichiers figés : elle ne dépend d'aucun site externe au moment
où le recruteur l'ouvre. Relancer ce script pour actualiser les données.
"""
import io
import json
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

ICI = Path(__file__).parent
DATA = ICI / "data"

URL_UE = "https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
URL_OFAC = "https://www.treasury.gov/ofac/downloads/sdn.csv"
URL_BM = "https://api.worldbank.org/v2/fr/country/all/indicator/GOV_WGI_CC.SC?format=json&source=3&mrv=1&per_page=500"
URL_PAYS = "https://api.worldbank.org/v2/fr/country?format=json&per_page=500"


def telecharger(url):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as r:
        return r.read()


def liste_ue():
    df = pd.read_csv(io.BytesIO(telecharger(URL_UE)), sep=";", dtype=str, encoding="utf-8-sig",
                     usecols=["Entity_LogicalId", "Entity_SubjectType_ClassificationCode",
                              "Entity_Regulation_Programme", "NameAlias_WholeName"])
    df = df.dropna(subset=["NameAlias_WholeName"]).drop_duplicates(["Entity_LogicalId", "NameAlias_WholeName"])
    return pd.DataFrame({
        "nom": df["NameAlias_WholeName"].str.strip(),
        "liste": "Union européenne",
        "programme": df["Entity_Regulation_Programme"].fillna(""),
        "type": df["Entity_SubjectType_ClassificationCode"].map({"person": "Personne", "enterprise": "Entité"}).fillna("Entité"),
    })


def liste_ofac():
    df = pd.read_csv(io.BytesIO(telecharger(URL_OFAC)), header=None, dtype=str, encoding="latin-1",
                     usecols=[1, 2, 3], names=["nom", "type", "programme"])
    return pd.DataFrame({
        "nom": df["nom"].str.strip(),
        "liste": "OFAC (États-Unis)",
        "programme": df["programme"].fillna("").str.replace("-0-", "", regex=False).str.strip(),
        "type": df["type"].str.strip().map({"individual": "Personne"}).fillna("Entité"),
    })


def risque_pays():
    pays = json.loads(telecharger(URL_PAYS))[1]
    vrais_pays = {p["id"]: p["name"] for p in pays if p["region"]["value"] != "Agrégats"
                  and p["region"]["id"] != "NA"}
    lignes = json.loads(telecharger(URL_BM))[1]
    df = pd.DataFrame([{"iso3": l["countryiso3code"], "pays": vrais_pays[l["countryiso3code"]],
                        "score_controle_corruption": l["value"], "annee": l["date"]}
                       for l in lignes if l["countryiso3code"] in vrais_pays and l["value"] is not None])
    return df.sort_values("pays").reset_index(drop=True)


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    sanctions = pd.concat([liste_ue(), liste_ofac()], ignore_index=True).drop_duplicates()
    sanctions.to_csv(DATA / "listes_sanctions.csv", index=False, encoding="utf-8")
    pays = risque_pays()
    pays.to_csv(DATA / "risque_pays.csv", index=False, encoding="utf-8")
    (DATA / "sources.json").write_text(json.dumps({
        "date_extraction": date.today().isoformat(),
        "nb_noms_ue": int((sanctions.liste == "Union européenne").sum()),
        "nb_noms_ofac": int((sanctions.liste == "OFAC (États-Unis)").sum()),
        "annee_wgi": pays["annee"].max(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(sanctions)} noms sur les listes de sanctions, {len(pays)} pays")
