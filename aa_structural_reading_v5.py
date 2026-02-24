\
"""
AA Structural Reading V5 (deterministic, frozen)

- Reuses V3.3 selection/extraction to keep case selection stable.
- Uses V4 family scoring (weights + aspect bonuses + house compatibility + tie-break).
- Adds cluster-based arcana selection + intra-theme anti-duplication.
"""
from __future__ import annotations

import json

from collections import defaultdict
from typing import Dict, List, Tuple, Any, Set

from .aa_structural_reading_v3_3 import compute as compute_v3_3, ARCANA_NAMES as ARCANA_NAMES_V33

# -----------------------------
# Normalization
# -----------------------------
ALIASES = {
    "North Node (Mean)": "North Node",
    "North Node": "North Node",
    "Lilith (Black Moon Mean)": "Lilith",
    "Lilith": "Lilith",
}

def norm_body(b: str) -> str:
    return ALIASES.get(b, b)

def load_signs_from_json(path: str) -> Dict[str, str]:
    """Return normalized mapping: body -> sign, from JSON_CU3 file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    m: Dict[str, str] = {}
    for p in data.get("positions", []):
        body = norm_body(p.get("body", ""))
        sign = p.get("sign")
        if body and sign:
            m[body] = sign
    return m


# -----------------------------
# Families (V4 invariant)
# -----------------------------
FAMILIES: Dict[str, str] = {
    "Saturn": "STRUTTURA",
    "Pluto": "TRASFORMAZIONE",
    "Neptune": "DISSOLUZIONE",
    "Uranus": "ROTTURA",
    "Sun": "IDENTITA",
    "Moon": "EMOZIONE",
    "Jupiter": "ESPANSIONE",
    "Venus": "DESIDERIO",
    "Mars": "DESIDERIO",
    "North Node": "KARMICA",
    "Lilith": "KARMICA",
    "Chiron": "KARMICA",
}

# Base weights (V4 invariant)
WEIGHTS: Dict[str, int] = {
    "Saturn": 3,
    "Pluto": 4,
    "Neptune": 2,
    "Uranus": 2,
    "Jupiter": 2,
    "Mars": 1,
    "Venus": 1,
    "Sun": 1,
    "Moon": 1,
    "North Node": 1,
    "Lilith": 1,
    "Chiron": 1,
}

# House × family compatibility (V4 invariant)
HOUSE_COMPAT: Dict[int, Dict[str, int]] = {
    1: {"IDENTITA": 1, "DESIDERIO": 1, "DISSOLUZIONE": -1},
    2: {"STRUTTURA": 1, "DISSOLUZIONE": -1, "ROTTURA": -1},
    3: {"ESPANSIONE": 1},
    4: {"EMOZIONE": 1, "STRUTTURA": 1, "ROTTURA": -1},
    5: {"DESIDERIO": 1, "IDENTITA": 1, "STRUTTURA": -1, "TRASFORMAZIONE": 1},
    6: {"STRUTTURA": 1, "DISSOLUZIONE": -1},
    7: {"DESIDERIO": 1, "STRUTTURA": -1},
    8: {"TRASFORMAZIONE": 1, "KARMICA": 1},
    9: {"ESPANSIONE": 1},
    10: {"STRUTTURA": 1, "IDENTITA": 1, "DESIDERIO": -1},
    11: {"ROTTURA": 1},
    12: {"DISSOLUZIONE": 1, "KARMICA": 1, "STRUTTURA": -1},
}

TIE_ORDER: List[str] = [
    "Saturn","Pluto","Neptune","Uranus","Jupiter","Mars","Venus","Sun","Moon","North Node","Lilith","Chiron"
]

# -----------------------------
# V5 clusters (variable size)
# -----------------------------
CLUSTERS: Dict[str, List[str]] = {
    "STRUTTURA": ["IV","V","VIII","IX"],
    "TRASFORMAZIONE": ["XV","XIII","XVI","XX","XXI"],
    "DISSOLUZIONE": ["XII","XVIII","XVII","XIV"],
    "ROTTURA": ["XXII","XVI","VII","XVII"],
    "IDENTITA": ["XIX","III","VI","IV","I"],
    "EMOZIONE": ["XVIII","II","XIV"],
    "ESPANSIONE": ["X","V","XXI","XIX"],
    "DESIDERIO": ["XV","VI","III","VII","XI"],
    "KARMICA": ["XX","XIII","II","XXII"],
}

# Bonus sets
BONUS_TENSIONE = {"XVI","XV","XIII","XX","XXII"}
BONUS_CONGIUNZIONE = {"IV","XIX","XV","V"}

ARC_BASE_OFFSET: Dict[str,int] = {
    "I": -2,   # Bagatto: avoid winning ties unless supported by signals
    "XI": -2,  # Forza: avoid winning ties unless supported by signals
}

BONUS_CASA: Dict[int, Dict[str,int]] = {
    8: {"XIII": 2, "XX": 2},
    12: {"XII": 2, "XVIII": 2},
    10: {"IV": 2, "XIX": 2},
    5: {"VI": 2, "III": 2},
    7: {"VI": 2, "XX": 2},
}

BONUS_DOM: Dict[str, Dict[str,int]] = {
    "Saturn": {"IV": 1, "V": 1},
    "Pluto": {"XV": 1, "XIII": 1},
    "Neptune": {"XII": 1, "XVIII": 1},
    "Uranus": {"XXII": 1, "XVI": 1},
    "Jupiter": {"X": 1, "XXI": 1},
    "Sun": {"XIX": 1},
    "Moon": {"XVIII": 1},
    "Venus": {"VI": 1, "III": 1},
    "Mars": {"VII": 1, "XI": 1},
    "North Node": {"XX": 1},
    "Chiron": {"II": 1},
}

AspectTuple = Tuple[str, str, str, float]  # (p1,p2,type,orb)

ARCANA_NAMES: Dict[str, str] = dict(ARCANA_NAMES_V33)
ARCANA_NAMES.setdefault("I", "Il Bagatto")
ARCANA_NAMES.setdefault("XI", "La Forza")
ARCANA_NAMES.setdefault("XXII", "Il Matto")
ARCANA_NAMES.setdefault("V", "Il Papa")
ARCANA_NAMES.setdefault("VII", "Il Carro")
ARCANA_NAMES.setdefault("XVII", "La Stella")
ARCANA_NAMES.setdefault("XXI", "Il Mondo")
# -----------------------------
# Output phrases (V6.4)
# -----------------------------
# Deterministic helper text: house function + arcano function.
# These are *not* interpretations; they are fixed labels to aid reading.

HOUSE_PHRASES_DR: Dict[int, Dict[str, str]] = {
    1: {"d": "Identità, postura, iniziativa (come entri nel mondo).", "r": "Tensione nell’identità e nella postura: iniziativa non pienamente allineata."},
    2: {"d": "Valori, risorse, sicurezza materiale (ciò che sostieni e difendi).", "r": "Tensione su valori e risorse: sicurezza materiale/valoriale instabile o contraddetta."},
    3: {"d": "Mente pratica, comunicazione, apprendimento (scambi e linguaggio).", "r": "Tensione nella mente pratica e nella comunicazione: scambi poco fluidi o frammentati."},
    4: {"d": "Radici, intimità, base emotiva (casa interiore).", "r": "Tensione nelle radici e nell’intimità: base emotiva non pacificata o non accessibile."},
    5: {"d": "Desiderio, creatività, espressione (gioco/eros/opera).", "r": "Tensione su desiderio ed espressione: creatività/eros sotto pressione o sbilanciati."},
    6: {"d": "Ritmi, lavoro quotidiano, cura (ordine e manutenzione).", "r": "Tensione su ritmi e manutenzione: lavoro/cura diventano frizione o disordine."},
    7: {"d": "Relazione, patto, specchio (contratto e reciprocità).", "r": "Tensione nei patti: reciprocità difficile, contratti impliciti o non integrati."},
    8: {"d": "Trasformazione, crisi, legami profondi (potere e fiducia).", "r": "Tensione trasformativa: legami profondi e fiducia in fase critica o non integrata."},
    9: {"d": "Visione, senso, studio, fede (mappa del mondo).", "r": "Tensione su visione e senso: fede/teoria in revisione, orientamento incerto."},
    10: {"d": "Ruolo, vocazione, direzione pubblica (responsabilità).", "r": "Tensione sul ruolo: direzione pubblica instabile, ambivalenza rispetto alla responsabilità."},
    11: {"d": "Rete, collettivo, futuro (alleanze e progetto).", "r": "Tensione nel collettivo: rete/progetto con attriti o appartenenza non stabile."},
    12: {"d": "Inconscio, ritiro, chiusure e dissoluzione (ciò che lavora sotto).", "r": "Tensione nell’inconscio: chiusure, ritiro o dissoluzione che interferiscono col visibile."},
}


ARCANA_PHRASES: Dict[str, Dict[str, str]] = {
    "I": {
        "d": "Attivazione: iniziativa mentale, avvio, messa in moto.",
        "r": "Attivazione discontinua: avvio impulsivo, dispersione, strumenti non allineati."
    },
    "II": {
        "d": "Ricettività: ascolto, custodia, sapere interno.",
        "r": "Ricettività bloccata: segreto, passività, chiusura o controllo interno eccessivo."
    },
    "III": {
        "d": "Generazione: crescita, fecondità, produzione di forme.",
        "r": "Generazione distorta: accumulo, dipendenza dal nutrimento, produttività caotica o sterile."
    },
    "IV": {
        "d": "Struttura: confini, ordine, governo, responsabilità.",
        "r": "Struttura instabile: confini rigidi o porosi, controllo reattivo, autorità che fatica."
    },
    "V": {
        "d": "Norma: senso, regola, trasmissione, legittimazione.",
        "r": "Norma vuota: dogma o colpa, delega, mancanza di senso pratico e coerenza."
    },
    "VI": {
        "d": "Scelta/legame: integrazione di polarità, patto, desiderio.",
        "r": "Scelta spezzata: ambivalenza, legami incongrui, polarità non integrate."
    },
    "VII": {
        "d": "Direzione: avanzamento, conquista, vettore, disciplina.",
        "r": "Direzione forzata: accelerazione, conflitto, controllo del vettore, perdita di centratura."
    },
    "VIII": {
        "d": "Equilibrio: misura, reciprocità, decisione giusta.",
        "r": "Equilibrio punitivo: giudizio, legalismo, indecisione, bilancia bloccata."
    },
    "IX": {
        "d": "Ritiro/ricerca: essenzialità, profondità, discernimento.",
        "r": "Ritiro sterile: isolamento difensivo, chiusura, paura di esporsi, rallentamento."
    },
    "X": {
        "d": "Ciclo: svolta, contingenza, variazione, opportunità.",
        "r": "Ciclo deviato: ripetizione, fatalismo, instabilità non integrata."
    },
    "XI": {
        "d": "Potenza: energia domata, coraggio, tenuta.",
        "r": "Energia non domata: reattività, eccesso/deficit, aggressività o cedimento."
    },
    "XII": {
        "d": "Sospensione: inversione, attesa, sacrificio funzionale.",
        "r": "Sospensione stagnante: paralisi, sacrificio inutile, vittimismo, rinvio."
    },
    "XIII": {
        "d": "Taglio: fine/inizio, muta, passaggio, ristrutturazione profonda.",
        "r": "Taglio rifiutato: attaccamento, paura del cambiamento, transizione lunga e faticosa."
    },
    "XIV": {
        "d": "Integrazione: misura, flusso, composizione.",
        "r": "Misura persa: dispersione, oscillazione, mediazione che non unisce."
    },
    "XV": {
        "d": "Intensità: vincolo, attaccamento, potere desiderante.",
        "r": "Vincolo dominante: compulsione, dipendenza, potere che consuma o trattiene."
    },
    "XVI": {
        "d": "Rottura: shock, verità che cade, reset.",
        "r": "Crepa trattenuta: rottura differita, tensione che non scarica, crollo evitato."
    },
    "XVII": {
        "d": "Fiducia: orientamento, speranza, ispirazione.",
        "r": "Fiducia astratta: idealizzazione, fuga, promessa non incarnata."
    },
    "XVIII": {
        "d": "Inconscio: soglia, immagini, ambivalenza, notte.",
        "r": "Nebbia: confusione, proiezione, ansia, autoinganno."
    },
    "XIX": {
        "d": "Chiarezza: vitalità, riconoscimento, calore.",
        "r": "Luce opaca: ego ferito, bisogno di riconoscimento, calore intermittente."
    },
    "XX": {
        "d": "Chiamata: risveglio, verifica, resa dei conti, decisione.",
        "r": "Chiamata respinta: rimando, giudizio esterno, paura di decidere."
    },
    "XXI": {
        "d": "Compimento: totalità, integrazione, chiusura del ciclo.",
        "r": "Compimento incompleto: chiusura mancata, dispersione, confini porosi."
    },
    "XXII": {
        "d": "Apertura: libertà, rischio, passo nel vuoto, inizio.",
        "r": "Libertà disorganizzata: fuga, discontinuità, irresponsabilità, passo senza radice."
    }
}

def _phrase_for_arc(arc: str, orient: str) -> str:
    d = ARCANA_PHRASES.get(arc, {})
    if not d:
        return ""
    if orient == "r":
        return d.get("r", "")
    return d.get("d", "")


def _phrase_for_house(house: int, orient: str) -> str:
    d = HOUSE_PHRASES_DR.get(house, {})
    if not d:
        return ""
    if orient == "r":
        return d.get("r", "")
    return d.get("d", "")


def _dominant_body(members_norm: List[str]) -> str | None:
    best = None
    best_w = -1
    for pl in TIE_ORDER:
        if pl in members_norm:
            w = WEIGHTS.get(pl, 0)
            if w > best_w:
                best = pl
                best_w = w
    return best

def _compute_ch_v2(members_norm: List[str], orient_aspects: List[AspectTuple]) -> int:
    """Local house conflict+gravity index C_h v2 (deterministic).

    Conflitto:
      - opposition <=3°: +3
      - square <=3°: +2
      - conjunction <=1°: +1
    Concentrazione:
      - stellium (>=3 bodies in house): +2
    Gravità:
      - Saturn in house: +2
      - Pluto in house: +2
      - Uranus in house: +1
      - Neptune in house: +1

    Only counts aspects that involve at least one body in this house.
    """
    ch = 0
    # concentration
    if len(members_norm) >= 3:
        ch += 2
    # gravity
    if "Saturn" in members_norm:
        ch += 2
    if "Pluto" in members_norm:
        ch += 2
    if "Uranus" in members_norm:
        ch += 1
    if "Neptune" in members_norm:
        ch += 1

    # conflict
    for p1, p2, typ, orb in orient_aspects:
        a = norm_body(p1)
        b = norm_body(p2)
        if a not in members_norm and b not in members_norm:
            continue
        if typ == "opposition" and orb <= 3:
            ch += 3
        elif typ == "square" and orb <= 3:
            ch += 2
        elif typ == "conjunction" and orb <= 1:
            ch += 1
    return int(ch)


def _family_score(
    house: int,
    members_raw: List[str],
    orient_aspects: List[AspectTuple],
    protocol: str,
) -> Tuple[str, int, int, Dict[str,int], Dict[str,int]]:
    """Return (winner_family, score_family, total_tense, tension_count, tension_weight).

    protocol:
      - "A": default (frozen V5.6/V6)
      - "B": lighter (reduced hard amplification + adds tight harmony)
    """
    members = [norm_body(m) for m in members_raw]

    fam_score: Dict[str,int] = defaultdict(int)
    tension_count: Dict[str,int] = defaultdict(int)
    tension_weight: Dict[str,int] = defaultdict(int)

    # base
    for m in members:
        if m in FAMILIES:
            fam_score[FAMILIES[m]] += WEIGHTS[m]

    total_tense = 0

    # aspects: only count if involves at least one body in this house
    for p1, p2, typ, orb in orient_aspects:
        p1n, p2n = norm_body(p1), norm_body(p2)
        involves_member = (p1n in members) or (p2n in members)
        if typ in ("square","opposition") and orb <= 3 and involves_member:
            total_tense += 1

        for p in (p1n, p2n):
            if p in members and p in FAMILIES:
                fam = FAMILIES[p]
                w = WEIGHTS[p]
                # tight bonus
                if orb <= 2:
                    fam_score[fam] += w
                # tense tracking; bonus only if orb>2 to avoid double-count
                if typ in ("square","opposition") and orb <= 3:
                    tension_count[fam] += 1
                    tension_weight[fam] += w
                    if orb > 2 and protocol == "A":
                        fam_score[fam] += w

                # harmony (protocol B only): reward tight trines/sextiles
                if protocol == "B" and involves_member and orb <= 2:
                    if typ == "trine":
                        fam_score[fam] += 1
                    elif typ == "sextile":
                        fam_score[fam] += 1

    # house compatibility
    for fam, coef in HOUSE_COMPAT.get(house, {}).items():
        fam_score[fam] += coef

    if not fam_score:
        return ("KARMICA", 0, total_tense, dict(tension_count), dict(tension_weight))

    max_score = max(fam_score.values())
    winners = [f for f,v in fam_score.items() if v == max_score]
    if len(winners) == 1:
        winner = winners[0]
    else:
        winner = None
        for pl in TIE_ORDER:
            if pl in members and FAMILIES.get(pl) in winners:
                winner = FAMILIES[pl]
                break
        if winner is None:
            winner = sorted(winners)[0]
    return (winner, int(max_score), total_tense, dict(tension_count), dict(tension_weight))

def _has_conjunction_le1(members_norm: List[str], orient_aspects: List[AspectTuple]) -> bool:
    for p1,p2,typ,orb in orient_aspects:
        if typ == "conjunction" and orb <= 1:
            if norm_body(p1) in members_norm or norm_body(p2) in members_norm:
                return True
    return False

_ROMAN = {
    "I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8,"IX":9,"X":10,
    "XI":11,"XII":12,"XIII":13,"XIV":14,"XV":15,"XVI":16,"XVII":17,"XVIII":18,"XIX":19,"XX":20,"XXI":21,"XXII":22
}
def _arc_num(a: str) -> int:
    return _ROMAN.get(a, 99)

def _rank_cluster(
    house: int,
    family: str,
    score_family: int,
    members_norm: List[str],
    orient_aspects: List[AspectTuple],
    total_tense: int,
    signs: Dict[str, str],
    protocol: str,
) -> List[Tuple[str,int]]:
    cluster = CLUSTERS[family]
    conj = _has_conjunction_le1(members_norm, orient_aspects)
    dom = _dominant_body(members_norm)

    dominant_sign = signs.get(dom) if dom is not None else None

    ranked: List[Tuple[str,int]] = []
    for arc in cluster:
        s = score_family
        s += ARC_BASE_OFFSET.get(arc, 0)

        if total_tense >= 2 and arc in BONUS_TENSIONE:
            s += (2 if protocol == "A" else 1)
        if conj and arc in BONUS_CONGIUNZIONE:
            s += 2

        s += BONUS_CASA.get(house, {}).get(arc, 0)

        if dom is not None:
            s += BONUS_DOM.get(dom, {}).get(arc, 0)

        
        # --- V5.1 Pluto refinement (cumulative bonuses) ---
        if family == "TRASFORMAZIONE":
            has_venus = "Venus" in members_norm
            has_mars = "Mars" in members_norm
            has_saturn = "Saturn" in members_norm
            has_uranus = "Uranus" in members_norm
            has_node = "North Node" in members_norm

            if (has_venus or has_mars) and arc == "XV":
                s += 2
            if has_saturn and arc == "XIII":
                s += 2
            if has_uranus and arc == "XVI":
                s += 2
            if has_node and arc == "XX":
                s += 2

        # --- V5.2 Zodiacal refinement (dominant planet only; element-based) ---
        if dominant_sign:
            FIRE = {"Aries","Leo","Sagittarius"}
            EARTH = {"Taurus","Virgo","Capricorn"}
            AIR = {"Gemini","Libra","Aquarius"}
            WATER = {"Cancer","Scorpio","Pisces"}

            if family == "EMOZIONE" and dom == "Moon":
                if dominant_sign in WATER and arc == "XVIII":
                    s += 2
                elif dominant_sign in AIR and arc == "II":
                    s += 2
                elif dominant_sign in FIRE and arc == "XIV":
                    s += 2
                elif dominant_sign in EARTH and arc == "II":
                    s += 2

            if family == "TRASFORMAZIONE" and dom == "Pluto":
                if dominant_sign in WATER and arc == "XIII":
                    s += 1
                elif dominant_sign in FIRE and arc == "XVI":
                    s += 1
                elif dominant_sign in AIR and arc == "XX":
                    s += 1
                elif dominant_sign in EARTH and arc == "XIII":
                    s += 1

            if family == "DESIDERIO" and dom in ("Venus","Mars"):
                if dominant_sign in FIRE and arc == "III":
                    s += 2
                elif dominant_sign in AIR and arc == "VI":
                    s += 2
                elif dominant_sign in EARTH and arc == "III":
                    s += 2
                elif dominant_sign in WATER and arc == "XV":
                    s += 2

            if family == "IDENTITA" and dom == "Sun":
                if dominant_sign in FIRE and arc == "XIX":
                    s += 2
                elif dominant_sign in EARTH and arc == "IV":
                    s += 2
                elif dominant_sign in AIR and arc == "VI":
                    s += 2
                elif dominant_sign in WATER and arc == "III":
                    s += 2

        ranked.append((arc, int(s)))

    ranked.sort(key=lambda x: (-x[1], _arc_num(x[0])))
    return ranked

def _orientation(total_tense: int, family: str, tension_count: Dict[str,int], tension_weight: Dict[str,int], score_family: int) -> str:
    tense_fam = tension_count.get(family, 0)
    tw = tension_weight.get(family, 0)
    if total_tense >= 2 or tense_fam >= 2 or (score_family > 0 and tw >= 0.4 * score_family):
        return "r"
    return "d"

def compute(path: str) -> List[Dict[str, Any]]:
    """
    V6.4: deterministic, audit-friendly (+phrases).

    - Keeps V6.1 anti-dup resolution.
    - Adds **local hybrid protocol** per house (A/B) driven by C_h v2:
        C_h v2 = conflict(opposition/square/conjunction) + concentration(stellium) + gravity(Saturn/Pluto/Uranus/Neptune)
        If C_h >= 7 -> Protocol A
        Else        -> Protocol B
      Protocol B reduces hard amplification and adds tight harmony (trine/sextile) bonuses.

    Change vs V5.6:
    - When the same Arcano is ranked #1 in multiple selected houses, we do NOT assign
      by house-order greedily.
    - We assign that Arcano to the house where it is most "decisive":
        decisivity = score(#1) - score(#2)
      Tie-breaks: higher score(#1), then lower house number.
    - All other behavior (scoring, clusters, orientation, etc.) remains unchanged.
    """
    base_rows = compute_v3_3(path)
    base_rows = sorted(base_rows, key=lambda r: r["house"])
    signs = load_signs_from_json(path)

    # --- First pass: compute rankings per house (no arc assigned yet) ---
    rows_info: List[Dict[str, Any]] = []
    for r in base_rows:
        house = int(r["house"])
        members_raw = r.get("members", [])
        orient_aspects = r.get("orient_aspects", [])
        members_norm = [norm_body(m) for m in members_raw]

        ch = _compute_ch_v2(members_norm, orient_aspects)
        protocol = "A" if ch >= 7 else "B"

        fam, fam_score, total_tense, tension_count, tension_weight = _family_score(house, members_raw, orient_aspects, protocol)
        ranked = _rank_cluster(house, fam, fam_score, members_norm, orient_aspects, total_tense, signs, protocol)

        top1_arc, top1_score = ranked[0]
        top2_score = ranked[1][1] if len(ranked) > 1 else (top1_score - 9999)
        decisivity = int(top1_score) - int(top2_score)

        rows_info.append({
            "row": r,
            "house": house,
            "members_raw": members_raw,
            "members_norm": members_norm,
            "orient_aspects": orient_aspects,
            "fam": fam,
            "fam_score": fam_score,
            "total_tense": total_tense,
            "tension_count": tension_count,
            "tension_weight": tension_weight,
            "ch": int(ch),
            "protocol": protocol,
            "ranked": ranked,
            "top1_arc": top1_arc,
            "top1_score": int(top1_score),
            "decisivity": int(decisivity),
        })

    # --- Resolve #1 duplicates deterministically (only for arc that is #1 in >=2 houses) ---
    top1_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for info in rows_info:
        top1_map[info["top1_arc"]].append(info)

    forced_arc_by_house: Dict[int, str] = {}
    forced_audit: Dict[int, Dict[str, Any]] = {}

    for arc, infos in top1_map.items():
        if len(infos) < 2:
            continue
        # pick winner by decisivity desc, then top1_score desc, then house asc
        infos_sorted = sorted(
            infos,
            key=lambda x: (-x["decisivity"], -x["top1_score"], x["house"])
        )
        winner = infos_sorted[0]
        forced_arc_by_house[winner["house"]] = arc
        forced_audit[winner["house"]] = {
            "forced_arc": arc,
            "reason": "top1_duplicate_winner",
            "decisivity": winner["decisivity"],
            "top1_score": winner["top1_score"],
            "contenders": [
                {"house": i["house"], "decisivity": i["decisivity"], "top1_score": i["top1_score"]}
                for i in infos_sorted
            ],
        }

    # --- Assignment pass ---
    assigned: Set[str] = set()
    house_to_choice: Dict[int, Dict[str, Any]] = {}

    # 1) assign forced first (stable order)
    for house in sorted(forced_arc_by_house.keys()):
        arc = forced_arc_by_house[house]
        info = next(i for i in rows_info if i["house"] == house)
        ranked = info["ranked"]
        # arc must be in ranked[0] by construction
        chosen_arc = arc
        chosen_score = next(sc for a, sc in ranked if a == chosen_arc)
        assigned.add(chosen_arc)
        house_to_choice[house] = {"arc": chosen_arc, "score": int(chosen_score), "audit": forced_audit.get(house)}

    # 2) assign remaining houses by best available
    for info in rows_info:
        house = info["house"]
        if house in house_to_choice:
            continue
        ranked = info["ranked"]
        chosen_arc = None
        chosen_score = None
        for arc, sc in ranked:
            if arc not in assigned:
                chosen_arc, chosen_score = arc, sc
                break
        if chosen_arc is None:
            chosen_arc, chosen_score = ranked[0]
        assigned.add(chosen_arc)
        house_to_choice[house] = {"arc": chosen_arc, "score": int(chosen_score), "audit": None}

    # --- Final pass: compute orientation and output ---
    out: List[Dict[str, Any]] = []

    for info in rows_info:
        r = info["row"]
        house = info["house"]
        members_norm = info["members_norm"]
        orient_aspects = info["orient_aspects"]

        chosen_arc = house_to_choice[house]["arc"]
        chosen_score = house_to_choice[house]["score"]
        audit = house_to_choice[house]["audit"]

        # --- V5.4 Orientation refinement: weighted dominant hard aspects ---
        dom_for_orient = _dominant_body(members_norm)
        dom_hard_count = 0
        dom_hard_weight = 0.0

        HARD_WEIGHTS = {
            "Saturn": 1.2,
            "Pluto": 1.1,
            "Uranus": 1.1,
            "Neptune": 1.0,
            "Jupiter": 0.8,
            "Mars": 0.9,
            "Venus": 0.9,
            "Mercury": 0.9,
            "Moon": 0.9,
            "Sun": 0.9,
            "North Node": 1.0,
            "Lilith": 1.0,
            "Chiron": 1.0,
        }

        if dom_for_orient is not None:
            for p1, p2, typ, orb in orient_aspects:
                orb_limit = 3
                if dom_for_orient == "Sun":
                    orb_limit = 6.5
                if typ in ("square", "opposition") and orb <= orb_limit:
                    weight_aspect = 1.2 if typ == "opposition" else 1.0
                    a = norm_body(p1)
                    b = norm_body(p2)
                    if a == dom_for_orient or b == dom_for_orient:
                        other = b if a == dom_for_orient else a
                        dom_hard_count += 1
                        dom_hard_weight += weight_aspect * HARD_WEIGHTS.get(other, 0.9)

        if dom_hard_count >= 2 and dom_hard_weight >= 1.8:
            orient = "r"
        else:
            orient = _orientation(info["total_tense"], info["fam"], info["tension_count"], info["tension_weight"], info["fam_score"])

        row_out = {**r, "arc": chosen_arc, "orient": orient, "score": int(chosen_score)}
        # helper phrases
        row_out["house_phrase"] = _phrase_for_house(house, orient)
        row_out["arc_phrase"] = _phrase_for_arc(chosen_arc, orient)
        if row_out["house_phrase"] or row_out["arc_phrase"]:
            row_out["text"] = f'Casa {house} — {ARCANA_NAMES.get(chosen_arc, chosen_arc)} ({orient}) — {row_out["house_phrase"]} per mezzo di {row_out["arc_phrase"]}'
        # audit (always present, lightweight)
        row_out["audit_house"] = {"ch": int(info["ch"]), "protocol": info["protocol"]}
        if audit is not None:
            row_out["audit_conflict"] = audit
        out.append(row_out)

    out = sorted(out, key=lambda r: (-r["score"], r["house"]))
    return out

