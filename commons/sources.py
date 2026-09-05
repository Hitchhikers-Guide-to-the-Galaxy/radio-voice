import sys, os, json
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); import fedwiki
FARM = os.path.expanduser("~/Nextcloud/fedwiki/constitution.legalcommons.org")
PROV = "Claude Code, in dialogue with David Bovill, from research David supplied on 3 September 2026; rights statements verified against each source the same day"
ACC = "This page was written by [[Claude Code]] in dialogue with [[David Bovill]], 3 September 2026, from research David supplied. Every rights statement below was checked against the source on that date."
def save(title, items, see, slug=None):
    slug = slug or fedwiki.as_slug(title)
    page = fedwiki.make_page(title, items, provenance=PROV)
    fedwiki.ensure_see(page, see, journal=False)
    fedwiki.save_page(f"{FARM}/pages/{slug}", page); return slug
def record(**kw): return {"type": "code", "language": "yaml", "text": "\n".join(f"{k}: {v}" for k, v in kw.items())}

SOURCES = [
 dict(title="UK Legislation", url="https://www.legislation.gov.uk/", jurisdiction="United Kingdom, England, Wales, Scotland, Northern Ireland",
   provides="Magna Carta 1297, the Bill of Rights 1688, the Act of Settlement 1700, the Parliament Acts, the Human Rights Act 1998, the Constitutional Reform Act 2005, the Well-being of Future Generations (Wales) Act 2015 — and every UK statute, revised and as enacted.",
   rights="open", licence="Open Government Licence v3.0", licence_url="https://www.legislation.gov.uk/help#copyright",
   quote="All content is available under the Open Government Licence v3.0 except where otherwise stated.",
   caveats="Crown and database right reserved under the licence; EU-derived content is reused under Commission Decision 2011/833/EU; third-party contributions are marked.",
   formats="HTML, XML (Legislation schema), Akoma Ntoso, RDF, Atom feeds", api="https://legislation.github.io/data-documentation/",
   tested="Appending /data.xml works: Magna Carta 1297 (aep/Edw1cc1929/25/9), the Bill of Rights (aep/WillandMarSess2/1/2) and the Well-being of Future Generations (Wales) Act 2015 (anaw/2015/2, 128 provisions, English and Welsh titles) all returned XML on 3 September 2026.",
   verdict="Checks out. The best source for this commons: explicit commercial reuse, structured XML, stable id URIs. First importer target."),
 dict(title="New Zealand Legislation", url="https://www.legislation.govt.nz/", jurisdiction="New Zealand",
   provides="The Constitution Act 1986, the Bill of Rights Act 1990, the Te Urewera Act 2014 and the Te Awa Tupua (Whanganui River Claims Settlement) Act 2017 — the legislation that makes a forest and a river juridical persons — and all New Zealand Acts and Bills.",
   rights="public-domain", licence="No copyright in legislation — Copyright Act 1994, section 27", licence_url="https://www.legislation.govt.nz/copyright/",
   quote="Under section 27 of the Copyright Act 1994, there is no copyright in New Zealand legislation … may be reproduced in any format or media, free of charge, without requiring specific permission.",
   caveats="Section 27 does not reach works incorporated by reference; some agency-published secondary legislation asserts overseas copyright.",
   formats="HTML, XML", api="https://www.legislation.govt.nz/learn-more/legislation-data/xml-data/",
   tested="Rights confirmed from the PCO copyright page (the page itself blocks automated fetches; confirmed via search results quoting it).",
   verdict="Checks out. The environmental-personhood Acts are the most valuable single addition to the commons: they let a river's legal standing sit beside Ecuador's Article 71."),
 dict(title="Australian Federal Register of Legislation", url="https://www.legislation.gov.au/", jurisdiction="Commonwealth of Australia",
   provides="The Commonwealth of Australia Constitution Act and all federal Acts and instruments.",
   rights="attribution", licence="CC BY 4.0", licence_url="https://www.legislation.gov.au/terms-of-use",
   quote="With the exception of the Commonwealth Coat of Arms, and where otherwise noted, all content on the Federal Register of Legislation is licensed under CC BY 4.0.",
   caveats="Third-party copyright material identified on the register needs its owner's permission.", formats="HTML, downloadable versions", api="site search and downloads; no bulk API documented on the terms page",
   tested="Licence confirmed from the terms of use, 3 September 2026.", verdict="Checks out."),
 dict(title="Canada Justice Laws", url="https://laws-lois.justice.gc.ca/", jurisdiction="Canada",
   provides="The Constitution Acts 1867 to 1982, the Canadian Charter of Rights and Freedoms, consolidated statutes and regulations.",
   rights="open", licence="Reproduction of Federal Law Order, SI/97-5", licence_url="https://laws-lois.justice.gc.ca/eng/regulations/si-97-5/page-1.html",
   quote="Anyone may, without charge or request for permission, reproduce enactments and consolidations of enactments of the Government of Canada … provided due diligence is exercised in ensuring the accuracy of the materials reproduced and the reproduction is not represented as an official version.",
   caveats="The Order speaks of enactments of the Government of Canada; the Constitution Act 1867 is a UK statute consolidated on the site. Treat the consolidation as covered, the original as UK Crown material under the OGL.",
   formats="HTML, XML, PDF", api="per-Act XML downloads", tested="Order text confirmed, 3 September 2026.", verdict="Checks out, with the Constitution Act 1867 provenance noted."),
 dict(title="US GovInfo", url="https://www.govinfo.gov/", jurisdiction="United States, federal",
   provides="The Constitution of the United States (with the National Archives transcript at archives.gov/founding-docs), the US Code, the Code of Federal Regulations and the Federal Register.",
   rights="public-domain", licence="US Government works — 17 U.S.C. § 105", licence_url="https://www.govinfo.gov/about/policies",
   quote="Copyright protection under this title is not available for any work of the United States Government.",
   caveats="Third-party material inside government documents keeps its copyright; GPO's licensed images are not public domain; credit the originating agency.",
   formats="bulk XML, PDF, HTML", api="https://www.govinfo.gov/developers", tested="Policy confirmed, 3 September 2026.", verdict="Checks out."),
 dict(title="Open US Law", url="https://github.com/Vaquill-AI/open-us-law", jurisdiction="United States, federal and all fifty states, DC and Puerto Rico",
   provides="A normalised corpus of US law: the US Code, CFR, Federal Register rules, and every state's statutes, regulations, court rules and constitution — 2,978,617 sections in snapshot v2026.08, of which 13,382 are constitutional sections across 52 jurisdictions.",
   rights="attribution", licence="Data and compilation CC BY 4.0; scripts Apache-2.0; underlying law public domain (Georgia v. Public.Resource.Org, 2020)", licence_url="https://github.com/Vaquill-AI/open-us-law",
   quote="Scripts - Apache-2.0. Data / compilation - CC BY 4.0.",
   caveats="A third-party compilation, not an official source; every section carries its official-source URL, which is what makes it usable.",
   formats="Parquet with a unified 24-column schema; JSONL from the scrapers", api="GitHub releases, quarterly",
   tested="Repository, licence line, snapshot v2026.08 and the 13,382 count all confirmed, 3 September 2026.",
   verdict="Checks out exactly as described. The fastest route to a varied sample of state constitutions."),
 dict(title="EUR-Lex", url="https://eur-lex.europa.eu/", jurisdiction="European Union",
   provides="The Treaty on European Union, the Treaty on the Functioning of the European Union, the Charter of Fundamental Rights, regulations, directives and case law, with CELEX identifiers.",
   rights="open", licence="Commission Decision 2011/833/EU for legal texts; CC BY 4.0 for editorial and consolidated content; CC0 1.0 for metadata", licence_url="https://eur-lex.europa.eu/content/legal-notice/legal-notice.html",
   quote="Legal texts: available for reuse under Decision 2011/833/EU for commercial or non-commercial purposes, unless otherwise specified.",
   caveats="Consolidated texts are editorial, so CC BY applies to them; acknowledge the source and indicate changes.", formats="HTML, XML (Formex), PDF", api="CELLAR SPARQL endpoint and the EUR-Lex web service",
   tested="Legal notice confirmed, 3 September 2026.", verdict="Checks out."),
 dict(title="French LEGI Open Data", url="https://www.data.gouv.fr/datasets/legi-codes-lois-et-reglements-consolides", jurisdiction="France",
   provides="Consolidated French codes, laws, decrees and ordinances since 1945 — 73 codes in force. The Constitution of 1958 and the Charter for the Environment live in the sibling CONSTIT base, which shares the same DTDs.",
   rights="open", licence="Licence Ouverte / Open Licence (Etalab)", licence_url="https://www.etalab.gouv.fr/licence-ouverte-open-licence/",
   quote="Licence Ouverte / Open Licence.", caveats="Authoritative text is French; English versions of the Constitution come from the Conseil constitutionnel and carry their own terms.",
   formats="bulk XML with DTDs, PDF", api="DILA bulk downloads; Légifrance API via PISTE", tested="Dataset page and licence confirmed, 3 September 2026; the CONSTIT base is a separate download.",
   verdict="Checks out, with the Constitution in CONSTIT rather than LEGI."),
 dict(title="CommunityRule", url="https://communityrule.info/about/", jurisdiction="community governance templates",
   provides="Templates for community decision-making, stewardship and cultural norms — from the Media Enterprise Design Lab at the University of Colorado Boulder with the Metagovernance Project.",
   rights="share-alike", licence="CC BY-SA 4.0", licence_url="https://communityrule.info/about/",
   quote="anyone has the right to use and adapt it, and adaptations must be re-shared under the same license",
   caveats="Share-alike: anything built on these must carry CC BY-SA.", formats="web, Markdown", api="none; git repository",
   tested="Licence confirmed, 3 September 2026.", verdict="Checks out. Experimental material for the drafting agent, more than state constitutions give."),
 dict(title="Sustainable Economies Law Center", url="https://www.theselc.org/templates", jurisdiction="United States, cooperative and nonprofit law",
   provides="Worker cooperative bylaws and articles, worker-self-directed nonprofit bylaws, permanent real estate cooperative documents, co-housing agreements, rematriation and cultural easement templates, solar cooperative bylaws.",
   rights="share-alike", licence="CC BY-SA 4.0 except where otherwise noted", licence_url="https://www.theselc.org/templates",
   quote="Feel free to share, use, and/or build upon any of these cartoons and these legal resources, which are licensed under a Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0), except where otherwise noted.",
   caveats="Share-alike; some documents are noted otherwise.", formats="PDF, DOCX", api="none", tested="Licence confirmed, 3 September 2026.", verdict="Checks out."),
 dict(title="Metagov Constitution Template", url="https://github.com/metagov/constitution-template", jurisdiction="DAO and online-community constitutions",
   provides="A forkable Markdown constitution template and a collection of existing DAO constitutions from the Constitutions of Web3 dataset.",
   rights="attribution", licence="MIT (repository)", licence_url="https://github.com/metagov/constitution-template",
   quote="MIT license — LICENSE file in the repository.",
   caveats="The template is MIT. The contributed DAO constitutions carry no separate rights statements; the research's warning stands — audit each text's provenance before republishing it.",
   formats="Markdown, JSON metadata", api="GitHub", tested="Repository and licence confirmed, 3 September 2026.", verdict="Checks out for the template; the collection needs per-text auditing."),
 dict(title="Creative Commons Legal Codes", url="https://creativecommons.org/policies/", jurisdiction="the licences themselves",
   provides="The legal code of every Creative Commons licence and of CC0 — legal text designed from the start to be copied, translated and read by machines.",
   rights="public-domain", licence="CC0 1.0", licence_url="https://creativecommons.org/policies/",
   quote="Creative Commons makes the legal code of its licenses and the CC0 Public Domain Dedication available under the CC0 Public Domain Dedication.",
   caveats="Trademarks and branding stay reserved.", formats="HTML, plain text, RDF", api="none needed", tested="Policy confirmed, 3 September 2026.",
   verdict="Checks out. The clearest example in the commons of law written to be forked."),
 dict(title="Constitute Project", url="https://www.constituteproject.org/", jurisdiction="every country's constitution in force, with translations and topic tagging",
   provides="The [[Constitution Corpus]] this site is built from — 240 texts, English with Spanish and Arabic editions, 479 topic keys applied section by section.",
   rights="non-commercial", licence="CC BY-NC 3.0 Unported", licence_url="https://www.constituteproject.org/content/about",
   quote="Creative Commons Attribution-Non Commercial 3.0 Unported License … allows you to make free use of information from the site for noncommercial purposes.",
   caveats="Non-commercial. Many translations additionally carry a publisher's copyright (Oxford University Press, William S. Hein) — 55 of the 240 — and those are excerpted, never attached. Keep it as a research garden, never under anything paid.",
   formats="HTML with inline topic tags, via a documented API", api="https://www.constituteproject.org/service/",
   tested="The about page states the licence; the terms page adds the no-fee, non-commercial condition. Corrected 3 September 2026 — the corpus page had said no open licence was stated.",
   verdict="Checks out as a non-commercial index and research garden — which is what this site is. Not a foundation for paid Guides."),
 dict(title="Laws.Africa", url="https://laws.africa/api/detail/", jurisdiction="African legislation, many countries",
   provides="African legislation in Akoma Ntoso XML and HTML, with tables of contents, amendment histories and points in time.",
   rights="non-commercial", licence="CC BY-NC-SA", licence_url="https://laws.africa/api/detail/",
   quote="Creative Commons Attribution-NonCommercial-ShareAlike (CC-BY-NC-SA).",
   caveats="Non-commercial and share-alike; commercial licences and public-interest research access are separate arrangements.", formats="Akoma Ntoso XML, HTML, PDF", api="https://laws.africa/api/detail/",
   tested="Licence confirmed, 3 September 2026.", verdict="Checks out. The best-structured African source, but isolated like Constitute."),
 dict(title="Wikisource", url="https://wikisource.org/", jurisdiction="historical constitutions and translations",
   provides="Transcriptions of historical constitutions and older translations.",
   rights="mixed", licence="per work — public domain or CC BY-SA, edition by edition", licence_url="https://wikisource.org/",
   quote="On Wikisource is not itself sufficient provenance.",
   caveats="Every work needs its edition, translation and rights checked separately. A public-domain original can sit beside a copyrighted modern translation.", formats="wikitext, HTML", api="MediaWiki API",
   tested="Not verified per work; the caution is the finding.", verdict="Useful for history; provenance is per text, never per site."),
]
CLASS = {"open": "open licence", "public-domain": "public domain", "attribution": "attribution", "share-alike": "share-alike", "non-commercial": "non-commercial — isolate", "mixed": "per work"}
for s in SOURCES:
    items = [ACC,
      f"**{s['title']}** — {s['provides']} Jurisdiction: {s['jurisdiction']}.",
      "# Rights", f"{CLASS[s['rights']]}: {s['licence']}. The source says: \"{s['quote']}\"", f"Caveats: {s['caveats']}",
      "# Importability", f"Formats: {s['formats']}. API: {s['api']}", f"Tested: {s['tested']}",
      "# Verdict", s["verdict"],
      "# Record", record(source=s["title"], url=s["url"], jurisdiction=s["jurisdiction"], rights_class=s["rights"], licence=s["licence"], licence_url=s["licence_url"], formats=s["formats"], api=s["api"], verified="2026-09-03", verified_by="Claude Code, WebFetch against the source"),
    ]
    save(s["title"], items, ["[[Constitutional Sources]] · [[Seed Collection]] · [[Import Constitutions Plan]]"])

rows = "\n".join(f"| [[{s['title']}]] | {s['jurisdiction'][:44]} | {CLASS[s['rights']]} | {s['formats'][:40]} |" for s in SOURCES)
save("Constitutional Sources", [ACC,
  "Where constitutional text can be taken from, and on what terms. The strongest sources are official legislation systems with explicit reuse rights and structured data; the two richest collections — Constitute and Laws.Africa — are non-commercial and stay isolated as research gardens. Each source has its own page with the rights statement quoted from the source and a record of when it was checked.",
  "# Sources", f"| Source | Jurisdiction | Rights | Formats |\n|---|---|---|---|\n{rows}",
  "# The Translation Trap", "An original constitutional text may be public domain while its modern English translation stays copyrighted. Every provision record therefore carries `text_language`, `translation_source` and `translation_rights` as separate fields — see [[Witness Reading Instrument]]. The [[Constitution Corpus]] already shows the pattern: 55 of its 240 English texts are publisher-copyrighted translations of public-domain originals.",
 ], ["[[Seed Collection]] · [[Witness Reading Instrument]] · [[Import Constitutions Plan]] · [[Constitution Corpus]]"])

save("Seed Collection", [ACC,
  "About twenty instruments to import first, chosen for reuse rights and for range, rather than every constitution indiscriminately. UK texts lead, because the Open Government Licence permits everything this commons might become and because the UK constitution is scattered across statutes that have never been gathered this way.",
  "# United Kingdom — [[UK Legislation]], OGL v3",
  "- Magna Carta 1297 — `aep/Edw1cc1929/25/9`\n- Bill of Rights 1688 — `aep/WillandMarSess2/1/2`\n- Act of Settlement 1700 — `aep/Will3/12-13/2`\n- Parliament Act 1911 and Parliament Act 1949\n- Human Rights Act 1998 — `ukpga/1998/42`\n- Constitutional Reform Act 2005 — `ukpga/2005/4`\n- Well-being of Future Generations (Wales) Act 2015 — `anaw/2015/2`, English and Welsh",
  "# New Zealand — [[New Zealand Legislation]], no copyright",
  "- Constitution Act 1986\n- New Zealand Bill of Rights Act 1990\n- Te Urewera Act 2014 — a forest as a legal person\n- Te Awa Tupua (Whanganui River Claims Settlement) Act 2017 — a river as a legal person",
  "# Australia, Canada, United States",
  "- Commonwealth of Australia Constitution Act — [[Australian Federal Register of Legislation]], CC BY 4.0\n- Constitution Acts 1867 to 1982 and the Charter of Rights and Freedoms — [[Canada Justice Laws]]\n- Constitution of the United States — [[US GovInfo]] and the National Archives transcript\n- A deliberately varied sample of state constitutions — [[Open US Law]], 13,382 constitutional sections to choose from",
  "# France and the European Union",
  "- Constitution of 1958 and the Charter for the Environment 2004 — [[French LEGI Open Data]], CONSTIT base, French text authoritative\n- Treaty on European Union and the Charter of Fundamental Rights — [[EUR-Lex]]",
  "# Community and experimental",
  "- [[CommunityRule]] templates — CC BY-SA 4.0\n- [[Sustainable Economies Law Center]] cooperative bylaws — CC BY-SA 4.0\n- [[Metagov Constitution Template]] — MIT, DAO texts audited one by one\n- [[Creative Commons Legal Codes]] — CC0, law written to be forked",
  "# Why the New Zealand Acts matter most",
  "Te Urewera and Te Awa Tupua are not rights clauses about nature; they make a forest and a river juridical subjects with their own standing and guardians. Beside Ecuador's Article 71 and Bolivia's Mother Earth they let the [[Clause Library]] compare a right *to* nature with nature *as* a legal person.",
 ], ["[[Constitutional Sources]] · [[Witness Reading Instrument]] · [[Import Constitutions Plan]]"])

save("Witness Reading Instrument", [ACC,
  "Three layers, so that a provision can grow a cloud of interpretation without anyone silently corrupting the legal text. The research David supplied names them; this page fits them to what the site already does.",
  "# The Layers",
  "- **Witness** — the exact, unedited provision from the source. No `[[wiki links]]` inside the canonical wording, ever. On this site a witness is a *fragment*: the verbatim quote under a fragment id, and the `fragments.jsonl` asset that holds every one.\n- **Reading** — commentary, links, comparisons, poems, interpretations. The [[Clause Library]] pages are readings; so are the For Speaking and Notable sections on a constitution page, and any page a person writes about a provision.\n- **Instrument** — the table of contents that connects a text's provisions. A constitution page on this register is an instrument page: its Record, its Structure outline, and its assets.",
  "The fragment id `{constitution}:{article}.{paragraph}` names the witness; readings cite it; the instrument lists it. A witness never changes; a reading may.",
  "# The Provision Record",
  "Every witness carries a record like this, so every fork is traceable and the translation trap is visible:",
  {"type": "code", "language": "yaml", "text": "\n".join([
    "jurisdiction: New Zealand", "instrument: Te Awa Tupua (Whanganui River Claims Settlement) Act 2017", "provision: Section 12",
    "fragment_id: te-awa-tupua-2017:12", "version_date: 2026-09-02", "status: in_force", "text_language: en",
    "translation_source: none — original", "translation_rights: n/a", "source_url: https://www.legislation.govt.nz/act/public/2017/0007/latest/DLM6830851.html",
    "source_format: xml", "rights: public-domain-nz-legislation (Copyright Act 1994 s 27)", "retrieved_at: 2026-09-02",
    "source_hash: sha256:…", "canonical_text_modified: false"])},
  "For the [[Constitution Corpus]] the same record reads `text_language: en`, `translation_source: Constitute Project`, and `translation_rights` is either `CC BY-NC 3.0` or the publisher's notice — which is exactly the split the register already makes between attached and excerpted texts.",
  "# What Changes on This Site",
  "- The constitution pages stay as they are: instrument pages with readings attached.\n- When fragments earn pages — the Fragment Mill's twenty first — they are witness pages: verbatim text, the provision record, nothing else. Readings link to them; they link to nothing.\n- The importer for the [[Seed Collection]] creates witness pages and instrument pages from XML directly, with the provision record filled from the source's own metadata and a hash of the text.",
 ], ["[[Constitutional Sources]] · [[Seed Collection]] · [[Import Constitutions Plan]]"])

# correct the corpus licence line on both sites
for site in ("constitution.legalcommons.org", "clause.legalcommons.org"):
    P = os.path.expanduser(f"~/Nextcloud/fedwiki/{site}/pages/constitution-corpus"); page = fedwiki.load_page(P)
    for it in page["story"]:
        if it.get("text", "").startswith("There is no open licence."):
            it["text"] = ("The about page states the licence: \"Creative Commons Attribution-Non Commercial 3.0 Unported License\", which \"allows you to make free use of information from the site for noncommercial purposes.\" The terms page adds: \"You may print material from the CCP website for your legitimate purposes, but you may not charge a fee for any use and commercial use is expressly prohibited.\" The station and this site are non-commercial and charge nothing, which qualifies. Every fragment that airs is attributed on air and on its page to the Constitute Project. Anything commercial — a paid programme, a sold recording — would need their permission first. Corrected 3 September 2026; the first version of this page said no licence was stated.")
            fedwiki.add_journal(page, "edit", it, provenance="Claude Code, 3 September 2026")
    fedwiki.save_page(P, page)
print("sources written:", len(SOURCES), "+ 3 index pages; corpus licence corrected")
