import frappe
from frappe import _


def before_save(doc, method=None):
    """Sales Order saqlashdan oldin:
    - Har bir item uchun Bosh Sklad valuation_rate ni olish
    - Kompaniya ustama foizini qo'shish
    - Valuation rate = 0 bo'lsa xato berish
    """
    try:
        settings = frappe.get_single("Sklad Settings")
    except Exception:
        return

    main_warehouse = settings.get("main_warehouse")
    if not main_warehouse:
        return

    # Mijoz kompaniyasini aniqlash (Customer → represents_company)
    customer_company = frappe.db.get_value("Customer", doc.customer, "represents_company")
    if not customer_company:
        return

    from ury.ury.doctype.sklad_settings.sklad_settings import get_markup_percent
    markup = get_markup_percent(customer_company)

    zero_rate_items = []

    for item in doc.items:
        valuation_rate = frappe.db.get_value(
            "Bin",
            {"item_code": item.item_code, "warehouse": main_warehouse},
            "valuation_rate"
        ) or 0

        if not valuation_rate:
            zero_rate_items.append(item.item_name or item.item_code)
            continue

        item.rate = round(float(valuation_rate) * (1 + markup / 100), 2)
        item.price_list_rate = item.rate

    if zero_rate_items:
        frappe.throw(
            _("Quyidagi mahsulotlar uchun <b>{0}</b> da narx topilmadi:"
              "<br><b>{1}</b><br><br>"
              "Avval tashqi supplierdan qabul qiling.").format(
                main_warehouse,
                "<br>".join(zero_rate_items)
            ),
            title=_("Narx topilmadi")
        )
