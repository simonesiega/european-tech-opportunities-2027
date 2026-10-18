"""Shared categories, employment types, and lifecycle statuses."""

from __future__ import annotations

from enum import StrEnum


class OpportunityCategory(StrEnum):
    """Technology categories recognized by the classifier."""

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
    """Opportunity types published by the directory."""

    INTERNSHIP = "internship"
    NEW_GRAD = "new-grad"


class JobStatus(StrEnum):
    """Open and closed listing states."""

    OPEN = "open"
    CLOSED = "closed"


class RunStatus(StrEnum):
    """Collection outcomes, including partially successful batches."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
