"""ENAM's 17 filing categories, refined into sub-types with a base materiality (0-1).

The category alone does not decide importance: "results" covers both the actual
numbers (market-moving) and the newspaper advert that reprints them (paperwork).
So every rule maps to (category, subtype, base). The first matching rule wins,
and routine paperwork rules run first so they can never be scored like the
real event.

`subject` regexes look at the exchange subject line (plus the exchange's own
category); `text` regexes look at subject + detail + attachment name.
Nothing here names a company.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CATEGORIES = [
    "results", "M&A", "fund_raise", "management_change", "litigation",
    "insider_trading", "earnings_call", "investor_meetings", "credit_rating",
    "dividend", "bonus_split", "capex", "press_release", "postal_ballot",
    "agm_egm", "pledging", "unclassified",
]

# Base for a category when only the LLM could classify it (no subtype rule).
CATEGORY_BASE = {
    "results": 0.6, "M&A": 0.6, "fund_raise": 0.5, "management_change": 0.45, "litigation": 0.55,
    "insider_trading": 0.25, "earnings_call": 0.2, "investor_meetings": 0.06, "credit_rating": 0.3,
    "dividend": 0.25, "bonus_split": 0.5, "capex": 0.45, "press_release": 0.3, "postal_ballot": 0.1,
    "agm_egm": 0.1, "pledging": 0.45, "unclassified": 0.05,
}


@dataclass(frozen=True)
class Rule:
    category: str
    subtype: str
    base: float
    subject: str | None = None
    text: str | None = None
    notext: str | None = None
    routine: bool = False
    card: str = "summary"            # results | people | summary | none

    def matches(self, subject: str, blob: str) -> bool:
        if self.subject and not re.search(self.subject, subject, re.I):
            return False
        if self.text and not re.search(self.text, blob, re.I):
            return False
        if self.notext and re.search(self.notext, blob, re.I):
            return False
        return bool(self.subject or self.text)


TOP_ROLE = (r"\b(ceo|cfo|coo|managing director|md|chief executive|chief financial|chief operating|"
            r"whole[- ]?time director|(?<!non[- ])executive director|chairman|chairperson)\b")
MGMT_EVENT = (r"change in (the )?(directorate|directors?|management|kmp|key managerial|senior management)|"
              r"resign|appoint|re-?appoint|cessation|superannuat|retire|demise|step(s|ped)? down")

RULES: list[Rule] = [
    # ---------------------------------------------------------------- routine paperwork first
    Rule("results", "newspaper_ad", 0.05, subject=r"newspaper|publication of (the )?(un-?audited |audited )?financial|advertisement",
         routine=True, card="none"),
    # a board outcome that carries the results is the results, whatever else it lists
    Rule("results", "financials", 0.75,
         text=r"(submitted|submission of).{0,80}financial results|outcome of (the )?board meeting.{0,300}financial results|"
              r"financial results.{0,300}outcome of (the )?board meeting|financial results for the (quarter|period|half)",
         notext=r"newspaper|publication|intimation of (the )?board|will be held|to consider|tax deduction|issued by|"
                r"commentary|presentation|media statement",
         card="results"),
    # scheme votes convened by the NCLT are a step in an M&A, not routine
    Rule("M&A", "scheme_vote", 0.35,
         text=r"nclt\W{0,6}convened|(voting results|scrutini[sz]er).{0,250}scheme of (amalgamation|arrangement)|"
              r"scheme of (amalgamation|arrangement).{0,250}(voting results|scrutini[sz]er)", card="summary"),
    # another company's results (e.g. the parent's), reported for information
    Rule("press_release", "related_company_results", 0.2,
         text=r"results (issued|published|announced) by|financial results of (the |its )?(parent|promoter|holding)",
         card="summary"),
    # shareholder votes: the vote is the event, whatever the resolution is about
    Rule("postal_ballot", "key_resolution", 0.35, subject=r"postal[ _]ballot",
         text=TOP_ROLE + r"|merger|amalgamation|scheme|buy ?back|preferential|qip|rights issue", card="summary"),
    Rule("postal_ballot", "routine", 0.1, text=r"postal[ _]ballot|e-?voting result|scrutini[sz]er", routine=True, card="none"),
    Rule("unclassified", "esop", 0.03, text=r"\besop|\besos|\besps|employee stock option|stock option scheme", routine=True, card="none"),
    Rule("unclassified", "registrar_or_compliance", 0.02,
         text=r"trading window|regulation\s*74\s*\(5\)|compliance certificate|registra|share transfer agent|\brta\b|kfin|"
              r"loss of share certificate|duplicate share|investor (grievance|complaint)|business responsibility|\bbrsr\b",
         routine=True, card="none"),
    # ---------------------------------------------------------------- earnings calls before meetings
    Rule("earnings_call", "transcript", 0.25, text=r"transcript", card="none"),
    Rule("earnings_call", "recording", 0.1, text=r"\brecording\b", routine=True, card="none"),
    Rule("earnings_call", "call_update", 0.15, text=r"\bq[1-4]\s*fy\s*'?\d{2,4}\s*(earnings )?call|earnings (conference )?call",
         notext=r"schedul|will (attend|participate)|intimation of", card="none"),
    Rule("investor_meetings", "meet", 0.06,
         text=r"analyst|institutional investor|investor (meet|conference|day|event)|non[- ]deal roadshow|one[- ]on[- ]one|"
              r"con\.? ?call updates|investor conference",
         routine=True, card="none"),
    # ---------------------------------------------------------------- results
    Rule("results", "board_meeting_intimation", 0.15,
         text=r"(board meeting intimation|intimation of (the )?board meeting|prior intimation).{0,200}result", routine=True, card="none"),
    Rule("fund_raise", "board_meeting_intimation", 0.15,
         text=r"(board meeting intimation|intimation of (the )?board meeting|prior intimation)", routine=True, card="none"),
    Rule("results", "financials", 0.75,
         subject=r"financial results?|un-?audited|audited|results for the (quarter|half|year)|integrated filing.{0,20}financial",
         notext=r"newspaper|publication|intimation|will be held|to consider|media statement|presentation|tax deduction|issued by",
         card="results"),
    Rule("results", "presentation_or_statement", 0.4, subject=r"financial results?.{0,40}(media statement|presentation)", card="summary"),
    Rule("results", "press_release", 0.62, subject=r"press release|media release|media statement",
         text=r"\bq[1-4]\s*fy|quarter (ended|and half)|half year ended|\bpat\b|net profit|revenue (rose|grew|fell|declined|of|up|down)",
         card="summary"),
    Rule("results", "investor_presentation", 0.2, text=r"investor presentation|earnings presentation|results presentation",
         routine=True, card="none"),
    Rule("results", "periodic_report", 0.4, text=r"half[- ]yearly report|half yearly (financial|results)", card="summary"),
    # ---------------------------------------------------------------- general meetings
    Rule("agm_egm", "egm", 0.3, text=r"extra[- ]?ordinary general meeting|\begm\b", card="summary"),
    Rule("agm_egm", "agm", 0.08, text=r"annual general meeting|\bagm\b|book closure", routine=True, card="none"),
    # ---------------------------------------------------------------- management change
    Rule("management_change", "auditor", 0.1,
         text=r"(statutory|secretarial|internal|cost) auditors?|change in (the )?auditors?", routine=True, card="none"),
    Rule("management_change", "top", 0.75, text=f"(?=.*({MGMT_EVENT}))(?=.*{TOP_ROLE})", card="people"),
    Rule("management_change", "board", 0.4,
         text=f"(?=.*({MGMT_EVENT}))(?=.*(independent director|non[- ]executive director|additional director|nominee director))",
         card="people"),
    Rule("management_change", "senior", 0.45, subject=MGMT_EVENT, card="people"),
    # ---------------------------------------------------------------- insider dealing, then litigation
    Rule("insider_trading", "insider", 0.25,
         text=r"\(pit\)|prohibition of insider trading|insider trading|regulation\s*7\s*\(2\)|regulation\s*29|\bsast\b|"
              r"substantial acquisition", card="summary"),
    Rule("pledging", "pledge", 0.5, text=r"\bpledg|encumbrance|regulation\s*31", card="summary"),
    Rule("litigation", "insolvency", 0.8, text=r"insolvency|\bcirp\b|\bnclt\b|\bnclat\b|\bibc\b", card="summary"),
    Rule("litigation", "enforcement", 0.7,
         text=r"show cause|penalty|adjudicat|sebi order|\b(search|raid)\b|tax demand|demand (notice|order)|gst demand|"
              r"warning letter|import alert|form 483|\bfraud\b|forensic", card="summary"),
    Rule("litigation", "dispute", 0.45, text=r"litigation|dispute|regulatory action|arbitration|\bcourt\b|tribunal|writ petition",
         card="summary"),
    # ---------------------------------------------------------------- M&A
    Rule("M&A", "deal", 0.7,
         text=r"acqui(re|sition)|amalgamation|merger|demerger|scheme of arrangement|joint venture|share purchase agreement|"
              r"business transfer|slump sale|divest|stake sale",
         notext=r"acquisition of shares by|regulation\s*29|\bsast\b", card="summary"),
    Rule("M&A", "subsidiary", 0.35, text=r"incorporation of (a |wholly[- ]owned )?(step[- ]down )?subsidiar|investment in (a |wholly[- ]owned )?subsidiar",
         card="summary"),
    # ---------------------------------------------------------------- fund raising
    Rule("fund_raise", "buyback", 0.7, text=r"buy[- ]?back", card="summary"),
    Rule("fund_raise", "debt", 0.3, text=r"commercial paper|non[- ]convertible debenture|\bncds?\b|\bbonds?\b|debenture",
         card="summary"),
    Rule("fund_raise", "equity", 0.72,
         text=r"\bqip\b|qualified institution|rights issue|preferential (issue|allotment)|\bwarrants?\b|fund ?rais|raising of funds",
         card="summary"),
    # ---------------------------------------------------------------- capital actions and ratings
    Rule("bonus_split", "bonus_split", 0.55, text=r"bonus (issue|shares)|sub[- ]?division|stock split|split of (equity )?shares",
         card="summary"),
    Rule("dividend", "record_or_tax", 0.1, text=r"(record date|tax deduction|\btds\b).{0,60}dividend|dividend.{0,60}(record date|tax deduction|\btds\b)",
         routine=True, card="none"),
    Rule("dividend", "declared", 0.3, text=r"\b(interim|final|special) dividend|dividend of|declared.{0,30}dividend", card="summary"),
    Rule("credit_rating", "downgrade", 0.7, text=r"(credit rating|rating).{0,200}(downgrad|negative)|downgrad.{0,60}rating", card="summary"),
    Rule("credit_rating", "upgrade", 0.45, text=r"(credit rating|rating|outlook).{0,200}(upgrad|positive)", card="summary"),
    Rule("credit_rating", "reaffirm", 0.1, text=r"credit rating|\brating\b", routine=True, card="none"),
    # ---------------------------------------------------------------- operations and news
    Rule("capex", "capex", 0.5,
         text=r"capex|capital expenditure|new (plant|facility|unit|campus|cent(er|re))|capacity expansion|"
              r"expansion of .{0,60}(cent(er|re)|plant|facility|campus|capacity)|greenfield|brownfield|commission(ed|ing) of",
         card="summary"),
    Rule("press_release", "clarification", 0.45,
         text=r"clarification|rumou?r verification|news item|media report|price movement|spurt in volume", card="summary"),
    Rule("press_release", "order_win", 0.5,
         text=r"bagging|receiving of order|orders? (win|won|bagged|secured|received)|wins? .{0,80}\border|letter of (award|intent)|"
              r"award(ed)? (of )?(a )?contract", card="summary"),
    Rule("press_release", "business_update", 0.4,
         text=r"production volume|sales volume|monthly (business )?update|traded volume|sold [\d,]+ units|business update",
         card="summary"),
    Rule("press_release", "general", 0.25, subject=r"press release|media release|general|updates", card="summary"),
]


@dataclass
class Classification:
    category: str
    subtype: str
    base: float
    confidence: float
    method: str                      # rule | llm | default
    routine: bool = False
    card: str = "summary"
    matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)
