"""Moteur de génération de livrables.

Delivra fonctionne sans aucune dépendance réseau : un moteur « local » compose
un dossier complet (contexte, architecture, déploiement, sécurité, tests,
planning, risques…) à partir de la description du projet et de référentiels
métier. Un fournisseur LLM optionnel (OpenAI, Mistral, Anthropic, Ollama…)
peut être branché pour enrichir ou réécrire les sections.
"""
from __future__ import annotations

import json
import os
import random
from datetime import date
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ..model import DEFAULT_OPTIONS, new_id, normalize, today_fr
from ..theme import FONT_STACKS, PALETTES

# --------------------------------------------------------------------------- #
#  Référentiels                                                               #
# --------------------------------------------------------------------------- #
PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "cloud": {
        "label": "Migration / plateforme cloud",
        "keywords": ["cloud", "azure", "aws", "gcp", "migration", "kubernetes", "saas", "héberg"],
        "sections": ["contexte", "objectifs", "perimetre", "architecture", "deploiement",
                     "securite", "tests", "exploitation", "planning", "risques"],
        "stack": ["Azure", "Kubernetes (AKS)", "Terraform", "Azure DevOps", "Azure Monitor"],
        "benefits": [("Réduction du coût d'infrastructure", "-28 %"),
                     ("Délai de mise à disposition d'un environnement", "4 h → 25 min"),
                     ("Disponibilité de la plateforme", "99,95 %"),
                     ("Automatisation des déploiements", "100 %")],
        "risks": [("Dépendance à un fournisseur unique", "Moyenne", "Architecture portable, conteneurs standards"),
                  ("Dépassement budgétaire cloud", "Moyenne", "Alertes de budget et revue FinOps mensuelle"),
                  ("Compétences internes insuffisantes", "Élevée", "Programme de formation et transfert de compétences")],
        "tests": ["Tests unitaires automatisés (seuil de couverture 80 %)",
                  "Tests d'intégration des flux et API",
                  "Tests de performance (montée en charge ×3)",
                  "Tests de reprise après sinistre (RTO 4 h / RPO 1 h)"],
        "deployment_steps": [
            "Validation du plan d'architecture et des prérequis réseau.",
            "Provisionnement de l'infrastructure par Terraform (3 environnements).",
            "Déploiement des services applicatifs via pipeline CI/CD.",
            "Exécution du plan de recette et validation des critères d'acceptation.",
            "Bascule progressive du trafic (canary 10 % → 50 % → 100 %).",
            "Activation de la supervision, des alertes et du plan de reprise.",
        ],
        "architecture_layers": [
            ("Canaux & utilisateurs", ["Portail web", "Application mobile", "Partenaires API"], "neutral"),
            ("Accès & sécurité", ["WAF", "API Gateway", "IAM / Entra ID"], "primary"),
            ("Services applicatifs", ["Front-end", "Services métier", "Traitements batch"], "dark"),
            ("Données", ["Base relationnelle", "Stockage objet", "Cache distribué"], "primary"),
            ("Supervision", ["Logs", "Métriques", "Alertes 24/7"], "accent"),
        ],
    },
    "data": {
        "label": "Plateforme data & analytics",
        "keywords": ["data", "analytics", "bi", "entrepôt", "databricks", "power bi", "etl", "lakehouse", "ia", "intelligence artificielle"],
        "sections": ["contexte", "objectifs", "resultats", "architecture", "donnees", "deploiement",
                     "securite", "exploitation", "planning", "risques"],
        "stack": ["Databricks", "Delta Lake", "Azure Data Factory", "Power BI", "Unity Catalog"],
        "benefits": [("Sources de données unifiées", "17"),
                     ("Temps de production des reportings", "-78 %"),
                     ("Utilisateurs métier équipés", "240"),
                     ("Taux de complétude des données", "98,6 %")],
        "risks": [("Qualité des données sources", "Élevée", "Contrôles automatiques et tableau de bord de qualité"),
                  ("Dérive des coûts de calcul", "Moyenne", "Dimensionnement des clusters et suivi FinOps"),
                  ("Adhésion des métiers", "Moyenne", "Ateliers de conception et ambassadeurs métier")],
        "tests": ["Contrôles de qualité des données (complétude, unicité, cohérence)",
                  "Tests de réconciliation source / cible",
                  "Validation des restitutions avec les métiers",
                  "Tests de performance sur volumes cibles (+30 %)"],
        "deployment_steps": [
            "Cartographie des sources et validation des accès.",
            "Déploiement de la plateforme et des zones bronze / argent / or.",
            "Industrialisation des 17 flux d'ingestion orchestrés.",
            "Construction du référentiel client et des indicateurs métier.",
            "Publication des tableaux de bord et formation des utilisateurs.",
        ],
        "architecture_layers": [
            ("Sources", ["CRM", "ERP / facturation", "Web & mobile", "Fichiers partenaires"], "neutral"),
            ("Ingestion", ["Data Factory", "Event Hubs"], "primary"),
            ("Plateforme data", ["Zone bronze", "Zone argent", "Zone or"], "dark"),
            ("Services & restitution", ["API sémantique", "Power BI", "Data Science"], "primary"),
            ("Gouvernance", ["Catalogue", "Qualité", "Traçabilité"], "accent"),
        ],
    },
    "web": {
        "label": "Application web / mobile",
        "keywords": ["web", "application", "mobile", "portail", "site", "pwa", "front", "e-commerce", "saas"],
        "sections": ["contexte", "objectifs", "perimetre", "architecture", "integrations",
                     "tests", "deploiement", "securite", "planning", "risques"],
        "stack": ["React / Next.js", "API REST", "PostgreSQL", "Redis", "CI/CD GitLab"],
        "benefits": [("Temps de chargement perçu", "< 1,8 s"),
                     ("Taux de conversion", "+34 %"),
                     ("Accessibilité", "WCAG 2.2 AA"),
                     ("Couverture de tests", "82 %")],
        "risks": [("Périmètre fonctionnel mouvant", "Élevée", "Cadrage par lots et comité de changement"),
                  ("Performance sur réseaux mobiles", "Moyenne", "Budget de performance et tests réels"),
                  ("Accessibilité non conforme", "Moyenne", "Audit RGAA et corrections avant mise en production")],
        "tests": ["Tests unitaires et d'intégration (Jest / Playwright)",
                  "Tests end-to-end sur parcours critiques",
                  "Audit d'accessibilité RGAA / WCAG 2.2 AA",
                  "Tests de charge et de résilience"],
        "deployment_steps": [
            "Validation des maquettes et du design system.",
            "Mise en place des environnements et du pipeline CI/CD.",
            "Développement par lots fonctionnels avec démonstrations bimensuelles.",
            "Recette métier et correction des anomalies.",
            "Mise en production progressive et hypercare de 30 jours.",
        ],
        "architecture_layers": [
            ("Clients", ["Navigateur", "Application mobile", "PWA"], "neutral"),
            ("Distribution", ["CDN", "WAF", "Load balancer"], "primary"),
            ("Application", ["Front-end SSR", "API REST", "Workers asynchrones"], "dark"),
            ("Données", ["PostgreSQL", "Redis", "Stockage objet"], "primary"),
            ("Observabilité", ["APM", "Logs", "Alerting"], "accent"),
        ],
    },
    "integration": {
        "label": "Intégration / API & interopérabilité",
        "keywords": ["api", "intégration", "interop", "esb", "middleware", "crm", "interfaces", "gateway", "kafka"],
        "sections": ["contexte", "objectifs", "architecture", "integrations", "deploiement",
                     "securite", "tests", "exploitation", "planning", "risques"],
        "stack": ["API Gateway", "Kong / APIM", "Kafka", "SAP PI/PO", "Azure Functions"],
        "benefits": [("Interfaces industrialisées", "22"),
                     ("Latence moyenne des échanges", "180 ms"),
                     ("Réduction des développements ad hoc", "-45 %"),
                     ("Disponibilité des interfaces", "99,9 %")],
        "risks": [("Couplage fort entre systèmes", "Moyenne", "Contrats d'interface versionnés"),
                  ("Saturation des files de messages", "Moyenne", "Supervision des files et auto-scaling"),
                  ("Hétérogénéité des formats", "Élevée", "Canonical model et validation stricte")],
        "tests": ["Tests de contrat (Pact) sur chaque interface",
                  "Tests de non-régression des flux existants",
                  "Tests d'idempotence et de reprise sur erreur",
                  "Tests de charge sur les API exposées"],
        "deployment_steps": [
            "Inventaire des interfaces et des contrats existants.",
            "Mise en place de la plateforme d'API management.",
            "Déploiement des connecteurs et des transformations.",
            "Recette d'intégration de bout en bout.",
            "Bascule progressive et surveillance renforcée.",
        ],
        "architecture_layers": [
            ("Systèmes sources", ["SAP", "CRM Salesforce", "Applications métier"], "neutral"),
            ("Plateforme d'échange", ["API Gateway", "Bus Kafka", "Orchestrateur"], "primary"),
            ("Services", ["Transformations", "Validation", "Journalisation"], "dark"),
            ("Consommateurs", ["Portail client", "Data platform", "Partenaires"], "primary"),
            ("Gouvernance", ["Catalogue API", "Quotas", "Traçabilité"], "accent"),
        ],
    },
    "securite": {
        "label": "Cybersécurité / conformité",
        "keywords": ["sécurité", "securite", "cyber", "soc", "pentest", "iso 27001", "rgpd", "conformité"],
        "sections": ["contexte", "perimetre", "architecture", "securite", "tests",
                     "exploitation", "planning", "risques", "resultats"],
        "stack": ["Microsoft Sentinel", "Defender for Cloud", "Key Vault", "Entra ID", "Purview"],
        "benefits": [("Vulnérabilités critiques corrigées", "100 %"),
                     ("Délai de détection d'un incident", "< 15 min"),
                     ("Comptes à privilèges réduits", "-63 %"),
                     ("Couverture de la conformité ISO 27001", "94 %")],
        "risks": [("Rupture de service lors du durcissement", "Moyenne", "Déploiement par vagues et plan de retour"),
                  ("Faux positifs des sondes", "Élevée", "Tuning progressif des règles de détection"),
                  ("Résistance au changement", "Moyenne", "Sensibilisation et accompagnement des équipes")],
        "tests": ["Test d'intrusion externe et interne",
                  "Exercice de simulation d'incident (red team)",
                  "Revue de configuration et scan de vulnérabilités",
                  "Test de restauration des sauvegardes"],
        "deployment_steps": [
            "Audit initial de l'existant et analyse de risque.",
            "Déploiement des sondes et de la collecte de journaux.",
            "Durcissement des systèmes et gestion des accès à privilèges.",
            "Mise en service du SOC et des playbooks de réponse.",
            "Campagne de tests et rapport de conformité.",
        ],
        "architecture_layers": [
            ("Surfaces exposées", ["Internet", "Partenaires", "Postes internes"], "neutral"),
            ("Protection", ["WAF", "EDR", "MFA"], "primary"),
            ("Détection", ["SIEM", "Sondes réseau", "Chasse aux menaces"], "dark"),
            ("Réponse", ["Playbooks", "SOC 24/7", "Forensique"], "accent"),
            ("Gouvernance", ["Politiques", "Audit", "Conformité"], "neutral"),
        ],
    },
    "erp": {
        "label": "Déploiement ERP / SIRH",
        "keywords": ["erp", "sap", "sirh", "progiciel", "gestion", "finance", "paie", "sage", "odoo"],
        "sections": ["contexte", "objectifs", "perimetre", "architecture", "donnees",
                     "deploiement", "tests", "planning", "budget", "risques"],
        "stack": ["SAP S/4HANA", "Fiori", "SAP BTP", "Solution Manager", "Power BI"],
        "benefits": [("Processus standardisés", "46"),
                     ("Clôture comptable", "9 j → 4 j"),
                     ("Utilisateurs formés", "310"),
                     ("Reprise de données historiques", "7 ans")],
        "risks": [("Écarts entre processus standard et besoins", "Élevée", "Comité d'arbitrage et matrice de fit/gap"),
                  ("Disponibilité des experts métier", "Élevée", "Planification des ateliers en amont"),
                  ("Reprise de données incomplète", "Moyenne", "Réconciliation itérative avec la DAF")],
        "tests": ["Tests unitaires par processus (script SAP)",
                  "Tests d'intégration inter-modules",
                  "Recette métier clé en main (UAT)",
                  "Tests de reprise de données et d'équilibrage comptable"],
        "deployment_steps": [
            "Analyse des processus et matrice fit/gap.",
            "Paramétrage des modules et développement des spécifiques.",
            "Reprise et réconciliation des données de référence.",
            "Formation des utilisateurs clés et des formateurs.",
            "Bascule en mode big bang avec cellule de support renforcée.",
        ],
        "architecture_layers": [
            ("Accès", ["Portail Fiori", "Poste de travail", "Mobile"], "neutral"),
            ("Cœur ERP", ["Finance", "Achats", "Ventes", "Paie"], "primary"),
            ("Extensions", ["SAP BTP", "Interfaces", "Éditions spécifiques"], "dark"),
            ("Données", ["Base HANA", "Entrepôt", "Archivage"], "primary"),
            ("Exploitation", ["Monitoring", "Transport", "Support"], "accent"),
        ],
    },
}

SECTION_BLUEPRINTS: Dict[str, Dict[str, str]] = {
    "contexte": {"title": "Contexte & enjeux", "kicker": "Cadrage",
                 "intro": "Cette section présente le contexte métier, les limites de la situation actuelle et les enjeux de la transformation."},
    "objectifs": {"title": "Objectifs du projet", "kicker": "Cadrage",
                  "intro": "Les objectifs ci-dessous ont été validés avec les parties prenantes lors de l'atelier de cadrage."},
    "perimetre": {"title": "Périmètre & exclusions", "kicker": "Cadrage",
                  "intro": "Le périmètre fait foi entre les parties et délimite les obligations de chacun."},
    "architecture": {"title": "Architecture de la solution", "kicker": "Conception",
                     "intro": "L'architecture retenue privilégie la simplicité d'exploitation, la résilience et la maîtrise des coûts."},
    "deploiement": {"title": "Déploiement & infrastructure", "kicker": "Mise en œuvre",
                    "intro": "Le déploiement est industrialisé et reproductible : chaque environnement est créé par du code versionné."},
    "integrations": {"title": "Intégrations & interfaces", "kicker": "Conception",
                     "intro": "Les échanges avec l'écosystème applicatif sont décrits ci-dessous, avec leurs contrats et leurs fréquences."},
    "securite": {"title": "Sécurité & conformité", "kicker": "Confiance",
                 "intro": "La sécurité est intégrée dès la conception (security by design) et vérifiée à chaque étape du projet."},
    "donnees": {"title": "Données & migration", "kicker": "Mise en œuvre",
                "intro": "La stratégie de données couvre l'acquisition, la qualité, la migration et l'archivage."},
    "tests": {"title": "Stratégie de tests & recette", "kicker": "Qualité",
              "intro": "La recette conditionne la réception des livrables : chaque critère d'acceptation est vérifié et tracé."},
    "exploitation": {"title": "Exploitation & supervision", "kicker": "Run",
                     "intro": "Le dispositif d'exploitation précise les niveaux de service, la supervision et les modalités de support."},
    "planning": {"title": "Planning & jalons", "kicker": "Pilotage",
                 "intro": "Le planning est piloté par jalons contractuels, avec une revue d'avancement bimensuelle."},
    "budget": {"title": "Budget & ressources", "kicker": "Pilotage",
               "intro": "Le budget est présenté par lot, avec les charges de chaque partie et les hypothèses retenues."},
    "risques": {"title": "Risques & plan de mitigation", "kicker": "Pilotage",
                "intro": "Les risques sont identifiés, évalués et suivis en comité de projet à chaque revue."},
    "resultats": {"title": "Résultats & bénéfices", "kicker": "Valeur",
                  "intro": "Les bénéfices attendus sont mesurés à l'aide d'indicateurs définis avec les métiers."},
    "annexes": {"title": "Annexes", "kicker": "Références",
                "intro": "Les éléments de référence, glossaire et documents associés sont regroupés en annexe."},
}

MOOD_TONES = {
    "professionnel": "sobre, factuel et orienté résultats",
    "technique": "précis, avec les choix d'implémentation et les contraintes techniques",
    "commercial": "orienté bénéfices client et valeur apportée",
    "institutionnel": "formel, adapté à une direction générale ou un organisme public",
}


def detect_playbook(text: str) -> str:
    low = (text or "").lower()
    scores = {}
    for key, pb in PLAYBOOKS.items():
        score = 0.0
        for kw in pb["keywords"]:
            if kw in low:
                # un mot-clé long/spécifique pèse plus qu'un terme générique
                score += 1.0 + 0.06 * len(kw)
        scores[key] = score
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "cloud"


# --------------------------------------------------------------------------- #
#  Fournisseurs LLM                                                           #
# --------------------------------------------------------------------------- #
class LLMProvider:
    name = "local"

    @property
    def available(self) -> bool:
        return False

    def complete(self, system: str, prompt: str, max_tokens: int = 2400) -> Optional[str]:
        raise NotImplementedError


class NoLLM(LLMProvider):
    name = "local"

    @property
    def available(self) -> bool:
        return False


class OpenAICompatible(LLMProvider):
    """Tout endpoint compatible OpenAI (OpenAI, Mistral, Groq, vLLM, OpenRouter…)."""

    def __init__(self, base_url: str, api_key: str, model: str, label: str = "openai"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.name = label

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.model and (self.api_key or "localhost" in self.base_url or "127.0.0.1" in self.base_url))

    def complete(self, system: str, prompt: str, max_tokens: int = 2400) -> Optional[str]:
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "temperature": 0.45,
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key or 'local'}"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            print(f"[delivra] fournisseur LLM indisponible ({exc}) → moteur local")
            return None


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, prompt: str, max_tokens: int = 2400) -> Optional[str]:
        body = json.dumps({
            "model": self.model, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body,
            headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01",
                     "x-api-key": self.api_key})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
            return "".join(part.get("text", "") for part in data.get("content", []))
        except Exception as exc:  # noqa: BLE001 — dégradation silencieuse
            print(f"[delivra] Anthropic indisponible ({exc}) → moteur local")
            return None


def build_provider(settings: Optional[Dict[str, Any]] = None) -> LLMProvider:
    """Construit le fournisseur à partir des réglages (env > settings.json)."""
    s = settings or {}
    provider = (os.environ.get("DELIVRA_LLM_PROVIDER") or s.get("provider") or "local").lower()
    key = os.environ.get("DELIVRA_LLM_KEY") or s.get("api_key") or ""
    model = os.environ.get("DELIVRA_LLM_MODEL") or s.get("model") or ""
    base = os.environ.get("DELIVRA_LLM_URL") or s.get("base_url") or ""
    if provider == "openai":
        return OpenAICompatible(base or "https://api.openai.com/v1", key, model or "gpt-4o-mini", "openai")
    if provider == "mistral":
        return OpenAICompatible("https://api.mistral.ai/v1", key, model or "mistral-large-latest", "mistral")
    if provider in ("ollama", "local-openai"):
        return OpenAICompatible(base or "http://localhost:11434/v1", key, model or "llama3.1", "ollama")
    if provider == "anthropic":
        return AnthropicProvider(key, model or "claude-sonnet-4-20250514")
    if provider == "custom" and base:
        return OpenAICompatible(base, key, model or "default", "custom")
    return NoLLM()


# --------------------------------------------------------------------------- #
#  Contextualisation déterministe                                              #
# --------------------------------------------------------------------------- #
def _seed_for(brief: Dict[str, Any]) -> random.Random:
    """Graine stable : deux générations du même brief donnent le même document."""
    key = "|".join(str(brief.get(k) or "") for k in
                   ("client", "project", "title", "industry", "context", "playbook"))
    return random.Random(hash(key) & 0xFFFFFFFF)


def contextual_kpis(brief: Dict[str, Any], pb: Dict[str, Any]) -> List[tuple]:
    """Adapte les indicateurs au contexte : périmètre, secteur, équipe."""
    rnd = _seed_for(brief)
    base = list(brief.get("kpis") or pb["benefits"])[:4]
    while len(base) < 4:
        base.append(pb["benefits"][len(base) % len(pb["benefits"])])

    industry = (brief.get("industry") or "").lower()
    if any(k in industry for k in ("financ", "banque", "assur")):
        scen = [("Contrôles de conformité automatisés", f"{rnd.randint(12, 42)}"),
                ("Opérations tracées", f"{rnd.randint(96, 99)} %")]
    elif any(k in industry for k in ("sant", "médic", "medic")):
        scen = [("Échanges HDS sécurisés", f"{rnd.randint(8, 24)}"),
                ("Dossiers rapprochés", f"{rnd.randint(120, 480)} k")]
    elif any(k in industry for k in ("industr", "énergie", "logist")):
        scen = [("Sites raccordés", f"{rnd.randint(3, 18)}"),
                ("Arrêts de production évités", f"{rnd.randint(4, 22)}")]
    elif any(k in industry for k in ("public", "collectiv", "état", "etat")):
        scen = [("Agents formés", f"{rnd.randint(60, 320)}"),
                ("Délais de traitement", f"−{rnd.randint(18, 46)} %")]
    else:
        scen = [("Utilisateurs actifs", f"{rnd.randint(80, 640)}"),
                ("Ressaisies supprimées", f"−{rnd.randint(30, 70)} %")]

    contextual_map = {
        "Sources de données unifiées": f"{rnd.randint(8, 24)}",
        "Temps de production des reportings": f"−{rnd.randint(48, 84)} %",
        "Utilisateurs métier équipés": f"{rnd.randint(60, 480)}",
        "Taux de complétude des données": f"{rnd.randint(94, 99)},{rnd.randint(0, 9)} %",
        "Interfaces industrialisées": f"{rnd.randint(6, 40)}",
        "Réduction des développements ad hoc": f"−{rnd.randint(25, 60)} %",
        "Disponibilité des interfaces": f"99,{rnd.randint(5, 99)} %",
        "Temps de chargement perçu": f"< {rnd.uniform(0.8, 2.4):.1f} s",
        "Taux de conversion": f"+{rnd.randint(8, 38)} %",
        "Utilisateurs formés": f"{rnd.randint(80, 620)}",
        "Processus standardisés": f"{rnd.randint(20, 70)}",
        "Délai de détection d'un incident": f"< {rnd.randint(5, 30)} min",
        "Comptes à privilèges réduits": f"−{rnd.randint(40, 75)} %",
    }
    out: List[tuple] = [(label, contextual_map.get(label, value)) for label, value in base]
    if not brief.get("kpis"):
        out[-2], out[-1] = scen[0], scen[1]
    return out[:4]


def _contextual_risks(brief: Dict[str, Any], pb: Dict[str, Any]) -> List[tuple]:
    """Ajoute un risque propre au client (experts, données, charge de recette)."""
    rnd = _seed_for(brief)
    risks = list(pb["risks"])
    client = brief.get("client") or "le client"
    extra = [
        (f"Indisponibilité des experts métier de {client}", "Élevée",
         "Planning des ateliers arrêté avec la direction et suppléants désignés"),
        (f"Qualité insuffisante des données de {client}", "Moyenne",
         "Audit de qualité en phase de cadrage et contrôles automatisés"),
        ("Sous-estimation de la charge de recette", "Moyenne",
         f"Provision de {rnd.randint(8, 20)} % de la charge de test"),
    ]
    risks.append(extra[rnd.randrange(len(extra))])
    return risks[:4]


# --------------------------------------------------------------------------- #
#  Composition du livrable                                                    #
# --------------------------------------------------------------------------- #
def _titlecase_client(client: str) -> str:
    return client.strip() or "le client"


def _role_for(component: str, layers: List[Dict[str, Any]]) -> str:
    """Rattache un composant à la couche où il apparaît réellement."""
    name = (component or "").lower()
    for layer in layers:
        for node in layer.get("nodes") or []:
            if node.lower() in name or name in node.lower():
                return f"Couche « {layer['title']} »"
    return "Support transverse"


def _pv(project: str) -> Dict[str, str]:
    p = project.strip() or "la solution"
    return {"p": p, "P": p}


def plan_outline(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse le brief : détecte le domaine, choisit les sections et le style."""
    text = " ".join(str(brief.get(k) or "") for k in
                    ("title", "project", "context", "description", "industry", "solution", "tags"))
    pb_key = brief.get("playbook") if brief.get("playbook") in PLAYBOOKS else detect_playbook(text)
    pb = PLAYBOOKS[pb_key]
    wanted = brief.get("sections")
    if isinstance(wanted, list) and wanted:
        keys = [k for k in wanted if k in SECTION_BLUEPRINTS]
    else:
        keys = list(pb["sections"])
    used = set(keys)
    pool = [{"key": k, **SECTION_BLUEPRINTS[k]} for k in SECTION_BLUEPRINTS if k not in used][:8]
    palette = brief.get("palette") or random.Random(text).choice(list(PALETTES.keys()))
    typography = brief.get("typography") or ("serif-mix" if pb_key == "erp" else "manrope")
    return {
        "playbook": pb_key,
        "playbook_label": pb["label"],
        "sections": keys,
        "palette": palette if palette in PALETTES else "ocean",
        "typography": typography if typography in FONT_STACKS else "manrope",
        "outline": [{"key": k, **SECTION_BLUEPRINTS[k]} for k in keys],
        "pool": pool,
    }


def _stack(brief: Dict[str, Any], pb: Dict[str, Any]) -> List[str]:
    custom = brief.get("stack") or brief.get("technologies")
    if isinstance(custom, str):
        custom = [c.strip() for c in re.split(r"[,;/]", custom) if c.strip()]
    return (custom or pb["stack"])[:6]


def _arch_layers(brief: Dict[str, Any], pb: Dict[str, Any]) -> List[Dict[str, Any]]:
    if brief.get("architecture_layers"):
        return brief["architecture_layers"]
    stack = _stack(brief, pb)
    layers = [{"title": t, "nodes": n, "tone": tone} for t, n, tone in pb["architecture_layers"]]
    # injection de la stack réelle dans la couche centrale
    if stack:
        layers[2]["nodes"] = stack[:4]
    return layers


def _bullets_context(client: str, project: str, industry: str, pb_label: str) -> List[str]:
    ind = f" dans le secteur {industry}" if industry else ""
    return [
        f"Les processus actuels{ind} reposent sur des outils hétérogènes et des ressaisies manuelles.",
        "Les délais de traitement et le manque de visibilité limitent la qualité de service rendue aux utilisateurs.",
        "Les équipes métier attendent une solution fiable, disponible et simple d'usage au quotidien.",
        "Les exigences de sécurité et de traçabilité imposent un cadre de gouvernance formalisé.",
        f"Le programme {project} s'inscrit dans la trajectoire de modernisation engagée par {client}.",
    ]


def _paragraph_contexte(client: str, project: str, industry: str, brief: Dict[str, Any]) -> str:
    ctx = (brief.get("context") or "").strip()
    base = (f"{client} engage la transformation de son système d'information autour du programme "
            f"« {project} ». ")
    if ctx:
        base += ctx if ctx.endswith(".") else ctx + "."
    else:
        base += (f"Les dispositifs en place{(' dans le secteur ' + industry) if industry else ''} "
                 "ne couvrent plus les besoins actuels : les données sont dispersées, les traitements "
                 "sont partiellement manuels et la qualité de service dépend fortement de la "
                 "disponibilité des équipes. La direction a donc décidé de doter l'organisation "
                 "d'une plateforme cible répondant aux exigences de fiabilité, de sécurité et de "
                 "performance attendues.")
    return base


def _table_brief(brief: Dict[str, Any], pb: Dict[str, Any]) -> Dict[str, Any]:
    goals = brief.get("goals")
    if isinstance(goals, str):
        goals = [g.strip(" -•") for g in goals.splitlines() if g.strip()]
    goals = goals or [
        "Disposer d'une vue fiable et partagée de l'information",
        "Réduire les délais de traitement et les tâches manuelles",
        "Sécuriser les accès et tracer les opérations sensibles",
        "Industrialiser le déploiement et l'exploitation",
    ]
    rows = [[f"OBJ-{i + 1:02d}", g, "Inclus", "Mesuré en recette"] for i, g in enumerate(goals[:6])]
    return {"type": "table", "caption": "Matrice des objectifs et critères d'acceptation",
            "columns": ["Réf.", "Objectif", "Portée", "Vérification"], "rows": rows}


def compose_section(key: str, brief: Dict[str, Any], pb: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """Compose une section complète (intro + blocs) à partir du brief."""
    client = _titlecase_client(brief.get("client") or "")
    project = (brief.get("project") or brief.get("solution") or "la solution").strip()
    industry = (brief.get("industry") or "").strip()
    owner = (brief.get("author") or "").strip()
    bp = SECTION_BLUEPRINTS[key]
    section: Dict[str, Any] = {
        "id": new_id("sec"), "title": bp["title"], "kicker": bp["kicker"],
        "intro": bp["intro"], "icon": key, "page_break": True, "blocks": [],
    }
    B = section["blocks"]
    stack = _stack(brief, pb)
    layers = _arch_layers(brief, pb)

    if key == "contexte":
        B.append({"type": "paragraph", "lead": True, "text": _paragraph_contexte(client, project, industry, brief)})
        B.append({"type": "heading", "text": "Situation actuelle", "level": 2})
        B.append({"type": "paragraph", "text":
                  "L'audit mené lors du cadrage a mis en évidence plusieurs points de friction "
                  "structurants. Ils sont partagés avec les équipes métier et ont servi de base "
                  "à la construction du présent dossier."})
        B.append({"type": "bullets", "items": _bullets_context(client, project, industry, pb["label"])})
        B.append({"type": "heading", "text": "Enjeux de la transformation", "level": 2})
        B.append({"type": "bullets", "items": [
            "Enjeu de service : offrir un parcours fluide et homogène aux utilisateurs.",
            "Enjeu de performance : fiabiliser les traitements et réduire les délais.",
            "Enjeu de conformité : garantir la traçabilité et la protection des données.",
            "Enjeu de coûts : maîtriser les dépenses d'exploitation et le temps des équipes.",
        ]})
        B.append({"type": "callout", "tone": "info", "title": "Objectif du document",
                  "text": f"Ce document constitue le dossier de livraison de {project}. Il décrit la "
                          f"solution déployée, son architecture, ses conditions d'exploitation et les "
                          f"engagements de qualité associés. Il sert de référence contractuelle entre "
                          f"{client} et le prestataire."})

    elif key == "objectifs":
        B.append({"type": "paragraph", "text":
                  "Les objectifs ont été priorisés selon leur valeur métier et leur faisabilité "
                  "technique. Chacun est associé à un critère de vérification objectif."})
        B.append(_table_brief(brief, pb))
        B.append({"type": "heading", "text": "Indicateurs de succès", "level": 2})
        B.append({"type": "kpi", "items": [
            {"label": b, "value": v, "hint": "cible mesurée"}
            for b, v in contextual_kpis(brief, pb)
        ]})
        B.append({"type": "callout", "tone": "success", "title": "Critère d'acceptation global",
                  "text": "La livraison est réputée conforme lorsque l'ensemble des objectifs "
                          "OBJ-01 à OBJ-04 est vérifié en recette et qu'aucune anomalie bloquante "
                          "n'est ouverte."})

    elif key == "perimetre":
        B.append({"type": "paragraph", "text":
                  "Le périmètre ci-dessous a valeur contractuelle. Toute évolution fait l'objet "
                  "d'une demande de changement évaluée en comité de pilotage."})
        B.append({"type": "two_col",
                  "left": {"title": "Inclus dans le périmètre", "items": [
                      f"Conception et déploiement de {project}",
                      f"Intégration des {len(stack)} composants de la stack retenue",
                      "Documentation technique et fonctionnelle",
                      "Transfert de compétences et formation des référents",
                      "Garantie de bon fonctionnement (3 mois)",
                  ]},
                  "right": {"title": "Hors périmètre", "items": [
                      "Postes de travail et équipements utilisateurs",
                      "Licences tierces non mentionnées au budget",
                      "Reprise des historiques au-delà de la période convenue",
                      "Correctifs liés à des évolutions réglementaires postérieures",
                      "Exploitation courante après la garantie",
                  ]}})
        B.append({"type": "heading", "text": "Interfaces et dépendances externes", "level": 2})
        B.append({"type": "table", "caption": "Tableau — Dépendances identifiées",
                  "columns": ["Dépendance", "Fournisseur", "Impact"],
                  "rows": [[f"Connecteur {s}", "Éditeur / intégrateur", "Moyen"] for s in stack[:3]] +
                          [["Environnement réseau", "DSI", "Fort"], ["Accès aux données de référence", client, "Fort"]]})
        B.append({"type": "callout", "tone": "warning", "title": "Conditions de périmètre",
                  "text": "Toute inclusion non listée ci-dessus fera l'objet d'un avenant chiffré "
                          "avant exécution."})

    elif key == "architecture":
        B.append({"type": "paragraph", "text":
                  f"La solution repose sur une architecture en couches, pensée pour être robuste, "
                  f"observable et maintenable. Les briques retenues sont pour l'essentiel des "
                  f"standards du marché, afin de limiter la dépendance à un fournisseur unique."})
        B.append({"type": "architecture", "layers": layers,
                  "caption": "Schéma logique — vue des couches et des flux principaux"})
        B.append({"type": "heading", "text": "Choix techniques structurants", "level": 2})
        B.append({"type": "table", "caption": "Tableau — Composants et responsabilités",
                  "columns": ["Composant", "Rôle", "Criticité"],
                  "rows": [[comp, _role_for(comp, layers), "Haute" if i < 2 else "Moyenne"]
                           for i, comp in enumerate(stack)]})
        B.append({"type": "heading", "text": "Principes d'architecture", "level": 2})
        B.append({"type": "numbered", "items": [
            "Découplage des composants par des interfaces explicites et versionnées.",
            "Résilience par redondance des composants critiques et tests de bascule.",
            "Observabilité native : journaux, métriques et traces corrélés.",
            "Sécurité par défaut : moindre privilège, chiffrement et journalisation.",
            "Portabilité : conteneurisation des services pour éviter l'enfermement technologique.",
        ]})
        if owner:
            B.append({"type": "quote", "author": f"{owner}, pilote de l'architecture",
                      "text": "Chaque composant doit pouvoir être remplacé sans réécrire les autres : "
                              "c'est ce qui garantit la durée de vie de la plateforme."})

    elif key == "deploiement":
        B.append({"type": "paragraph", "text":
                  "Le déploiement suit un processus reproductible et traçable. Chaque environnement "
                  "est créé à partir du même code d'infrastructure, ce qui garantit l'homogénéité "
                  "entre recette et production."})
        B.append({"type": "kpi", "items": [
            {"label": "Environnements", "value": "3", "hint": "dev · recette · prod"},
            {"label": "Fréquence de déploiement", "value": "2/sem.", "hint": "zéro interruption"},
            {"label": "Temps de provisionnement", "value": "25 min", "hint": "100 % automatisé"},
            {"label": "Retour arrière", "value": "< 10 min", "hint": "procédure testée"},
        ]})
        B.append({"type": "heading", "text": "Étapes de mise en production", "level": 2})
        B.append({"type": "numbered", "items": pb["deployment_steps"]})
        B.append({"type": "heading", "text": "Pipeline d'intégration continue", "level": 2})
        B.append({"type": "code", "language": "bash", "text":
                  "# Étapes du pipeline exécutées à chaque livraison\n"
                  "1. lint & analyse statique\n"
                  "2. tests unitaires (seuil 80 %)\n"
                  "3. build de l'artefact versionné\n"
                  "4. déploiement en recette puis tests automatisés\n"
                  "5. validation manuelle (porte de qualité)\n"
                  "6. déploiement en production (canary 10 % → 100 %)"})
        B.append({"type": "callout", "tone": "info", "title": "Fenêtre de bascule",
                  "text": "La mise en production est planifiée hors heures ouvrées, avec une "
                          "cellule de crise mobilisée et un plan de retour arrière validé avant "
                          "toute opération."})

    elif key == "integrations":
        B.append({"type": "paragraph", "text":
                  "Les échanges sont formalisés par des contrats d'interface. Toute évolution "
                  "de contrat suit une procédure de versionnement compatible."})
        B.append({"type": "table", "caption": "Tableau — Inventaire des interfaces",
                  "columns": ["Interface", "Source", "Cible", "Fréquence"],
                  "rows": [["API Client", "Portail", "Référentiel", "Temps réel"],
                           ["Synchronisation produits", "ERP", "Plateforme", "15 min"],
                           ["Export reporting", "Plateforme", "Entrepôt", "Quotidien 02:00"],
                           ["Notifications", "Plateforme", "Messagerie", "Événementiel"]]})
        B.append({"type": "bullets", "items": [
            "Authentification mutuelle TLS et jetons à durée de vie courte.",
            "Idempotence garantie par clé de corrélation sur chaque message.",
            "Files d'attente de secours en cas d'indisponibilité du système cible.",
            "Journalisation systématique des appels et des rejets.",
        ]})

    elif key == "securite":
        B.append({"type": "paragraph", "text":
                  "La sécurité s'appuie sur le référentiel ISO 27001 et sur les exigences du RGPD. "
                  "Les mesures ci-dessous sont vérifiées lors de la recette et font l'objet d'un "
                  "suivi trimestriel en comité sécurité."})
        B.append({"type": "checklist", "items": [
            {"text": "Chiffrement des données au repos (AES-256) et en transit (TLS 1.3)", "done": True},
            {"text": "Authentification forte (MFA) et gestion des accès par rôle", "done": True},
            {"text": "Journalisation centralisée et conservation des traces 12 mois", "done": True},
            {"text": "Analyse d'impact relative à la protection des données (AIPD)", "done": False},
            {"text": "Test d'intrusion externe annuel par un prestataire qualifié", "done": False},
        ]})
        B.append({"type": "heading", "text": "Mesures de protection", "level": 2})
        B.append({"type": "bullets", "items": [
            "Cloisonnement des environnements et séparation des réseaux.",
            "Gestion des secrets centralisée, sans identifiant en clair dans le code.",
            "Sauvegardes chiffrées quotidiennes avec test de restauration semestriel.",
            "Politique de moindre privilège appliquée aux comptes techniques.",
        ]})
        B.append({"type": "callout", "tone": "warning", "title": "Réserve",
                  "text": "L'AIPD doit être finalisée et validée par le DPO avant l'ouverture des "
                          "données à de nouveaux profils utilisateurs."})
        B.append({"type": "signature", "parties": [
            {"role": "Responsable sécurité — client", "name": "", "place": "", "date": ""},
            {"role": "RSSI — prestataire", "name": "", "place": "", "date": ""}]})

    elif key == "donnees":
        B.append({"type": "paragraph", "text":
                  "Chaque jeu de données est documenté et rattaché à un propriétaire désigné. "
                  "Les règles ci-dessous s'appliquent à l'ensemble des flux, y compris les "
                  "reprises ponctuelles effectuées lors des bascules."})
        B.append({"type": "table", "caption": "Tableau — Jeux de données et règles de migration",
                  "columns": ["Jeu de données", "Volume", "Migration", "Contrôle"],
                  "rows": [["Clients", "8,4 M", "Chargement initial + delta", "Unicité et complétude"],
                           ["Contrats", "1,2 M", "Chargement initial", "Réconciliation comptable"],
                           ["Transactions", "310 M", "Historique 5 ans", "Somme de contrôle"],
                           ["Référentiels", "68 tables", "Reprise paramétrable", "Comparaison ligne à ligne"]]})
        B.append({"type": "heading", "text": "Règles de qualité", "level": 2})
        B.append({"type": "bullets", "items": [
            "Complétude : taux de renseignement supérieur à 98 % sur les champs obligatoires.",
            "Unicité : aucune duplication sur la clé métier après rapprochement.",
            "Cohérence : les valeurs de référence proviennent du référentiel unique.",
            "Fraîcheur : les données sont disponibles avant 06:00 chaque jour.",
        ]})
        B.append({"type": "callout", "tone": "success", "title": "Résultat",
                  "text": "Les contrôles automatiques ont permis de réduire les anomalies de "
                          "chargement de 87 % entre la première et la dernière itération."})

    elif key == "tests":
        B.append({"type": "paragraph", "text":
                  "La stratégie de tests couvre l'ensemble des niveaux, de l'unitaire à "
                  "l'acceptation métier. Les résultats sont consignés dans le procès-verbal de "
                  "recette annexé."})
        B.append({"type": "checklist", "items": [{"text": t, "done": i < 2} for i, t in enumerate(pb["tests"])]})
        B.append({"type": "table", "caption": "Tableau — Campagne de recette",
                  "columns": ["Niveau", "Responsable", "Nombre de cas", "Résultat"],
                  "rows": [["Unitaire", "Équipe de développement", "412", "100 %"],
                           ["Intégration", "Équipe projet", "86", "98 %"],
                           ["Performance", "Équipe technique", "12", "Conforme"],
                           ["Acceptation métier", "Représentants métier", "57", "En cours"]]})
        B.append({"type": "callout", "tone": "info", "title": "Critère de réception",
                  "text": "La recette est prononcée lorsque 100 % des cas bloquants et au moins "
                          "95 % des cas majeurs sont validés."})

    elif key == "exploitation":
        B.append({"type": "paragraph", "text":
                  "L'exploitation s'appuie sur une supervision continue et des engagements de "
                  "service mesurés. Le dispositif est transféré aux équipes de production avec "
                  "la documentation d'exploitation."})
        B.append({"type": "table", "caption": "Tableau — Engagements de service",
                  "columns": ["Indicateur", "Cible", "Mesure"],
                  "rows": [["Disponibilité mensuelle", "99,9 %", "Sonde externe toutes les minutes"],
                           ["Prise en charge incident P1", "15 min", "Astreinte 24/7"],
                           ["Résolution incident P2", "4 h", "Suivi ITSM"],
                           ["Restauration après sinistre", "RTO 4 h / RPO 1 h", "Test semestriel"]]})
        B.append({"type": "heading", "text": "Supervision mise en place", "level": 2})
        B.append({"type": "bullets", "items": [
            "Tableau de bord unique des indicateurs techniques et métier.",
            "Alertes graduées avec astreinte et escalade automatisée.",
            "Revue mensuelle des incidents et des actions correctives.",
            "Base de connaissances alimentée à chaque résolution.",
        ]})
        B.append({"type": "timeline", "items": [
            {"when": "J+0", "title": "Mise en production", "text": "Bascule et surveillance renforcée.", "status": "done"},
            {"when": "J+30", "title": "Fin d'hypercare", "text": "Stabilisation et transfert aux équipes.", "status": "in_progress"},
            {"when": "M+3", "title": "Revue de service", "text": "Bilan des engagements et plan d'amélioration.", "status": "planned"},
        ]})

    elif key == "planning":
        weeks = int(brief.get("weeks") or 18)
        q = max(1, weeks // 4)
        B.append({"type": "paragraph", "text":
                  f"Le planning prévisionnel s'étend sur {weeks} semaines, organisées en {q} "
                  f"lots livrables. Chaque lot fait l'objet d'une démonstration et d'une "
                  f"validation formelle."})
        B.append({"type": "timeline", "items": [
            {"when": "S1 – S3", "title": "Cadrage & conception détaillée", "text": "Ateliers, dossier d'architecture, plan de recette.", "status": "done"},
            {"when": f"S4 – S{max(4, weeks // 2)}", "title": "Réalisation — lot 1", "text": "Développement, tests unitaires, démonstration.", "status": "in_progress"},
            {"when": f"S{max(5, weeks // 2 + 1)} – S{weeks - 3}", "title": "Réalisation — lot 2", "text": "Intégrations, performances, documentation.", "status": "planned"},
            {"when": f"S{weeks - 2} – S{weeks}", "title": "Recette & mise en production", "text": "UAT, correction, bascule et hypercare.", "status": "planned"},
        ]})
        B.append({"type": "table", "caption": "Tableau — Jalons contractuels",
                  "columns": ["Jalon", "Échéance", "Livrable associé"],
                  "rows": [["J1 — Validation du dossier de conception", f"S{max(2, weeks // 6)}", "Dossier d'architecture"],
                           ["J2 — Validation du lot 1", f"S{max(4, weeks // 2)}", "Version en recette"],
                           ["J3 — Recette prononcée", f"S{weeks - 2}", "PV de recette"],
                           ["J4 — Mise en production", f"S{weeks}", "Note de mise en service"]]})
        B.append({"type": "callout", "tone": "info", "title": "Gouvernance",
                  "text": "Comité de projet hebdomadaire, comité de pilotage mensuel et "
                          "revue de risques à chaque jalon."})

    elif key == "budget":
        B.append({"type": "paragraph", "text":
                  "Le budget est présenté par lot, en charge prévisionnelle. Les hypothèses de "
                  "chiffrage sont explicitées afin de faciliter les arbitrages."})
        rows = [["Lot 1 — Cadrage", "Conception", "12 %", "Inclus"],
                ["Lot 2 — Réalisation", "Développement & tests", "48 %", "Inclus"],
                ["Lot 3 — Intégration", "Interfaces & données", "22 %", "Inclus"],
                ["Lot 4 — Mise en service", "Recette & bascule", "12 %", "Inclus"],
                ["Garantie", "Support 3 mois", "6 %", "Inclus"]]
        B.append({"type": "table", "caption": "Tableau — Répartition prévisionnelle",
                  "columns": ["Lot", "Nature", "Part", "Statut"], "rows": rows})
        B.append({"type": "kpi", "items": [
            {"label": "Charge prestataire", "value": f"{weeks_charge(brief)} j", "hint": "jours-homme"},
            {"label": "Charge client", "value": f"{max(10, weeks_charge(brief) // 3)} j", "hint": "disponibilité métier"},
            {"label": "Contingence", "value": "10 %", "hint": "aléas"},
            {"label": "Valorisation", "value": "Lot 1 inclus", "hint": "cf. devis"},
        ]})
        B.append({"type": "callout", "tone": "warning", "title": "Hypothèses de chiffrage",
                  "text": "Le chiffrage suppose la disponibilité des experts métier selon le plan "
                          "de charge convenu. Tout retard imputable au client pourra faire l'objet "
                          "d'un ajustement."})

    elif key == "risques":
        B.append({"type": "paragraph", "text":
                  "Les risques sont évalués selon leur probabilité et leur impact. Un plan de "
                  "mitigation est associé à chacun et suivi en comité de projet."})
        risk_rows = [[r[0], r[1], r[2]] for r in (brief.get("risks") or _contextual_risks(brief, pb))]
        B.append({"type": "table", "caption": "Tableau — Registre des risques",
                  "columns": ["Risque", "Criticité", "Mesure de mitigation"], "rows": risk_rows})
        B.append({"type": "heading", "text": "Dispositif de suivi", "level": 2})
        B.append({"type": "bullets", "items": [
            "Revue mensuelle du registre en comité de pilotage.",
            "Escalade immédiate des risques de criticité haute.",
            "Mise à jour documentée à chaque changement de phase.",
        ]})
        B.append({"type": "callout", "tone": "danger", "title": "Risque bloquant identifié",
                  "text": "L'indisponibilité prolongée des experts métier au moment de la recette "
                          "constituerait un risque majeur pour le respect du jalon J3."})

    elif key == "resultats":
        B.append({"type": "paragraph", "text":
                  "Les bénéfices sont mesurés à partir des indicateurs définis en phase de "
                  "cadrage. Le relevé ci-dessous correspond aux valeurs constatées en fin de "
                  "déploiement."})
        B.append({"type": "kpi", "items": [
            {"label": lbl, "value": val, "hint": "constaté"} for lbl, val in contextual_kpis(brief, pb)]})
        B.append({"type": "heading", "text": "Témoignages utilisateurs", "level": 2})
        B.append({"type": "quote",
                  "text": "L'outil nous fait gagner un temps considérable : ce qui prenait "
                          "plusieurs jours est désormais disponible en quelques minutes.",
                  "author": "Utilisateur clé — " + client})
        B.append({"type": "bullets", "items": [
            "Adoption mesurée à 89 % des utilisateurs cibles après 30 jours.",
            "Satisfaction moyenne de 4,4 / 5 sur les indicateurs de service.",
            "Réduction mesurable des tâches manuelles récurrentes.",
        ]})

    elif key == "annexes":
        B.append({"type": "paragraph", "text":
                  "Les documents de référence suivants complètent le présent dossier et sont "
                  "archivés dans l'espace projet."})
        B.append({"type": "table", "caption": "Tableau — Documents associés",
                  "columns": ["Référence", "Document", "Version"],
                  "rows": [["ANN-01", "Dossier d'architecture détaillé", "1.4"],
                           ["ANN-02", "Plan de recette et PV", "1.0"],
                           ["ANN-03", "Documentation d'exploitation", "2.1"],
                           ["ANN-04", "Registre des traitements RGPD", "1.2"]]})
        B.append({"type": "heading", "text": "Glossaire", "level": 2})
        B.append({"type": "table", "caption": "",
                  "columns": ["Terme", "Définition"],
                  "rows": [["PRA", "Plan de reprise d'activité : procédures de redémarrage après sinistre."],
                           ["RTO / RPO", "Délai maximal d'interruption / perte de données acceptable."],
                           ["UAT", "User Acceptance Testing : recette par les utilisateurs."],
                           ["SLA", "Service Level Agreement : engagement de niveau de service."]]})

    return section


def weeks_charge(brief: Dict[str, Any]) -> int:
    return max(30, int(round((int(brief.get("weeks") or 18) * 4.5))))


def _norm_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [v.strip(" -•") for v in value.splitlines() if v.strip()]
    return []


# --------------------------------------------------------------------------- #
#  API de génération                                                          #
# --------------------------------------------------------------------------- #
def generate(brief: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Génère un livrable complet à partir d'un brief libre."""
    brief = dict(brief or {})
    brief["title"] = (brief.get("title") or brief.get("project") or "Document de livraison").strip()
    brief["client"] = (brief.get("client") or "").strip()
    brief["project"] = (brief.get("project") or brief.get("title") or "").strip()

    plan = plan_outline(brief)
    pb = PLAYBOOKS[plan["playbook"]]
    provider = build_provider(settings)

    sections = [compose_section(k, brief, pb, i + 1) for i, k in enumerate(plan["sections"])]

    # Enrichissement LLM optionnel, section par section (best effort)
    if provider.available and brief.get("use_llm", True):
        sections = _enrich_with_llm(sections, brief, provider)

    meta = {
        "title": brief["title"],
        "subtitle": brief.get("subtitle") or (f"{plan['playbook_label']} — {brief['project']}" if brief["project"] else ""),
        "client": brief["client"],
        "project": brief["project"],
        "reference": brief.get("reference") or f"LIV-{date.today().year}-{random.randint(1000, 9999)}",
        "version": brief.get("version") or "1.0",
        "date": brief.get("date") or today_fr(),
        "author": brief.get("author") or "",
        "author_role": brief.get("author_role") or "",
        "author_email": brief.get("author_email") or "",
        "recipient": brief.get("recipient") or "",
        "confidentiality": brief.get("confidentiality") or "Confidentiel",
        "industry": brief.get("industry") or "",
        "tags": _norm_list(brief.get("tags"))[:4] or _stack(brief, pb)[:3],
        "executive_summary": brief.get("executive_summary") or _summary(brief, plan, pb),
    }
    doc = normalize({
        "meta": meta,
        "style": {
            "palette": plan["palette"],
            "typography": plan["typography"],
            "density": brief.get("density") or "normal",
            "paper": brief.get("paper") or "A4",
        },
        "options": {**DEFAULT_OPTIONS,
                    "watermark": brief.get("watermark") or "",
                    "tone": brief.get("tone") or "professionnel"},
        "sections": sections,
        "brand": brief.get("brand") or {},
    })
    doc["meta"]["playbook"] = plan["playbook"]
    doc["meta"]["playbook_label"] = plan["playbook_label"]
    doc["meta"]["generated_by"] = provider.name if provider.available else "local"
    return doc


def _summary(brief: Dict[str, Any], plan: Dict[str, Any], pb: Dict[str, Any]) -> str:
    client = _titlecase_client(brief.get("client") or "")
    project = brief.get("project") or brief.get("title") or "la solution"
    industry = brief.get("industry") or ""
    tone = MOOD_TONES.get(brief.get("tone") or "professionnel", MOOD_TONES["professionnel"])
    titles = ", ".join(s["title"].lower() for s in plan["outline"][:5])
    parts = [
        f"Le présent dossier documente la livraison de {project} pour {client}"
        + (f", acteur du secteur {industry}" if industry else "") + ".",
        f"Il présente le contexte, les objectifs retenus, l'architecture de la solution, "
        f"les conditions de déploiement et les engagements de qualité associés.",
        f"Le document couvre notamment : {titles}.",
        f"Rédigé dans un registre {tone}, il constitue le référentiel de référence pour la "
        f"recette et l'exploitation de la solution.",
    ]
    if brief.get("executive_summary"):
        return brief["executive_summary"]
    return " ".join(parts)


def _enrich_with_llm(sections: List[Dict[str, Any]], brief: Dict[str, Any],
                     provider: LLMProvider) -> List[Dict[str, Any]]:
    """Réécrit les paragraphes avec le LLM ; conserve la structure générée."""
    system = (
        "Tu es un architecte solutions senior qui rédige des dossiers de livraison "
        "professionnels en français. Ton style est précis, factuel, sans emphase "
        "commerciale excessive. Tu réponds uniquement en JSON valide."
    )
    context = json.dumps({k: brief.get(k) for k in
                          ("title", "client", "project", "industry", "context", "goals", "stack", "tone")},
                         ensure_ascii=False)
    for sec in sections:
        block = next((b for b in sec["blocks"] if b["type"] == "paragraph"), None)
        if not block:
            continue
        prompt = (
            f"Contexte du projet : {context}\n"
            f"Section : {sec['title']} — {sec['kicker']}\n"
            f"Paragraphe actuel : {block.get('text', '')[:900]}\n\n"
            "Réécris ce paragraphe (120 à 180 mots) en français professionnel, sans titres, "
            "sans listes. Réponds au format {\"text\": \"...\"}."
        )
        raw = provider.complete(system, prompt, max_tokens=700)
        if not raw:
            continue
        try:
            match = re.search(r"\{.*\}", raw, flags=re.S)
            data = json.loads(match.group(0) if match else raw)
            text = (data.get("text") or "").strip()
            if len(text) > 120:
                block["text"] = text
                sec["ai_written"] = True
        except (json.JSONDecodeError, AttributeError):
            continue
    return sections


def suggest_titles(brief: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> List[str]:
    """Propositions de titres de livrable (local + LLM si disponible)."""
    client = (brief.get("client") or "").strip()
    project = (brief.get("project") or brief.get("solution") or "").strip()
    plan = plan_outline(brief)
    base = [
        f"Dossier de livraison — {project or 'Solution'}",
        f"Documentation de solution — {client or 'Client'}",
        f"Rapport de déploiement — {project or 'Projet'}",
        f"Dossier d'architecture et d'exploitation — {project or 'Solution'}",
        f"Note de synthèse de livraison — {client or 'Client'}",
    ]
    provider = build_provider(settings)
    if provider.available:
        raw = provider.complete(
            "Tu proposes des titres de documents professionnels, en français.",
            f"Propose 5 titres de dossiers de livraison pour : {json.dumps(brief, ensure_ascii=False)[:1200]}. "
            'Réponds en JSON {"titles": ["..."]}.', max_tokens=400)
        if raw:
            try:
                data = json.loads(re.search(r"\{.*\}", raw, flags=re.S).group(0))
                titles = [t for t in data.get("titles", []) if isinstance(t, str)]
                if titles:
                    return titles[:5]
            except Exception:
                pass
    return base
