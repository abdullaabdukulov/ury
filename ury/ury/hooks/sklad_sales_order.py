import frappe
from frappe import _


def before_save(doc, method=None):
    """Sklad kompaniyasidan filial kompaniyalariga sotilganda:
    - Valuation rate × ustama foiz bilan SO itemlarini yangilash
    - Delivery date ni SO transaction_date ga tenglashtirish

    Faqat quyidagi holatda ishlaydi:
      1. SO inter-company bo'lsa (inter_company_order_reference bo'lsa)
      2. doc.company = Sklad Settings dagi main_warehouse kompaniyasi bo'lsa
      3. Customer ning represents_company si company_markups listida bo'lsa
    """
    if not doc.inter_company_order_reference:
        return

    names = frappe.get_all("Sklad Settings", limit=1, pluck="name")
    if not names:
        return
    settings = frappe.get_doc("Sklad Settings", names[0])

    main_warehouse = settings.get("main_warehouse")
    if not main_warehouse:
        return

    # Sotuvchi kompaniya Sklad kompaniyasi bo'lishi kerak
    sklad_company = frappe.db.get_value("Warehouse", main_warehouse, "company")
    if not sklad_company or doc.company != sklad_company:
        return

    customer_company = frappe.db.get_value("Customer", doc.customer, "represents_company")
    if not customer_company:
        return

    # Customer company Sklad Settings listida bo'lishi kerak
    markup_row = next(
        (row for row in settings.company_markups if row.company == customer_company),
        None
    )
    if not markup_row:
        return

    markup = float(markup_row.percent or settings.default_markup_percent or 0)
    multiplier = 1 + markup / 100

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

        item.rate = round(float(valuation_rate) * multiplier, 2)
        item.price_list_rate = item.rate
        item.amount = round(item.rate * item.qty, 2)

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

    # ERPNext validate delivery_date ni bugungi sanaga o'zgartirib yuboradi —
    # inter-company SO uchun transaction_date bilan bir xil bo'lishi kerak
    if doc.transaction_date:
        doc.delivery_date = doc.transaction_date
        for item in doc.items:
            item.delivery_date = doc.transaction_date

    doc.run_method("calculate_taxes_and_totals")
