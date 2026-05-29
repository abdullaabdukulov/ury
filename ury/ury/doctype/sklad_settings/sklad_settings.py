import frappe
from frappe.model.document import Document


class SkladSettings(Document):
    pass


def get_markup_percent(company: str) -> float:
    """Kompaniya uchun ustama foizni qaytaradi.
    Alohida sozlanmagan bo'lsa — default foiz ishlatiladi.

    Sklad Settings — Single doctype, shuning uchun get_single ishlatiladi
    (get_all Single doctype'da har doim [] qaytaradi)."""
    settings = frappe.get_single("Sklad Settings")

    for row in settings.company_markups:
        if row.company == company:
            return float(row.percent or 0)

    return float(settings.default_markup_percent or 15)
