import json

import frappe
from ury.ury_pos.api import getBranch
from frappe.utils import get_datetime


# Function to set order status in a KOT document
@frappe.whitelist()
def serve_kot(name, time):
    current_time = get_datetime()
    creation_time = frappe.db.get_value("URY KOT", name, "creation")
    production_time = current_time - creation_time
    production_time_minutes = production_time.total_seconds() / 60
    frappe.db.set_value("URY KOT", name, "start_time_serv", time)
    frappe.db.set_value("URY KOT", name, "production_time", production_time_minutes)
    frappe.db.set_value("URY KOT", name, "order_status", "Served")


@frappe.whitelist()
def start_preparation(name, time):
    frappe.db.set_value("URY KOT", name, "order_status", "In Preparation")


@frappe.whitelist()
def mark_ready(name, time):
    frappe.db.set_value("URY KOT", name, "order_status", "Ready")


# Function to mark it as verified by a user in cancel type KOT
@frappe.whitelist()
def confirm_cancel_kot(name, user):
    frappe.db.set_value("URY KOT", name, "verified", 1)
    frappe.db.set_value("URY KOT", name, "verified_by", user)


@frappe.whitelist(allow_guest=True)
def get_site_name():
    return {"site_name": frappe.local.site}

@frappe.whitelist()
def kot_list():
    today = frappe.utils.now()
    branch = getBranch()
    kot_alert_time = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_warning_time"
    )
    daily_order_number = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_reset_order_number_daily"
    )
    three_hours_ago = frappe.utils.add_to_date(today, hours=-3)
    audio_alert = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_alert"
    )

    kot_types = ["New Order", "Order Modified", "Duplicate", "Cancelled", "Partially cancelled"]
    base_filters = {
        "branch": branch,
        "type": ["in", kot_types],
        "docstatus": 1,
        "verified": 0,
        "creation": (">=", three_hours_ago),
    }

    def fetch_kots(status):
        filters = dict(base_filters, order_status=status)
        rows = frappe.get_list("URY KOT", fields=["name"], filters=filters, order_by="creation asc")
        result = []
        for row in rows:
            kotdoc = frappe.get_doc("URY KOT", row.name)
            kotjson = json.loads(frappe.as_json(kotdoc))
            if kotdoc.invoice:
                kotjson["ticket_number"] = frappe.db.get_value(
                    "POS Invoice", kotdoc.invoice, "custom_ticket_number"
                )
            result.append(kotjson)
        return result

    return {
        "YANGI": fetch_kots("Ready For Prepare"),
        "TAYYORLANMOQDA": fetch_kots("In Preparation"),
        "TAYYOR": fetch_kots("Ready"),
        "Branch": branch,
        "kot_alert_time": kot_alert_time,
        "audio_alert": audio_alert,
        "daily_order_number": daily_order_number,
    }

@frappe.whitelist()
def served_kot_list():
    today = frappe.utils.now()
    branch = getBranch()
    kot_alert_time = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_warning_time"
    )
    daily_order_number = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_reset_order_number_daily"
    )
    three_hours_ago = frappe.utils.add_to_date(today, hours=-3)
    audio_alert = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_alert"
    )
    kotList = frappe.get_list(
        "URY KOT",
        fields=["name"],
        filters={
            "order_status": "Served",
            "branch": branch,
            "type": [
                "in",
                [
                    "New Order",
                    "Order Modified",
                    "Duplicate",
                    "Cancelled",
                    "Partially cancelled",
                ],
            ],
            "docstatus": 1,
            "verified": 0,
            "creation": (">=", three_hours_ago),
        },
        order_by="creation desc",
    )
    print(kotList,"kotList..................")
    KOT = []
    for kot in kotList:
        kotdoc = frappe.get_doc("URY KOT", kot.name)
        print(kot.name,".................kotdoc")
        invoice=frappe.db.get_value("URY KOT",kot.name,"invoice")
        print(invoice,".....................invoice")
        kotjson = json.loads(frappe.as_json(kotdoc))
        KOT.append(kotjson)
    return {
        "KOT": KOT,
        "Branch": branch,
        "kot_alert_time": kot_alert_time,
        "audio_alert": audio_alert,
        "daily_order_number":daily_order_number
    }

