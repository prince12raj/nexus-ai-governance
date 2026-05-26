"""
rag/regulations_seed.py — Curated regulatory knowledge base for Nexus AI Governance Platform.

Contains the full REGULATIONS_CORPUS — seeded into the vector store on startup.
Add new entries here to extend coverage across all frameworks.

Frameworks covered:
  - GDPR      (EU General Data Protection Regulation)
  - ISO 27001 (Information Security Management)
  - HIPAA     (Health Insurance Portability and Accountability Act)
  - SOC 2     (System and Organisation Controls)
  - PCI-DSS   (Payment Card Industry Data Security Standard)
"""
from __future__ import annotations

from typing import Any, Dict, List

REGULATIONS_CORPUS: List[Dict[str, Any]] = [

    # ══════════════════════════════════════════════════════════════════════════
    # GDPR
    # ══════════════════════════════════════════════════════════════════════════

    {
        "id": "gdpr-art5",
        "title": "GDPR Article 5 — Data Minimisation & Retention",
        "framework": "GDPR",
        "citation": "Regulation (EU) 2016/679, Article 5",
        "severity": "Critical",
        "tags": ["data-minimisation", "retention", "purpose-limitation", "storage-limitation"],
        "text": (
            "Personal data shall be: collected for specified, explicit and legitimate purposes "
            "and not further processed in a manner that is incompatible with those purposes; "
            "adequate, relevant and limited to what is necessary in relation to the purposes "
            "for which they are processed ('data minimisation'); kept in a form which permits "
            "identification of data subjects for no longer than is necessary for the purposes "
            "for which the personal data are processed ('storage limitation'). "
            "Violations can result in fines up to €20 million or 4% of annual global turnover."
        ),
        "remediation": [
            "Implement documented data retention schedules",
            "Conduct data minimisation audits quarterly",
            "Document legal basis for each data processing category",
            "Automate data deletion at end of retention period",
        ],
    },
    {
        "id": "gdpr-art17",
        "title": "GDPR Article 17 — Right to Erasure (Right to be Forgotten)",
        "framework": "GDPR",
        "citation": "Regulation (EU) 2016/679, Article 17",
        "severity": "Critical",
        "tags": ["erasure", "right-to-forget", "deletion", "subject-rights"],
        "text": (
            "The data subject shall have the right to obtain from the controller the erasure "
            "of personal data concerning him or her without undue delay. The controller shall "
            "have the obligation to erase personal data without undue delay where the personal "
            "data are no longer necessary in relation to the purposes for which they were collected "
            "or otherwise processed. Erasure requests must be fulfilled within 30 calendar days. "
            "Refusal must be documented with legal justification."
        ),
        "remediation": [
            "Build automated erasure request workflows",
            "Maintain deletion audit trails with timestamps",
            "Implement 30-day SLA tracking for all erasure requests",
            "Propagate deletion to all downstream processors and backups",
        ],
    },
    {
        "id": "gdpr-art25",
        "title": "GDPR Article 25 — Privacy by Design and by Default",
        "framework": "GDPR",
        "citation": "Regulation (EU) 2016/679, Article 25",
        "severity": "High",
        "tags": ["privacy-by-design", "default-settings", "engineering", "technical-measures"],
        "text": (
            "The controller shall implement appropriate technical and organisational measures "
            "designed to implement data-protection principles in an effective manner. "
            "Privacy-by-default requires that only personal data necessary for each specific "
            "purpose is processed. This applies to the amount of data collected, the extent of "
            "processing, the period of storage, and accessibility. Systems must be designed with "
            "privacy as a default state, not an add-on."
        ),
        "remediation": [
            "Embed privacy reviews in the SDLC process",
            "Conduct Data Protection Impact Assessments (DPIAs) for high-risk processing",
            "Default all new features to the most privacy-protective settings",
            "Use data anonymisation and pseudonymisation by default",
        ],
    },
    {
        "id": "gdpr-art7",
        "title": "GDPR Article 7 — Conditions for Consent",
        "framework": "GDPR",
        "citation": "Regulation (EU) 2016/679, Article 7",
        "severity": "Critical",
        "tags": ["consent", "opt-in", "withdrawal", "freely-given"],
        "text": (
            "Where processing is based on consent, the controller shall be able to demonstrate "
            "that the data subject has consented to processing of his or her personal data. "
            "Consent must be freely given, specific, informed, and unambiguous. Pre-ticked boxes "
            "or silence does not constitute valid consent. The data subject shall have the right "
            "to withdraw consent at any time without detriment. Consent given as a condition of "
            "service is not valid under GDPR."
        ),
        "remediation": [
            "Implement explicit opt-in consent capture with clear language",
            "Build one-click consent withdrawal functionality",
            "Maintain timestamped consent audit logs",
            "Separate consent for each distinct processing purpose",
        ],
    },
    {
        "id": "gdpr-art32",
        "title": "GDPR Article 32 — Security of Processing",
        "framework": "GDPR",
        "citation": "Regulation (EU) 2016/679, Article 32",
        "severity": "Critical",
        "tags": ["encryption", "security", "technical-measures", "pseudonymisation"],
        "text": (
            "The controller and processor shall implement appropriate technical and organisational "
            "measures to ensure a level of security appropriate to the risk, including: "
            "pseudonymisation and encryption of personal data; ability to ensure ongoing "
            "confidentiality, integrity, availability and resilience of processing systems; "
            "ability to restore access to personal data in a timely manner in the event of a "
            "physical or technical incident; regular testing and evaluation of technical and "
            "organisational security measures. Encryption at rest and in transit is required."
        ),
        "remediation": [
            "Encrypt all personal data at rest (AES-256) and in transit (TLS 1.3)",
            "Implement pseudonymisation for datasets used in analytics",
            "Establish and test business continuity and disaster recovery plans",
            "Conduct annual penetration testing and security audits",
        ],
    },
    {
        "id": "gdpr-art33",
        "title": "GDPR Article 33 — Data Breach Notification",
        "framework": "GDPR",
        "citation": "Regulation (EU) 2016/679, Article 33",
        "severity": "Critical",
        "tags": ["breach", "notification", "72-hours", "incident-response"],
        "text": (
            "In the case of a personal data breach, the controller shall notify the competent "
            "supervisory authority within 72 hours of becoming aware of it. The notification "
            "must include: the nature of the breach, categories and approximate number of data "
            "subjects and records concerned, likely consequences, and measures taken or proposed. "
            "If notification is not made within 72 hours, a reasoned justification must accompany it."
        ),
        "remediation": [
            "Implement automated breach detection and alerting",
            "Create a breach response playbook with 72-hour workflow",
            "Designate a Data Protection Officer (DPO) or breach coordinator",
            "Maintain a breach register with all incidents and outcomes",
        ],
    },
    {
        "id": "gdpr-art13",
        "title": "GDPR Article 13 — Transparency and Privacy Notices",
        "framework": "GDPR",
        "citation": "Regulation (EU) 2016/679, Article 13",
        "severity": "High",
        "tags": ["transparency", "privacy-notice", "information", "lawful-basis"],
        "text": (
            "Where personal data are collected from the data subject, the controller shall "
            "provide information including: the identity of the controller, the purposes and "
            "legal basis for processing, legitimate interests pursued, recipients of data, "
            "retention periods, and the existence of data subject rights. Information must be "
            "provided in a concise, transparent, intelligible, and easily accessible form using "
            "clear and plain language at the time of collection."
        ),
        "remediation": [
            "Audit and update all privacy notices to include required GDPR elements",
            "Ensure privacy notices are written in plain language",
            "Display notices at point of data collection",
            "Review and update notices annually or when processing changes",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ISO 27001
    # ══════════════════════════════════════════════════════════════════════════

    {
        "id": "iso-a9",
        "title": "ISO 27001 A.9 — Access Control",
        "framework": "ISO 27001",
        "citation": "ISO/IEC 27001:2022, Annex A, Control 9",
        "severity": "Critical",
        "tags": ["access-control", "rbac", "least-privilege", "user-management"],
        "text": (
            "Access to information and information processing facilities shall be restricted "
            "in accordance with the access control policy. Users shall only be provided with "
            "access to information and systems they require for their role (least privilege). "
            "Access rights shall be reviewed at regular intervals (minimum quarterly). "
            "Privileged access rights must be allocated separately and reviewed more frequently. "
            "All access provisioning must follow a formal approval process."
        ),
        "remediation": [
            "Implement role-based access control (RBAC)",
            "Conduct quarterly access rights reviews",
            "Remove access within 24 hours of employee departure",
            "Maintain a privileged access register",
        ],
    },
    {
        "id": "iso-a943",
        "title": "ISO 27001 A.9.4.3 — Password Management System",
        "framework": "ISO 27001",
        "citation": "ISO/IEC 27001:2022, Annex A, Control 9.4.3",
        "severity": "High",
        "tags": ["password", "authentication", "mfa", "credentials"],
        "text": (
            "Password management systems shall be interactive and ensure quality passwords. "
            "Requirements: minimum 12 characters, complexity (upper, lower, digits, symbols), "
            "prohibition of last 12 passwords reuse, maximum 90-day expiry for privileged accounts, "
            "account lockout after 5 failed attempts. Passwords must never be stored in plaintext. "
            "Approved hashing: bcrypt, Argon2, or PBKDF2 with appropriate work factors. "
            "MFA is mandatory for all remote access and privileged accounts."
        ),
        "remediation": [
            "Deploy enterprise password manager",
            "Enforce MFA for all privileged and remote access",
            "Implement password strength validators at input",
            "Migrate all passwords to bcrypt or Argon2 hashing",
        ],
    },
    {
        "id": "iso-a12",
        "title": "ISO 27001 A.12 — Operations Security: Logging & Monitoring",
        "framework": "ISO 27001",
        "citation": "ISO/IEC 27001:2022, Annex A, Control 12.4",
        "severity": "High",
        "tags": ["logging", "monitoring", "audit-trail", "siem", "events"],
        "text": (
            "Event logs recording user activities, exceptions, faults, and information security "
            "events shall be produced, kept and regularly reviewed. Logs must capture: timestamp, "
            "user ID, event type, affected system, source IP, and outcome. "
            "Log retention: minimum 12 months with 3 months hot storage. "
            "Unauthorized access or modification of logs is strictly prohibited. "
            "SIEM integration required for real-time threat detection and alerting."
        ),
        "remediation": [
            "Deploy centralised SIEM solution (e.g. Splunk, Elastic SIEM)",
            "Set log retention policy to 12+ months",
            "Implement log integrity verification (hash chaining)",
            "Configure real-time alerting for critical security events",
        ],
    },
    {
        "id": "iso-a8",
        "title": "ISO 27001 A.8 — Information Asset Management",
        "framework": "ISO 27001",
        "citation": "ISO/IEC 27001:2022, Annex A, Control 8.1",
        "severity": "Medium",
        "tags": ["asset-management", "inventory", "classification", "data-owner"],
        "text": (
            "All information assets associated with information processing shall be identified "
            "and an inventory drawn up and maintained. Assets must be classified "
            "(Public, Internal, Confidential, Restricted), assigned an owner, and have documented "
            "handling procedures per classification level. Asset inventory must be reviewed "
            "and updated annually. Data owners are accountable for appropriate protection."
        ),
        "remediation": [
            "Build and maintain comprehensive information asset inventory",
            "Assign data owners to each asset and classification category",
            "Implement data classification labels in documents and systems",
            "Schedule annual asset audits with owner sign-off",
        ],
    },
    {
        "id": "iso-a6",
        "title": "ISO 27001 A.6 — Organisation of Information Security",
        "framework": "ISO 27001",
        "citation": "ISO/IEC 27001:2022, Annex A, Control 6.1",
        "severity": "Medium",
        "tags": ["governance", "roles", "responsibilities", "segregation-of-duties"],
        "text": (
            "All information security responsibilities shall be defined and allocated. "
            "Segregation of duties must be implemented to reduce opportunities for unauthorised "
            "or unintentional modification or misuse of assets. Conflicts of interest must be "
            "identified and managed. A named CISO or equivalent must be appointed and report "
            "to senior management. Security must be integrated into project management."
        ),
        "remediation": [
            "Document and publish information security roles and responsibilities",
            "Implement segregation of duties in critical processes",
            "Appoint a named CISO or Information Security Manager",
            "Include security reviews in all project lifecycle stages",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # HIPAA
    # ══════════════════════════════════════════════════════════════════════════

    {
        "id": "hipaa-security",
        "title": "HIPAA Security Rule — Technical Safeguards",
        "framework": "HIPAA",
        "citation": "45 CFR §164.312",
        "severity": "Critical",
        "tags": ["phi", "ephi", "encryption", "access-control", "healthcare", "technical-safeguards"],
        "text": (
            "Covered entities must implement technical security measures to guard against "
            "unauthorised access to ePHI transmitted over electronic communications networks. "
            "Required controls: unique user identification, emergency access procedures, "
            "automatic logoff after inactivity, encryption and decryption of ePHI, "
            "audit controls to record access, and integrity controls to prevent improper alteration. "
            "All ePHI must be encrypted at rest (AES-256) and in transit (TLS 1.2+)."
        ),
        "remediation": [
            "Encrypt all ePHI at rest using AES-256",
            "Enforce TLS 1.2+ for all ePHI data in transit",
            "Implement automatic session timeouts (max 15 minutes)",
            "Deploy access logging and audit trail systems for all ePHI access",
        ],
    },
    {
        "id": "hipaa-access",
        "title": "HIPAA — Minimum Necessary Standard",
        "framework": "HIPAA",
        "citation": "45 CFR §164.502(b)",
        "severity": "High",
        "tags": ["minimum-necessary", "phi", "access-control", "least-privilege"],
        "text": (
            "Covered entities must make reasonable efforts to limit PHI to the minimum necessary "
            "to accomplish the intended purpose. This applies to all uses, disclosures, and requests. "
            "Role-based access controls must ensure staff can only access PHI required for their "
            "specific job functions. Bulk exports of PHI must be approved and logged. "
            "Access to entire patient records must be justified and audited."
        ),
        "remediation": [
            "Implement granular role-based access control for all PHI systems",
            "Audit user PHI access permissions quarterly",
            "Require documented justification for bulk PHI exports",
            "Log and review all PHI access in real time",
        ],
    },
    {
        "id": "hipaa-baa",
        "title": "HIPAA — Business Associate Agreements",
        "framework": "HIPAA",
        "citation": "45 CFR §164.308(b)",
        "severity": "Critical",
        "tags": ["baa", "vendor", "business-associate", "third-party"],
        "text": (
            "A covered entity may permit a business associate to create, receive, maintain, or "
            "transmit ePHI only if a Business Associate Agreement (BAA) is in place. "
            "The BAA must specify: permitted uses of PHI, requirement to implement safeguards, "
            "obligation to report breaches, and requirement to return or destroy PHI at termination. "
            "Sharing PHI with any vendor without a signed BAA is a direct HIPAA violation."
        ),
        "remediation": [
            "Audit all vendors who process, store, or transmit PHI",
            "Execute BAAs with all identified Business Associates before sharing PHI",
            "Add BAA requirement to vendor onboarding and procurement checklist",
            "Review BAAs annually and upon any material vendor changes",
        ],
    },
    {
        "id": "hipaa-privacy",
        "title": "HIPAA Privacy Rule — Patient Rights",
        "framework": "HIPAA",
        "citation": "45 CFR §164.524",
        "severity": "High",
        "tags": ["patient-rights", "access", "amendment", "accounting-disclosures"],
        "text": (
            "Patients have the right to access their PHI held by covered entities within 30 days "
            "of request (max 60 days with one extension). Covered entities must provide PHI in the "
            "format requested by the patient where possible. Patients may request amendments to "
            "their records. Covered entities must provide an accounting of disclosures of PHI "
            "made for purposes other than treatment, payment, or operations upon patient request."
        ),
        "remediation": [
            "Implement patient portal with self-service PHI access",
            "Build 30-day SLA workflow for access and amendment requests",
            "Maintain a disclosure log to support accounting requests",
            "Train staff on patient rights and request handling procedures",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SOC 2
    # ══════════════════════════════════════════════════════════════════════════

    {
        "id": "soc2-security",
        "title": "SOC 2 — Security Trust Service Criteria (CC6, CC7)",
        "framework": "SOC 2",
        "citation": "AICPA TSC CC6, CC7",
        "severity": "High",
        "tags": ["soc2", "security", "logical-access", "encryption", "vulnerability-management"],
        "text": (
            "The entity implements logical access security over protected information assets. "
            "Required controls: logical access restrictions with MFA, encryption of data at "
            "rest and in transit, vulnerability scanning (minimum quarterly), annual penetration "
            "testing, documented security incident response procedures, and formal change management. "
            "Security incidents must be logged, investigated, and reported to management. "
            "Vendors with system access must be assessed annually."
        ),
        "remediation": [
            "Deploy WAF and DDoS protection on all public-facing systems",
            "Conduct quarterly vulnerability scans with remediation SLAs",
            "Establish formal incident response playbooks with defined escalation paths",
            "Implement formal change management with approval workflows",
        ],
    },
    {
        "id": "soc2-availability",
        "title": "SOC 2 — Availability Trust Service Criteria (A1)",
        "framework": "SOC 2",
        "citation": "AICPA TSC A1",
        "severity": "Medium",
        "tags": ["soc2", "availability", "uptime", "disaster-recovery", "rto", "rpo"],
        "text": (
            "System availability for operation and use must meet committed or agreed SLAs. "
            "Requirements: documented availability commitments communicated to users, "
            "capacity planning and monitoring, backup and recovery procedures with defined "
            "RTO and RPO targets, environmental controls, and regular DR testing. "
            "RTO and RPO targets must be tested annually and results documented. "
            "Significant availability events must be communicated to affected users."
        ),
        "remediation": [
            "Define RTO/RPO targets and document in BCP",
            "Test disaster recovery plans at least annually",
            "Implement automated infrastructure monitoring with alerting",
            "Deploy multi-region or multi-zone redundancy for critical systems",
        ],
    },
    {
        "id": "soc2-confidentiality",
        "title": "SOC 2 — Confidentiality Trust Service Criteria (C1)",
        "framework": "SOC 2",
        "citation": "AICPA TSC C1",
        "severity": "High",
        "tags": ["soc2", "confidentiality", "data-classification", "nda", "disposal"],
        "text": (
            "Information designated as confidential is protected as committed or agreed. "
            "Controls required: data classification policy, NDAs with employees and contractors, "
            "encryption of confidential data, secure disposal of media and records, "
            "DLP (Data Loss Prevention) controls on endpoints, and restrictions on confidential "
            "data leaving the controlled environment. Annual review of confidential data inventory required."
        ),
        "remediation": [
            "Implement and enforce data classification policy",
            "Deploy DLP solutions on all endpoints and email systems",
            "Establish secure media disposal procedures (NIST 800-88)",
            "Ensure all employees sign NDAs covering confidential information",
        ],
    },
    {
        "id": "soc2-privacy",
        "title": "SOC 2 — Privacy Trust Service Criteria (P1–P8)",
        "framework": "SOC 2",
        "citation": "AICPA TSC P1–P8",
        "severity": "High",
        "tags": ["soc2", "privacy", "consent", "notice", "personal-information"],
        "text": (
            "Personal information is collected, used, retained, disclosed, and disposed of in "
            "conformity with the entity's commitments. Requirements: privacy notice provided at "
            "collection, consent obtained where required, data quality maintained, data subject "
            "access and correction rights supported, personal information retained only as long "
            "as necessary, and proper disposal procedures. Annual privacy risk assessments required."
        ),
        "remediation": [
            "Publish and maintain a comprehensive privacy notice",
            "Implement data subject rights handling workflows",
            "Conduct annual privacy risk assessments",
            "Document and enforce personal information retention and disposal schedules",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PCI-DSS
    # ══════════════════════════════════════════════════════════════════════════

    {
        "id": "pci-req3",
        "title": "PCI DSS Requirement 3 — Protect Stored Account Data",
        "framework": "PCI-DSS",
        "citation": "PCI DSS v4.0, Requirement 3",
        "severity": "Critical",
        "tags": ["pci", "cardholder-data", "encryption", "storage", "tokenisation", "pan"],
        "text": (
            "Cardholder data must be protected wherever stored. Never store sensitive "
            "authentication data after authorisation (CVV2, PIN blocks, full magnetic stripe). "
            "Primary Account Numbers (PAN) must be masked when displayed (show max 6 first and 4 last digits). "
            "Strong cryptography (AES-256 minimum) must protect stored PAN. "
            "Cryptographic key management must document all custodians, rotation schedules (annual), "
            "and key storage procedures. Tokenisation is the recommended approach."
        ),
        "remediation": [
            "Implement tokenisation to replace PAN with non-sensitive tokens",
            "Deploy field-level encryption for any stored cardholder data",
            "Establish formal documented key management procedures",
            "Purge all stored sensitive authentication data (CVV2, etc.)",
        ],
    },
    {
        "id": "pci-req6",
        "title": "PCI DSS Requirement 6 — Secure Systems and Software",
        "framework": "PCI-DSS",
        "citation": "PCI DSS v4.0, Requirement 6",
        "severity": "High",
        "tags": ["pci", "patching", "vulnerability", "secure-development", "waf"],
        "text": (
            "All system components and software must be protected from known vulnerabilities "
            "by installing applicable security patches within one month of release for critical patches. "
            "Secure development practices must be followed including: security training for developers, "
            "code review for custom-developed applications, web application firewall (WAF) for "
            "public-facing web applications, and protection against OWASP Top 10 vulnerabilities. "
            "All code changes must be reviewed before deployment to production."
        ),
        "remediation": [
            "Establish a patch management process with 30-day SLA for critical patches",
            "Train all developers in secure coding practices annually",
            "Deploy WAF in blocking mode for all public-facing applications",
            "Conduct OWASP Top 10 vulnerability testing before each release",
        ],
    },
    {
        "id": "pci-req8",
        "title": "PCI DSS Requirement 8 — Identify Users and Authenticate Access",
        "framework": "PCI-DSS",
        "citation": "PCI DSS v4.0, Requirement 8",
        "severity": "High",
        "tags": ["pci", "authentication", "mfa", "user-management", "passwords"],
        "text": (
            "All users with access to system components must be assigned a unique ID. "
            "Shared or generic accounts are strictly prohibited in the CDE. "
            "MFA must be implemented for all access into the cardholder data environment (CDE). "
            "Password requirements: minimum 12 characters, complexity enforced, changed every 90 days, "
            "last 4 passwords cannot be reused, lockout after 6 failed attempts for 30 minutes. "
            "Vendor and third-party accounts must be enabled only during required service periods."
        ),
        "remediation": [
            "Enforce unique user IDs — audit and eliminate all shared accounts",
            "Deploy MFA for all CDE access (TOTP or hardware token)",
            "Implement password rotation and complexity enforcement",
            "Disable third-party accounts when not in active use",
        ],
    },
    {
        "id": "pci-req10",
        "title": "PCI DSS Requirement 10 — Log and Monitor All Access",
        "framework": "PCI-DSS",
        "citation": "PCI DSS v4.0, Requirement 10",
        "severity": "High",
        "tags": ["pci", "logging", "monitoring", "audit-trail", "log-retention"],
        "text": (
            "All access to system components and cardholder data must be logged. "
            "Log entries must include: user ID, event type, date/time, success/failure, "
            "origination, and identity of affected data/component. "
            "Logs must be reviewed daily (automated tools acceptable). "
            "Log retention: minimum 12 months, with 3 months immediately available. "
            "Logs must be protected from unauthorised modification and deletion. "
            "Time synchronisation (NTP) must be implemented across all systems."
        ),
        "remediation": [
            "Implement centralised log management with daily automated review",
            "Configure log retention for 12 months with 3-month hot storage",
            "Enable log integrity monitoring (hash verification)",
            "Deploy NTP synchronisation across all in-scope systems",
        ],
    },
]


# ── Helper functions ──────────────────────────────────────────────────────────

def get_all_regulations() -> List[Dict[str, Any]]:
    """Return the full regulations corpus."""
    return REGULATIONS_CORPUS


def get_by_framework(framework: str) -> List[Dict[str, Any]]:
    """Return all regulations for a specific framework."""
    return [r for r in REGULATIONS_CORPUS if r["framework"] == framework]


def get_by_id(reg_id: str) -> Dict[str, Any] | None:
    """Return a single regulation by its ID."""
    for r in REGULATIONS_CORPUS:
        if r["id"] == reg_id:
            return r
    return None


def get_by_severity(severity: str) -> List[Dict[str, Any]]:
    """Return all regulations of a given severity level."""
    return [r for r in REGULATIONS_CORPUS if r.get("severity") == severity]


def get_frameworks() -> List[str]:
    """Return list of unique frameworks in the corpus."""
    return sorted({r["framework"] for r in REGULATIONS_CORPUS})


def get_corpus_stats() -> Dict[str, Any]:
    """Return summary statistics about the regulations corpus."""
    framework_counts: Dict[str, int] = {}
    severity_counts:  Dict[str, int] = {}

    for r in REGULATIONS_CORPUS:
        fw  = r.get("framework", "Unknown")
        sev = r.get("severity", "Unknown")
        framework_counts[fw]  = framework_counts.get(fw, 0) + 1
        severity_counts[sev]  = severity_counts.get(sev, 0) + 1

    return {
        "total":            len(REGULATIONS_CORPUS),
        "by_framework":     framework_counts,
        "by_severity":      severity_counts,
        "frameworks":       get_frameworks(),
    }