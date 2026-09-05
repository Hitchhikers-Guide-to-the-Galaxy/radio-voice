# Radio Voice

The code behind the Constitution Commons and the Radio Voice Plan: the world's
constitutions pulled from the Constitute Project, milled into fragments that can
be cited, spoken on the radio and compared clause by clause, and published as
federated wiki pages.

- **mill/** — the Constitute pull (`pull.py`), the Fragment Mill (`parse.py`,
  `score.py`, `shortlist.py`), and `globe.py`, which builds the data behind the
  [Constitution Globe](https://constitution.legalcommons.org/view/constitution-globe).
- **commons/** — page generators for
  [constitution.legalcommons.org](https://constitution.legalcommons.org) and
  clause.legalcommons.org; `gen_constitution.py` writes one page per text with
  the original download, plain text and fragments as page assets.
- **hear/** — the Hear Crowds street builder and its media schema.
- **uk/** — an importer for UK instruments from legislation.gov.uk.
- **bin/voice** — one command for every speech engine on the station, with the
  palette in `voices.json`.

The scripts import `fedwiki.py` from the fedwiki-lib skill and expect the
sites under `~/Nextcloud/fedwiki/`. Audio, models, raw pulls and generated
corpora are not in the repository.

Texts come from the [Constitute Project](https://www.constituteproject.org/)
under CC BY-NC 3.0; everything here is non-commercial.
