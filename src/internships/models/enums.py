"""Small finite-value types used by the focused LinkedIn pipeline."""

from __future__ import annotations

from enum import StrEnum


class InternshipCategory(StrEnum):
    """Enumerate supported technology internship categories."""

    ARTIFICIAL_INTELLIGENCE = "artificial-intelligence"
    CLOUD_DEVOPS_INFRASTRUCTURE = "cloud-devops-infrastructure"
    COMPUTER_SCIENCE = "computer-science"
    COMPUTER_VISION = "computer-vision"
    CYBERSECURITY = "cybersecurity"
    DATA_ENGINEERING = "data-engineering"
    DATA_SCIENCE = "data-science"
    DEVOPS_SITE_RELIABILITY = "devops-site-reliability"
    EMBEDDED_FIRMWARE_ROBOTICS = "embedded-firmware-robotics"
    FIRMWARE = "firmware"
    HARDWARE_SEMICONDUCTOR = "hardware-semiconductor"
    MACHINE_LEARNING_AI = "machine-learning-ai"
    NATURAL_LANGUAGE_PROCESSING = "natural-language-processing"
    QUANTITATIVE_TECHNOLOGY = "quantitative-technology"
    RESEARCH_ENGINEERING = "research-engineering"
    ROBOTICS = "robotics"
    SECURITY_ENGINEERING = "security-engineering"
    SEMICONDUCTOR_SILICON = "semiconductor-silicon"
    SITE_RELIABILITY = "site-reliability"
    SOFTWARE_DEVELOPMENT = "software-development"
    SOFTWARE_ENGINEERING = "software-engineering"
    SOFTWARE_TECHNOLOGY = "software-technology"
    SOFTWARE_TESTING = "software-testing"
    MACHINE_LEARNING = "machine-learning"
    INFRASTRUCTURE = "infrastructure"
    EMBEDDED_SYSTEMS = "embedded-systems"
    QUANTITATIVE_DEVELOPMENT = "quantitative-development"
    OTHER_TECH = "other-tech"
    UNKNOWN = "unknown"


class EmploymentType(StrEnum):
    """Enumerate the two opportunity types published by the directory."""

    INTERNSHIP = "internship"
    NEW_GRAD = "new-grad"


class JobStatus(StrEnum):
    """Enumerate job lifecycle states."""

    OPEN = "open"
    CLOSED = "closed"


class RunStatus(StrEnum):
    """Enumerate search-run outcomes."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
