AA_STRUCTURAL_READING_PIPELINE_V6_4_2_FULL_FIXED_PHRASES_DR_HOUSE

Scope
- Deterministic, auditabile, autosufficiente.
- Input: JSON_CU3 (txt/json) come nei batch forniti.
- Output: lista di righe (una per casa selezionata) con arcano, orientamento, score.

Core
- Selezione case: invariata (motore V3.3).
- Scoring/cluster/anti-duplicazione: V5/V6 con risoluzione deterministica dei duplicati #1 (V6.1).

Novità V6.3 (IBRIDO LOCALE PER CASA)
- Per ogni casa h si calcola un indice locale C_h v2 (conflitto + gravità):
  Conflitto:
    • opposition <=3°: +3
    • square <=3°: +2
    • conjunction <=1°: +1
  Concentrazione:
    • stellium (>=3 corpi in casa): +2
  Gravità:
    • Saturn in casa: +2
    • Pluto in casa: +2
    • Uranus in casa: +1
    • Neptune in casa: +1
  (Si contano solo aspetti che coinvolgono almeno un corpo della casa.)

- Protocollo per casa:
    • Se C_h >= 7  -> Protocollo A (standard)
    • Se C_h <  7  -> Protocollo B (alleggerito)

- Protocollo B:
    • riduce l'amplificazione degli hard "larghi" (orb >2°) sullo scoring di famiglia
    • aggiunge bonus deterministici per armonici stretti (trine/sextile <=2°)
    • riduce il bonus "tensione" nel ranking cluster (BONUS_TENSIONE: +1 invece di +2)

Audit
- Ogni riga include:
    audit_house = { "ch": <int>, "protocol": "A"|"B" }
- Se scatta la risoluzione duplicati top1, la riga include:
    audit_conflict = { ... }


V6.4 NOTE
- Adds deterministic helper phrases in output fields: house_phrase, arc_phrase, text.
- Does not change scoring, selection, orientation, or audit logic.


Output (V6.4.2)
- Ordinamento: intensità decrescente (score DESC), tie-break per house ASC.
- Per ogni riga: Casa - Carta - frase casa + frase carta.
- Fusione frasi: "<frase casa> per mezzo di <frase carta>".
- Frasi separate per dritto/rovescio sia per Casa che per Arcano.
