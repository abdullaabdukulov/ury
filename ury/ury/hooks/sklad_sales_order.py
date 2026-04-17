import frappe
from frappe import _


def before_save(doc, method=None):
    """Inter-company SO saqlashdan oldin:
    - PO narxlari × ustama foiz bilan SO itemlarini yangilash
    - PO da narx topilmagan itemlar bo'lsa xato berish
    """
    if not doc.inter_company_order_reference:
        return

    # Sklad Settings
    names = frappe.get_all("Sklad Settings", limit=1, pluck="name")
    if not names:
        frappe.throw(_("Sklad Settings topilmadi. Avval sozlang."), title=_("Sozlash kerak"))
    settings = frappe.get_doc("Sklad Settings", names[0])

    # Mijoz kompaniyasini aniqlash
    customer_company = frappe.db.get_value("Customer", doc.customer, "represents_company")
    if not customer_company:
        return

    # Ustama foizni Sklad Settings dan olish (ikkinchi query yo'q)
    markup = _get_markup_from_settings(settings, customer_company)

    # PO dan asl narxlarni olish
    po_rates = {
        row.item_code: float(row.rate or 0)
        for row in frappe.get_all(
            "Purchase Order Item",
            filters={"parent": doc.inter_company_order_reference},
            fields=["item_code", "rate"],
        )
    }

    if not po_rates:
        frappe.throw(
            _("Purchase Order <b>{0}</b> da item topilmadi.").format(
                doc.inter_company_order_reference
            ),
            title=_("PO bo'sh")
        )

    zero_rate_items = []
    multiplier = 1 + markup / 100

    for item in doc.items:
        base_rate = po_rates.get(item.item_code) or 0

        if not base_rate:
            zero_rate_items.append(item.item_name or item.item_code)
            continue

        item.rate = round(base_rate * multiplier, 2)
        item.price_list_rate = item.rate
        item.amount = round(item.rate * item.qty, 2)

    if zero_rate_items:
        frappe.throw(
            _("Quyidagi mahsulotlar Purchase Order <b>{0}</b> da topilmadi:"
              "<br><b>{1}</b>").format(
                doc.inter_company_order_reference,
                "<br>".join(zero_rate_items)
            ),
            title=_("Narx topilmadi")
        )

    doc.run_method("calculate_taxes_and_totals")


def _get_markup_from_settings(settings, company):
    """Settings doc dan kompaniya uchun ustama foizni qaytaradi (qayta fetch qilmaydi)."""
    for row in settings.company_markups:
        if row.company == company:
            return float(row.percent or 0)
    return float(settings.default_markup_percent or 0)
