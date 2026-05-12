import frappe
from frappe import _
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
    make_inter_company_purchase_invoice,
)


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

    items_without_valuation = []

    for item in doc.items:
        # Avval Bin dagi valuation_rate
        valuation_rate = frappe.db.get_value(
            "Bin",
            {"item_code": item.item_code, "warehouse": main_warehouse},
            "valuation_rate"
        ) or 0

        # Fallback: Item master dagi valuation_rate
        if not valuation_rate:
            valuation_rate = frappe.db.get_value(
                "Item", item.item_code, "valuation_rate"
            ) or 0

        if not valuation_rate:
            # Tannarx topilmadi — foydalanuvchi qo'lda kiritgan rate saqlanadi
            items_without_valuation.append(item.item_name or item.item_code)
            continue

        item.rate = round(float(valuation_rate) * multiplier, 2)
        item.price_list_rate = item.rate
        item.amount = round(item.rate * item.qty, 2)

    if items_without_valuation:
        frappe.msgprint(
            _("Quyidagi mahsulotlarda tannarx topilmadi — 'Rate' ustunida "
              "qo'lda kiriting (ustama qo'shilgan holda):<br><b>{0}</b>").format(
                "<br>".join(items_without_valuation)
            ),
            indicator="orange",
            alert=True
        )

    # ERPNext validate delivery_date ni bugungi sanaga o'zgartirib yuboradi —
    # inter-company SO uchun transaction_date bilan bir xil bo'lishi kerak
    if doc.transaction_date:
        doc.delivery_date = doc.transaction_date
        for item in doc.items:
            item.delivery_date = doc.transaction_date

    doc.run_method("calculate_taxes_and_totals")


def on_submit(doc, method=None):
    """Sales Order Filial Manager tomonidan tasdiqlanganda (workflow_state='Filial Approved'):
    1. Sales Invoice (Sklad company) yaratiladi va submit qilinadi
    2. Sales Invoice asosida Purchase Invoice (Filial company) yaratiladi va submit qilinadi

    Faqat inter-company SO uchun (Sklad → Filial) ishlaydi.
    """
    # Faqat Workflow orqali "Filial Approved" bo'lganda ishga tushadi
    if (doc.get("workflow_state") or "") != "Filial Approved":
        return

    # Faqat inter-company SO (Sklad → Filial) bo'lganida
    if not doc.inter_company_order_reference:
        return

    customer_company = frappe.db.get_value("Customer", doc.customer, "represents_company")
    if not customer_company:
        return

    # ── 1) Sales Invoice yaratish (Sklad company tomonida) ──
    try:
        si = make_sales_invoice(doc.name, ignore_permissions=True)
        si.update_stock = 0   # SO+DN bilan stock harakati alohida hisoblanadi
        si.flags.ignore_permissions = True
        si.insert(ignore_permissions=True)
        si.submit()
        frappe.msgprint(
            _("Sales Invoice yaratildi: <b>{0}</b>").format(
                frappe.utils.get_link_to_form("Sales Invoice", si.name)
            ),
            indicator="green",
            alert=True,
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         f"SO {doc.name} → Sales Invoice yaratishda xato")
        frappe.throw(_("Sales Invoice yaratilmadi: {0}").format(str(e)))

    # ── 2) Inter-company Purchase Invoice yaratish (Filial company tomonida) ──
    try:
        pi = make_inter_company_purchase_invoice(si.name)
        pi.flags.ignore_permissions = True
        pi.insert(ignore_permissions=True)
        pi.submit()
        frappe.msgprint(
            _("Inter-company Purchase Invoice yaratildi: <b>{0}</b>").format(
                frappe.utils.get_link_to_form("Purchase Invoice", pi.name)
            ),
            indicator="green",
            alert=True,
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         f"SI {si.name} → Purchase Invoice yaratishda xato")
        frappe.msgprint(
            _("Sales Invoice yaratildi, lekin Purchase Invoice yaratilmadi: {0}").format(str(e)),
            indicator="orange",
        )
