"""Conservative editorial scope for imported vacancies at financial institutions.

Classify the role title, never the employer name or boilerplate description.
Unknown titles are withheld for review. Technical exclusions take precedence
so e.g. an AML application engineer is not mistaken for a compliance officer.
"""
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class RoleDecision:
    include: bool
    reason: str


def normalized(title):
    return ''.join(c for c in unicodedata.normalize('NFKD', title.casefold()) if not unicodedata.combining(c))


TECHNOLOGY = re.compile(
    r'\b(engineer\w*|ingenieur\w*|architect\w*|architekt\w*|developer\w*|developpeur\w*|entwickler\w*|'
    r'software|devops|sre|scrum|cyber\w*|informatik\w*|informatique|it|ict|infrastructure|'
    r'database|datenbank\w*|cloud|blockchain|ux|ui|technology|technical|technisch\w*|technique)\b|'
    r'\b(application|applications|production)\s+(support|integration)|'
    r'\b(trading|crm|pricing)\s+systems?\b|\bsystem\s+integration\b|'
    r'\b(test|testing)\s+(manager|environment|specialist|automation)|'
    r'\bdata\s+(platform|office|scientist|science|governance|analytics\s+expert)|'
    r'\b(generative\s+ai|ai\s+(workshop|innovation|automation)|information\s+security)|'
    r'\bplatform\s+(owner|specialist)|\bdigital\s+delivery\b|'
    r'\b(unified\s+communications|enterprise\s+collaboration|e[ -]?banking)\b'
)
SUPPORT = re.compile(
    r'\b(reception\w*|telephon\w*|hospitality|facilit\w*|executive\s+assistant|administrative\s+support|'
    r'hr|human\s+resources|recruit\w*|talent\s+acquisition|marketing|web\s+publishing|'
    r'corporate\s+services|global\s+mobility|compensation|physical\s+security|workplace\s+safety|'
    r'sicherheitsdienst|ressources\s+humaines|personalwesen)\b'
)
FINANCE = re.compile(
    r'\b(financ\w*|finanz\w*|accountant\w*|accounting|comptab\w*|buchhalt\w*|'
    r'controller\w*|controlling|valuation|bewertung\w*|treasury|tresorerie|'
    r'investment\w*|investissement\w*|anlagen?\w*|asset\s+(management|manager|allocation|liability)|'
    r'portfolio\w*|portefeuille\w*|wealth\w*|vermogens\w*|equity|equities|fixed\s+income|'
    r'funds?|fonds\w*|hedge|private\s+assets|private\s+equity|'
    r'credit\w*|kredit\w*|mortgage\w*|hypothek\w*|lending|loans?|'
    r'risk\w*|risiko\w*|risque\w*|compliance|conformite|aml|kyc|sanctions?|cross[ -]border|'
    r'tax\w*|steuer\w*|fiscal\w*|audit\w*|revision|'
    r'banker\w*|banking|banquier\w*|banque|relationship\s+(manager|officer)|kundenberater\w*|'
    r'client\s+(associate|relationship|advis\w*|data\s+services)|'
    r'structured\s+products?|derivatives?|derivate\w*|trader\w*|trading|e[ -]trading|'
    r'trade\s+(reporting|processing|finance)|fx|foreign\s+exchange|'
    r'corporate\s+actions?|custody|safekeeping|cash\s+(desk|management)|'
    r'settlement\w*|securities|wertpapier\w*|metaux\s+precieux|'
    r'quantitative\s+(analyst|research)|product\s+control|'
    r'pricing|revenue|dcfo|cfo|family\s+offices?|institutional\s+(clients|sales))\b'
)


def classify_role(title):
    title = normalized(title)
    # A business developer in private banking is a commercial role, not software.
    technical_title = re.sub(r'\bbusiness developer\b', 'business development', title)
    # Financial engineering is a finance discipline; generic engineering is not.
    technical_title = re.sub(r'\bfinancial engineer(?:ing)?\b', 'financial structuring', technical_title)
    if TECHNOLOGY.search(technical_title):
        return RoleDecision(False, 'technology_role')
    if SUPPORT.search(title):
        return RoleDecision(False, 'non_finance_support')
    if re.search(r'\b(product owner|project (lead|manager))\b', title):
        return RoleDecision(False, 'needs_finance_review')
    if FINANCE.search(title):
        return RoleDecision(True, 'finance_role')
    return RoleDecision(False, 'needs_finance_review')
