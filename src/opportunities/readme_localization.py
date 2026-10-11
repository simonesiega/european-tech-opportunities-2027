"""Fixed presentation strings for deterministic README projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from opportunities.utils.time import ensure_utc


@dataclass(frozen=True, slots=True)
class ReadmeLocale:
    """Localize presentation only; listing values and state seals remain unchanged."""

    months: tuple[str, ...]
    timestamp: str
    never: str
    collection_label: str
    badge_labels: tuple[str, str, str]
    badge_alt_labels: tuple[str, str, str]
    metadata: str
    directory: str
    new_grad_heading: str
    new_grad_preview: str
    internship_heading: str
    internship_preview: str
    columns: tuple[str, str, str, str]
    view: str

    def collection_time(self, value: datetime | None) -> str:
        if value is None:
            return self.never
        utc = ensure_utc(value)
        return self.timestamp.format(
            year=utc.year,
            month=self.months[utc.month - 1],
            day=utc.day,
            hour=f"{utc.hour:02d}",
            minute=f"{utc.minute:02d}",
        )

    @property
    def table_header(self) -> str:
        return "| " + " | ".join(self.columns) + " |\n|---|---|---|---|\n"


LOCALES = {
    "en": ReadmeLocale(
        months=(
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        timestamp="{month} {day}, {year} at {hour}:{minute} UTC",
        never="Never",
        collection_label="Last successful collection: ",
        badge_labels=("Total opportunities", "Internships", "New Grad"),
        badge_alt_labels=("Total opportunities: ", "Internships: ", "New Grad opportunities: "),
        metadata=(
            "**Open opportunities:** {total} (Internships: {internships} · "
            "New Grad: {new_grad})<br>\n**Last successful collection:** "
            "{updated}\n"
        ),
        directory="Browse and filter the complete directory at **[{url}]({url})**.",
        new_grad_heading="Latest New Grad opportunities",
        new_grad_preview=(
            "Showing {shown} of {total} open New Grad opportunities, "
            "newest first by first-seen time:"
        ),
        internship_heading="Latest internships",
        internship_preview=(
            "Showing {shown} of {total} open internships, newest first by first-seen time:"
        ),
        columns=("Company", "Title", "Location", "Listing"),
        view="View",
    ),
    "it": ReadmeLocale(
        months=(
            "gennaio",
            "febbraio",
            "marzo",
            "aprile",
            "maggio",
            "giugno",
            "luglio",
            "agosto",
            "settembre",
            "ottobre",
            "novembre",
            "dicembre",
        ),
        timestamp="{day} {month} {year} alle {hour}:{minute} UTC",
        never="Mai",
        collection_label="Ultima raccolta completata con successo: ",
        badge_labels=("Offerte attive", "Tirocini", "New Grad"),
        badge_alt_labels=("Offerte attive: ", "Tirocini: ", "Posizioni New Grad: "),
        metadata=(
            "**Offerte aperte:** {total} (Tirocini: {internships} · New Grad:"
            " {new_grad})<br>\n**Ultima raccolta completata con successo:** "
            "{updated}\n"
        ),
        directory="Consulta e filtra tutte le offerte su **[{url}]({url})**.",
        new_grad_heading="Ultime offerte New Grad",
        new_grad_preview=(
            "{shown} offerte New Grad su {total} ancora aperte, ordinate dalla data "
            "di prima rilevazione più recente:"
        ),
        internship_heading="Ultimi tirocini",
        internship_preview=(
            "{shown} tirocini su {total} ancora aperti, ordinati dalla data "
            "di prima rilevazione più recente:"
        ),
        columns=("Azienda", "Posizione", "Località", "Annuncio"),
        view="Apri",
    ),
    "fr": ReadmeLocale(
        months=(
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ),
        timestamp="{day} {month} {year} à {hour} h {minute} UTC",
        never="Jamais",
        collection_label="Dernière collecte réussie : ",
        badge_labels=("Offres actives", "Stages", "New Grad"),
        badge_alt_labels=("Offres actives : ", "Stages : ", "Offres New Grad : "),
        metadata=(
            "**Offres actives :** {total} (Stages : {internships} · New Grad "
            ": {new_grad})<br>\n**Dernière collecte réussie :** {updated}\n"
        ),
        directory="Consultez et filtrez l\u2019ensemble des offres sur **[{url}]({url})**.",
        new_grad_heading="Dernières offres New Grad",
        new_grad_preview=(
            "{shown} offres parmi les {total} offres New Grad actives, classées "
            "par date de première observation, de la plus récente à la plus ancienne :"
        ),
        internship_heading="Derniers stages",
        internship_preview=(
            "{shown} offres parmi les {total} stages actifs, classées par date de "
            "première observation, de la plus récente à la plus ancienne :"
        ),
        columns=("Entreprise", "Intitulé du poste", "Localisation", "Annonce"),
        view="Voir l\u2019offre",
    ),
    "de": ReadmeLocale(
        months=(
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ),
        timestamp="{day}. {month} {year} um {hour}:{minute} UTC",
        never="Nie",
        collection_label="Letzte erfolgreiche Datenerfassung: ",
        badge_labels=("Offene Stellen", "Praktika", "New Grad"),
        badge_alt_labels=("Offene Stellen: ", "Praktika: ", "New-Grad-Stellen: "),
        metadata=(
            "**Offene Stellen:** {total} (Praktika: {internships} · New Grad:"
            " {new_grad})<br>\n**Letzte erfolgreiche Datenerfassung:** "
            "{updated}\n"
        ),
        directory=(
            "Alle Stellenangebote findest du mit Such- und "
            "Filtermöglichkeiten unter **[{url}]({url})**."
        ),
        new_grad_heading="Neueste New-Grad-Stellen",
        new_grad_preview=(
            "{shown} von {total} offenen New-Grad-Angeboten, nach dem Zeitpunkt "
            "der ersten Erfassung sortiert, neueste zuerst:"
        ),
        internship_heading="Neueste Praktika",
        internship_preview=(
            "{shown} von {total} offenen Praktika, nach dem Zeitpunkt "
            "der ersten Erfassung sortiert, neueste zuerst:"
        ),
        columns=("Unternehmen", "Position", "Standort", "Anzeige"),
        view="Ansehen",
    ),
    "es": ReadmeLocale(
        months=(
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ),
        timestamp="{day} de {month} de {year} a las {hour}:{minute} UTC",
        never="Nunca",
        collection_label="Última recopilación realizada con éxito: ",
        badge_labels=("Ofertas activas", "Prácticas", "New Grad"),
        badge_alt_labels=("Ofertas activas: ", "Prácticas: ", "Puestos New Grad: "),
        metadata=(
            "**Ofertas activas:** {total} (Prácticas: {internships} · New "
            "Grad: {new_grad})<br>\n**Última recopilación realizada con "
            "éxito:** {updated}\n"
        ),
        directory="Consulta y filtra todas las oportunidades en **[{url}]({url})**.",
        new_grad_heading="Últimas ofertas New Grad",
        new_grad_preview=(
            "{shown} de {total} puestos New Grad activos, ordenados por fecha "
            "del primer registro, del más reciente al más antiguo:"
        ),
        internship_heading="Últimas ofertas de prácticas",
        internship_preview=(
            "{shown} de {total} prácticas activas, ordenadas por fecha "
            "del primer registro, de la más reciente a la más antigua:"
        ),
        columns=("Empresa", "Puesto", "Ubicación", "Anuncio"),
        view="Ver oferta",
    ),
    "zh-CN": ReadmeLocale(
        months=tuple(str(month) for month in range(1, 13)),
        timestamp="{year} 年 {month} 月 {day} 日 {hour}:{minute}\uff08UTC\uff09",
        never="从未",
        collection_label="最近一次成功采集\uff1a",
        badge_labels=("在招职位", "实习岗位", "应届生岗位"),
        badge_alt_labels=("在招职位总数\uff1a", "实习岗位\uff1a", "应届生岗位\uff1a"),
        metadata=(
            "**在招职位\uff1a** {total}\uff08实习\uff1a{internships} · "
            "New Grad\uff1a{new_grad}\uff09<br>\n"
            "**最近一次成功采集\uff1a** {updated}\n"
        ),
        directory="前往 **[{url}]({url})** 浏览和筛选完整的职位目录。",
        new_grad_heading="最新 New Grad 职位",
        new_grad_preview=(
            "以下展示 {total} 个在招 New Grad 职位中的 {shown} 个\uff0c"
            "按首次记录时间从新到旧排序\uff1a"
        ),
        internship_heading="最新实习岗位",
        internship_preview=(
            "以下展示 {total} 个在招实习岗位中的 {shown} 个\uff0c按首次记录时间从新到旧排序\uff1a"
        ),
        columns=("公司", "职位名称", "地点", "原始公告"),
        view="查看",
    ),
}


def locale_for_path(path: Path) -> ReadmeLocale:
    """Recognize supported README filenames; custom filenames retain English output."""
    language = path.name.removeprefix("README.").removesuffix(".md")
    if path.name != f"README.{language}.md":
        return LOCALES["en"]
    return LOCALES.get(language, LOCALES["en"])
