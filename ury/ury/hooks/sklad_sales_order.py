"""
Sklad → Filial inter-company Sales Order avtomatlashtirish (YAGONA manba).

Oqim:
  1. Filial Purchase Order yaratadi → ERPNext inter-company SO (Sklad) yaratadi
  2. before_save: SO itemlariga tannarx × ustama (Sklad Settings) qo'llanadi
  3. Workflow: Draft → "Filial Approved" (tasdiqlash + submit)
  4. on_submit (faqat "Filial Approved"): Sales Invoice + Purchase Invoice
     avtomatik yaratiladi (ikkalasi ham update_stock=1)

Konfiguratsiya: Sklad Settings (Single) — main_warehouse, default_markup_percent,
company_markups[]. Logika shu yerda (kod), sozlamalar UI'da.

DIQQAT: Bu yagona inter-company SO handleri. jazira_app dagi eski dublikat
overrides/sales_order.on_submit hooki olib tashlangan (double-invoicing oldini olish).
"""

import frappe
from frappe import _
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
    make_inter_company_purchase_invoice,
)

APPROVED_STATE = "Filial Approved"


# =============================================================================
# Sklad Settings (Single) helperlari
# =============================================================================
def _get_settings():
    """Sklad Settings Single doctype. Sozlanmagan bo'lsa None."""
    settings = frappe.get_single("Sklad Settings")
    if not settings.main_warehouse:
        return None
    return settings


def _get_markup_percent(settings, company):
    """Filial Sklad Settings ro'yxatida bo'lsa ustama foizini, aks holda None.

    QATTIQ qoida: ro'yxatda yo'q filial uchun None qaytadi → avtomatlashtirish
    ishlamaydi (oddiy SO bo'lib qoladi). Ro'yxatda bor, lekin foiz 0/bo'sh
    bo'lsa — default_markup_percent ishlatiladi.
    """
    for row in settings.company_markups:
        if row.company == company:
            return float(row.percent or settings.default_markup_percent or 0)
    return None


def _resolve_sklad_to_filial(doc, settings):
    """SO Sklad → Filial inter-company ekanligini aniqlaydi (qattiq validatsiya).

    Returns (customer_company, markup_percent) yoki (None, None).
    Shartlar:
      1. inter-company SO bo'lishi (inter_company_order_reference)
      2. sotuvchi = Sklad Settings'dagi main_warehouse kompaniyasi (FROM)
      3. xaridor = represents_company bor internal customer
      4. xaridor kompaniyasi Sklad Settings company_markups ro'yxatida bo'lishi (TO)
    """
    if not doc.inter_company_order_reference:
        return None, None

    # FROM: faqat bosh skladdan
    sklad_company = frappe.db.get_value("Warehouse", settings.main_warehouse, "company")
    if not sklad_company or doc.company != sklad_company:
        return None, None

    # internal customer mi?
    customer_company = frappe.db.get_value("Customer", doc.customer, "represents_company")
    if not customer_company:
        return None, None

    # TO: filial Sklad Settings ro'yxatida bo'lishi SHART.
    # Ro'yxatda yo'q bo'lsa — oddiy SO sifatida qoldiriladi (skip, xato yo'q).
    markup = _get_markup_percent(settings, customer_company)
    if markup is None:
        return None, None

    return customer_company, markup


# =============================================================================
# before_save — tannarx × ustama narxlarni qo'llash
# =============================================================================
def before_save(doc, method=None):
    settings = _get_settings()
    if not settings:
        return

    customer_company, markup = _resolve_sklad_to_filial(doc, settings)
    if customer_company is None:
        return

    multiplier = 1 + (markup or 0) / 100
    items_without_valuation = []

    for item in doc.items:
        valuation_rate = (
            frappe.db.get_value(
                "Bin",
                {"item_code": item.item_code, "warehouse": settings.main_warehouse},
                "valuation_rate",
            )
            or frappe.db.get_value("Item", item.item_code, "valuation_rate")
            or 0
        )

        if not valuation_rate:
            items_without_valuation.append(item.item_name or item.item_code)
            continue

        item.rate = round(float(valuation_rate) * multiplier, 2)
        item.price_list_rate = item.rate
        item.amount = round(item.rate * item.qty, 2)

    if items_without_valuation:
        frappe.msgprint(
            _(
                "Quyidagi mahsulotlarda tannarx topilmadi — 'Rate' ustunida "
                "qo'lda kiriting (ustama qo'shilgan holda):<br><b>{0}</b>"
            ).format("<br>".join(items_without_valuation)),
            indicator="orange",
            alert=True,
        )

    # ERPNext validate delivery_date ni bugunga o'zgartiradi — inter-company uchun
    # transaction_date bilan bir xil bo'lishi kerak
    if doc.transaction_date:
        doc.delivery_date = doc.transaction_date
        for item in doc.items:
            item.delivery_date = doc.transaction_date

    doc.run_method("calculate_taxes_and_totals")


# =============================================================================
# on_submit — "Filial Approved" bo'lganda SI + PI yaratish
# =============================================================================
def on_submit(doc, method=None):
    # Faqat Workflow orqali tasdiqlangan SO uchun
    if (doc.get("workflow_state") or "") != APPROVED_STATE:
        return

    settings = _get_settings()
    if not settings:
        return

    customer_company, _markup = _resolve_sklad_to_filial(doc, settings)
    if customer_company is None:
        return

    # Idempotentlik: bu SO uchun SI allaqachon mavjud bo'lsa qayta yaratmaymiz
    if frappe.db.exists(
        "Sales Invoice Item", {"sales_order": doc.name, "docstatus": ["<", 2]}
    ):
        return

    branch_warehouse = _get_branch_warehouse(doc.inter_company_order_reference)

    # Atomik: commit chaqirilmaydi — PI xato bo'lsa SO submit + SI birga rollback bo'ladi
    si = _create_sales_invoice(doc, settings)
    pi = _create_purchase_invoice(si, branch_warehouse)

    frappe.msgprint(
        _("Sales Invoice <b>{0}</b> va Purchase Invoice <b>{1}</b> avtomatik yaratildi").format(
            frappe.utils.get_link_to_form("Sales Invoice", si.name),
            frappe.utils.get_link_to_form("Purchase Invoice", pi.name),
        ),
        indicator="green",
        alert=True,
    )


def _get_branch_warehouse(po_name):
    """Filial Purchase Order'ining ombori (header → items fallback)."""
    if not po_name:
        return None
    warehouse = frappe.db.get_value("Purchase Order", po_name, "set_warehouse")
    if warehouse:
        return warehouse
    return frappe.db.get_value(
        "Purchase Order Item", {"parent": po_name}, "warehouse", order_by="idx asc"
    )


def _create_sales_invoice(so_doc, settings):
    """Sklad tomonida Sales Invoice (update_stock=1 — sklad omboridan chiqim)."""
    si = make_sales_invoice(so_doc.name, ignore_permissions=True)
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.update_stock = 1
    si.set_posting_time = 1
    si.posting_date = so_doc.transaction_date
    si.due_date = so_doc.transaction_date

    sklad_warehouse = so_doc.set_warehouse or settings.main_warehouse
    si.set_warehouse = sklad_warehouse
    for item in si.items:
        if not item.warehouse:
            item.warehouse = sklad_warehouse

    si.run_method("calculate_taxes_and_totals")
    si.insert(ignore_permissions=True)
    si.submit()
    return si


def _create_purchase_invoice(si_doc, branch_warehouse):
    """Filial tomonida inter-company Purchase Invoice (update_stock=1 — kirim)."""
    pi = make_inter_company_purchase_invoice(si_doc.name)
    pi.flags.ignore_permissions = True
    pi.update_stock = 1
    pi.set_posting_time = 1
    pi.posting_date = si_doc.posting_date
    pi.bill_date = si_doc.posting_date
    pi.due_date = si_doc.posting_date

    if not branch_warehouse:
        frappe.throw(
            _(
                "Filial ombori topilmadi. Purchase Order'da 'Set Warehouse' ni belgilang."
            )
        )

    pi.set_warehouse = branch_warehouse
    for item in pi.items:
        item.warehouse = branch_warehouse

    # update_stock=1 da expense_account inventory account bo'lishi shart
    # (aks holda ERPNext "Expense Head Changed" ogohlantirishi)
    inventory_account = frappe.db.get_value(
        "Company", pi.company, "default_inventory_account"
    )
    if inventory_account:
        for item in pi.items:
            item.expense_account = inventory_account

    pi.insert(ignore_permissions=True)
    pi.run_method("calculate_taxes_and_totals")
    pi.submit()
    return pi
