"""The reading pass: twenty fragments chosen by hand from the scored shortlist
plus the famous clauses the lexical score cannot see. Each carries a framing
line — what it is, where it comes from — and the exact text from the corpus."""
import json, re
us = [json.loads(l) for l in open("scored.jsonl")]
by = {}
for u in us: by.setdefault(u["cons_id"], []).append(u)
def pick(cid, pat, minw=12):
    hits = [u for u in by[cid] if re.search(pat, u["text"], re.I) and u["words"] >= minw]
    hits.sort(key=lambda u: u["words"]); return hits[0]   # the article, not the longest window
PICKS = [
 ("Bolivia_2009", r"^In ancient times mountains arose", "The Constitution of Bolivia, 2009, opens before there is a state — with geology, and with what came after it."),
 ("Ecuador_2021", r"^Nature, or Pacha Mama, where life is reproduced", "Article 71 of the Constitution of Ecuador, 2008 — the first constitution to give nature rights of its own."),
 ("Bhutan_2008", r"minimum of sixty percent", "Article 5 of the Constitution of Bhutan, 2008. A floor for the forest, held for all time."),
 ("Bhutan_2008", r"^The State shall strive to promote those conditions that will enable the pursuit of Gross National Happiness\.$", "Article 9 of the Constitution of Bhutan. Seventeen words."),
 ("Japan_1946", r"^Aspiring sincerely to an international peace", "Article 9 of the Constitution of Japan, 1946 — the renunciation of war, still in force."),
 ("German_Federal_Republic_2014", r"^Amendments to this Basic Law affecting the division", "Article 79 of the German Basic Law, 1949 — the eternity clause: what may never be amended."),
 ("Nicaragua_2014", r"^Nicaraguans have the right to live in a healthy environment", "Article 60 of the Constitution of Nicaragua, as revised in 2014. The earth as a subject of dignity."),
 ("Zimbabwe_2021", r"land is a finite natural resource", "Section 289 of the Constitution of Zimbabwe, 2013. Land as common heritage."),
 ("Gambia_2018", r"generations of Gambians yet unborn", "From the preamble of the Constitution of The Gambia, 1996 — a gift to the unborn."),
 ("Micronesia_1990", r"^Micronesia began in the days when man explored seas", "The preamble of the Constitution of the Federated States of Micronesia, 1978."),
 ("Tuvalu_2023", r"^DEEPLY CONCERNED with the imminent existential threat", "From the preamble of the Constitution of Tuvalu, 2023 — a constitution written under rising water."),
 ("Papua_New_Guinea_2016", r"^We declare our fourth goal", "The fourth National Goal of the Constitution of Papua New Guinea, 1975 — resources held in trust."),
 ("Uruguay_2004", r"^The national policy concerning water and sanitation", "Article 47 of the Constitution of Uruguay, added by referendum in 2004 — water as a public good."),
 ("Marshall_Islands_1995", r"^WE, THE PEOPLE OF THE REPUBLIC OF THE MARSHALL ISLANDS", "The preamble of the Constitution of the Marshall Islands, 1979."),
 ("United_Kingdom_2013", r"^NO Freeman shall be taken or imprisoned", "Clause 29 of Magna Carta, in the 1297 statute — still on the statute book of England."),
 ("Bahrain_2017", r"social and human systems are not inflexible tools", "From the preamble of the Constitution of Bahrain, 2002 — on borrowing institutions."),
 ("Iraq_2005", r"^We, the people of Mesopotamia", "The preamble of the Constitution of Iraq, 2005. The first law made by man."),
 ("Bolivia_2009", r"ama qhilla, ama llulla, ama suwa", "Article 8 of the Constitution of Bolivia, 2009 — the ethical principles of a plural society, in Quechua, Aymara and Guaraní."),
 ("Switzerland_2014", r"dignity of living beings", "Article 120 of the Swiss Federal Constitution — the dignity of living beings, written into law in 1999."),
 ("Denmark_1953", r"three times been called upon to disperse", "Section 80 of the Constitution of Denmark, 1953 — the protocol for dispersing a riot."),
]
out = []
for i, (cid, pat, frame) in enumerate(PICKS, 1):
    u = pick(cid, pat, minw={"Papua_New_Guinea_2016":60,"Zimbabwe_2021":40,"Marshall_Islands_1995":90}.get(cid, 12))
    t = u["text"]
    if len(t.split()) > 100:            # over the band: cut at the last clause break before 100 words
        head = " ".join(t.split()[:100]); cut = max(head.rfind(";"), head.rfind(". "))
        t = head[:cut].rstrip(";,") + "."
    out.append(dict(n=i, cons_id=cid, title=u["title"], heading=u["heading"], words=len(t.split()),
                    score=u["score"], d=u["d"], frame=frame, text=t, topics=u["topics"]))
json.dump(out, open("top20.json", "w"), indent=1, ensure_ascii=False)
for o in out: print(f"{o['n']:2d}. {o['title'][:28]:28s} {o['words']:3d}w  {o['score']:.2f}  {o['text'][:60]}")
