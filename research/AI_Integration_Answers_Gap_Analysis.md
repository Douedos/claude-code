# Gap Analysis — Claude Answers vs. ChatGPT Expected Answers

Comparison of `AI_Integration_Clarification_Answers.md` (Claude) against the
"Clarification Questions — Expected Answers" document (ChatGPT), question by question.
Each divergence is classified as: **true miss** (Claude should have said it),
**document ambiguity** (the skeleton underdetermines the answer; both readings defensible),
**deliberate deviation** (a tagged [PROPOSED CHANGE], not a miss), or
**push-back** (Claude's answer is more faithful to the skeleton than the expected one).

## Headline agreement

~33 of 39 questions are substantively aligned, frequently down to the same named
techniques (latent-factor provider reconciliation in C3, permutations preserving
country time paths in H1/F4, Oct-2024 WEO baseline in E5, "nulls are first-class"
with power context in K2). The convergence is expected: both sets of answers were
derived from the same skeleton, and the skeleton is prescriptive.

## Divergences

### B1 — Canonical unit (document ambiguity; the most important divergence)
- Claude: primary inference on country×sector×**year** (annual productivity), monthly output as fast intermediate.
- Expected: primary panel country×sector×**month**, annual productivity as "slower validation layer".
- The skeleton supports both readings: §8 names the canonical *table* as country×month×sector, while Axis B ranks annual per-hour productivity "closest to the mechanism" and H7 (priority 1) is a productivity — i.e. annual — hypothesis.
- Evidence that this is the document's incoherence rather than either side's miss: the expected answers themselves diverge internally — expected **B1** makes the monthly panel primary, while expected **E1** makes "real labor productivity per hour" (annual) the primary outcome. Both answer sets independently tripped over the same seam.
- **Resolution needed at sign-off:** distinguish the canonical *storage* unit (monthly, per §8) from the primary *inference* unit (annual productivity, per Axis B/H7). Suggested wording: "canonical table monthly; primary inferential outcome annual EPS; monthly output panel is the fast intermediate."

### B3 — China / restricted markets (partial true miss, Claude)
- Claude: exclude from telemetry-based inference, versioned exclusion list.
- Expected: analyze separately or with domestic-model proxies; never read low Claude/OpenAI usage as low total AI use.
- The skeleton is silent on China. Claude's exclusion is the conservative subset of the expected answer, but the domestic-proxy *option* was not considered — that omission is a genuine gap in coverage. Counter-consideration: domestic-model proxies introduce sources absent from the S01–S17 registry, in tension with I1's first-party rule, so the proxy track requires new registered sources before it is admissible.

### C4 — Breadth definition (minor true miss, Claude)
- Skeleton Axis A puts **messages/person under breadth**; Claude placed messages-per-user under depth. Expected matches the skeleton's literal assignment. Small imprecision, no downstream consequence, but the expected answer is the more faithful transcription.

### C5 — Lag grid (document ambiguity)
- Claude: {0, 6, 12, 24} months / {0, 1, 2} years. Expected: {0, 3, 6, 12, 18} months.
- The skeleton never specifies lags ("several months or years"). Both grids are invented; the disagreement is evidence the choice is undetermined and must be fixed by decision, not by either document. Both sides agree on the part that matters: the family is closed in advance, logged, and corrected for; leads run only as placebos.

### E4 — Negative-control roster (document ambiguity, minor)
- Claude: accommodation/food, transport, construction, mining/utilities. Expected: accommodation/food as strong controls; transport and real estate only secondary, "not perfectly unexposed".
- The skeleton names no control sectors. The expected answer's calibration (transport is partially exposed via logistics optimization) is a fair nuance. Claude's rule — take both tails from one pre-specified published exposure index — would settle the roster empirically and is the stronger governance answer; adopting the expected answer's exposed/secondary/control **tiering** on top of it combines both.

### F2 — Fixed effects (deliberate deviation, Claude)
- Claude [PROPOSED CHANGE]: country×time + sector×time FE (Rajan–Zingales identification), wild-cluster bootstrap.
- Expected: country FE + month FE, richer interactions "where data volume supports them" — the skeleton's literal baseline.
- Not a miss on either side: Claude's is a flagged upgrade beyond the skeleton; the expected answer's data-volume caution is legitimate and the saturated spec should be primary with the baseline as sensitivity, not the reverse.

### I1 — Admissible core sources (push-back, Claude more faithful)
- Expected adds "World Bank/OECD when needed" to the core list. The skeleton classes S15 (World Bank) as SUPPORTING, and OECD appears nowhere in the S01–S17 registry. Loosening core admissibility in the answer sheet is exactly the silent-drift the checklist exists to prevent; any new core source should enter via a registered fingerprint, not a parenthetical.

### J2 — Holdout (partial true miss, Claude)
- Claude: future 2027–2028 releases only; "no re-splitting of historical data is ever labeled confirmation."
- Expected: prefer future releases; **fallback** — reserve a final contiguous historical period never inspected during exploration.
- The skeleton criticizes "repeatedly re-splitting historical data" and confirmation "on the same observations"; a never-inspected terminal block violates neither. Claude collapsed "no re-splitting" into "no historical holdout at all" — an overstatement. The fallback is skeleton-compatible and worth having if 2027 data is delayed. (Caveat retained: with adoption data starting ~2023, any reserved historical block is short and weak — the prospective holdout remains the real test.)

## Where Claude's answers add beyond the expected set (deliberate, tagged)

MDE/power gate on promotion and abandonment (H4/K3 — the expected K2/K3 gesture at
"power/precision" and "sufficient precision", so the direction is shared; Claude
operationalizes it as a blocking gate); generated-regressor inference for AIS
(one-step FWL variant + full-pipeline bootstrap, D5); published occupational-exposure
indices instead of a bespoke cognitive-exposure score (E3); promotion of multi-provider
reconciliation from robustness layer to core AIS construction (C2); external timestamped
registration of the confirmatory freeze (J1). The expected answers include none of these
as requirements; all five stand as proposals for sign-off.

## Verdict

- **True misses (Claude):** B3 (domestic-proxy option not considered), J2 (overstated ban on historical holdout), C4 (minor breadth/depth misassignment).
- **Document ambiguities surfaced by disagreement:** B1/E1 (storage unit vs. inference unit — also internally inconsistent within the expected answers), C5 (lag grid), E4 (control roster). These need explicit versioned decisions; neither answer set can settle them alone.
- **Push-backs on the expected answers:** I1 source loosening; B1 monthly-primary framing contradicting the skeleton's mechanism-proximity ranking and the expected set's own E1.
- **Deliberate deviations, not misses:** F2 FE upgrade plus the five additions above.
