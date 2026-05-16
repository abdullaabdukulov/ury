import frappe
from frappe import _
from datetime import date, datetime, timedelta
from frappe.utils import validate_phone_number


#GetTable  decripted temporarily
# @frappe.whitelist()
# def getTable(room):
#     branch_name = getBranch()   
#     tables = frappe.get_all(
#         "URY Table",
#         fields=["name", "occupied", "latest_invoice_time", "is_take_away", "restaurant_room","table_shape","no_of_seats","layout_x","layout_y"],
#         filters={"branch": branch_name,"restaurant_room":room,}
#     )    
#     return tables

@frappe.whitelist()
def getRestaurantMenu(pos_profile, room=None, order_type=None):
    menu_items = []
    menu_items_with_image = []

    user_role = frappe.get_roles()

    pos_profile = frappe.get_doc("POS Profile", pos_profile)

    cashier = any(
        role.role in user_role for role in pos_profile.role_allowed_for_billing
    )
    branch_name = getBranch()
    restaurant = frappe.db.get_value("URY Restaurant", {"branch": branch_name}, "name")
    
    if room:
    
        room_wise_menu = frappe.db.get_value(
            "URY Restaurant", restaurant, "room_wise_menu"
        )
        
        if room_wise_menu:
            menu = frappe.db.get_value(
                "Menu for Room",
                {"parent": restaurant, "room": room},
                "menu"
            )
            if not menu:
                 menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
        else:
            menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")

    elif cashier and order_type:
        order_type_wise_menu = frappe.db.get_value(
            "URY Restaurant", restaurant, "order_type_wise_menu"
        )
    
        if order_type_wise_menu:
            menu = frappe.db.get_value(
                "Order Type Menu",
                {"parent": restaurant, "order_type": order_type},
                "menu"
            )
            if not menu:
                 menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
    
        else:
            menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")

    # Default menu if nothing is selected
    else:
        menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
    
    if not menu:
        frappe.throw(_("Please set an active menu for Restaurant {0}").format(restaurant))
    
    
    # Get menu items — `idx` orqali admin drag-drop tartibi, keyin alfavit (Phase 3)
    menu_items = frappe.get_all(
        "URY Menu Item",
        filters={"parent": menu, "disabled": 0},
        fields=["item", "item_name", "rate", "special_dish", "disabled", "course", "idx"],
        order_by="idx asc, item_name asc"
    )

    # ─── TOP SELLERS — oxirgi 30 kun ichida eng ko'p sotilgan itemlar ───
    # Filial darajasida hisoblanadi (pos_profile bilan filterlangan POS Invoice lar).
    # Natija: item_code -> (sales_count, top_level)
    # top_level: 1 (top 25%), 2 (top 10%), 3 (top 3%) — UI da rim raqami badge
    sales_stats = _get_top_sellers_stats(pos_profile.name)

    menu_items_with_image = [
        {
            "item": item.item,
            "item_name": item.item_name,
            "rate": item.rate,
            "special_dish": item.special_dish,
            "disabled": item.disabled,
            "item_image": frappe.db.get_value("Item", item.item, "image"),
            "course": item.course,
            "idx": int(item.idx or 0),
            "sales_count": sales_stats.get(item.item, {}).get("count", 0),
            "top_level": sales_stats.get(item.item, {}).get("level", 0),
        }
        for item in menu_items
    ]
    modified = frappe.db.get_value("URY Menu", menu, "modified")


    return {
        "items": menu_items_with_image,
        "modified_time": modified,
        "name": menu
    }


def _get_top_sellers_stats(pos_profile_name: str) -> dict:
    """Oxirgi 30 kun POS Invoice item statistikasi bo'yicha top sellers.

    Returns:
        dict: {item_code: {"count": int, "level": 0..3}}
        level: 0=oddiy, 1=top-25%, 2=top-10%, 3=top-3% (eng zo'rlar)
    """
    from frappe.utils import add_days, nowdate

    try:
        from_date = add_days(nowdate(), -30)
        rows = frappe.db.sql(
            """
            SELECT sii.item_code, SUM(sii.qty) AS qty
            FROM `tabPOS Invoice` si
            INNER JOIN `tabPOS Invoice Item` sii ON sii.parent = si.name
            WHERE si.pos_profile = %(profile)s
              AND si.docstatus = 1
              AND si.posting_date >= %(from_date)s
            GROUP BY sii.item_code
            ORDER BY qty DESC
            """,
            {"profile": pos_profile_name, "from_date": from_date},
            as_dict=True,
        )
    except Exception:
        # POS Invoice yo'q yoki boshqa xato — bo'sh statistika qaytarish
        return {}

    if not rows:
        return {}

    total = len(rows)
    # Top 3% = level 3 (eng zo'rlar), top 10% = level 2, top 25% = level 1
    t3 = max(1, int(total * 0.03))
    t2 = max(2, int(total * 0.10))
    t1 = max(3, int(total * 0.25))

    stats = {}
    for idx, row in enumerate(rows):
        if idx < t3:
            level = 3
        elif idx < t2:
            level = 2
        elif idx < t1:
            level = 1
        else:
            level = 0
        stats[row["item_code"]] = {
            "count": int(row["qty"] or 0),
            "level": level,
        }
    return stats

@frappe.whitelist()
def getBranch():
    user = frappe.session.user
    if user != "Administrator":
        sql_query = """
            SELECT b.branch
            FROM `tabURY User` AS a
            INNER JOIN `tabBranch` AS b ON a.parent = b.name
            WHERE a.user = %s
        """
        branch_array = frappe.db.sql(sql_query, user, as_dict=True)
        if not branch_array:
            frappe.throw("User is not Associated with any Branch.Please refresh Page")

        branch_name = branch_array[0].get("branch")

        return branch_name

@frappe.whitelist()
def getBranchRoom():
    user = frappe.session.user
    if user != "Administrator":
        sql_query = """
            SELECT b.branch , a.room
            FROM `tabURY User` AS a
            INNER JOIN `tabBranch` AS b ON a.parent = b.name
            WHERE a.user = %s
        """
        branch_array = frappe.db.sql(sql_query, user, as_dict=True)

        if not branch_array:
            branch_name = getBranch()
            return [{"name": "", "branch": branch_name}]

        branch_name = branch_array[0].get("branch")
        room_name = branch_array[0].get("room") or ""

        if not branch_name:
            branch_name = getBranch()

        return [{
            "name": room_name,
            "branch": branch_name,
        }]

@frappe.whitelist()
def getRoom():
    user = frappe.session.user
    if user != "Administrator":
        sql_query = """
            SELECT b.branch, a.room
            FROM `tabURY User` AS a
            INNER JOIN `tabBranch` AS b ON a.parent = b.name
            WHERE a.user = %s
        """
        branch_array = frappe.db.sql(sql_query, user, as_dict=True)
        
        if not branch_array:
            frappe.throw("No branch or room information found for the user. Please contact your administrator.")
        
        room_details = [
            {
                "name": row.get("room"),
                "branch": row.get("branch")
            } 
            for row in branch_array
        ]

        return room_details

@frappe.whitelist()
def getModeOfPayment():
    posDetails = getPosProfile()
    posProfile = posDetails["pos_profile"]
    posProfiles = frappe.get_doc("POS Profile", posProfile)
    mode_of_payments = posProfiles.payments
    modeOfPayments = []
    for mop in mode_of_payments:
        modeOfPayments.append(
            {"mode_of_payment": mop.mode_of_payment, "opening_amount": float(0)}
        )
    return modeOfPayments

@frappe.whitelist()
def getInvoiceForCashier(status, cashier, limit, limit_start):
    branch = getBranch()
    updatedlist = []
    limit = int(limit)+1
    limit_start = int(limit_start)
    if status == "Draft":
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number, 
                posting_date, rounded_total, order_type 
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s AND cashier = %s
            AND (invoice_printed = 1 OR (invoice_printed = 0 AND COALESCE(restaurant_table, '') = ''))
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, status, cashier, limit,limit_start),
            as_dict=True,
        )
        updatedlist.extend(invoices)
    elif status == "Unbilled":
        
        docstatus = "Draft"
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number, 
                posting_date, rounded_total, order_type 
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s AND cashier = %s
            AND (invoice_printed = 0 AND restaurant_table IS NOT NULL)
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, docstatus, cashier, limit, limit_start),
            as_dict=True,
        )
        updatedlist.extend(invoices)
    elif status == "Recently Paid":
        docstatus = "Paid"
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number,
                posting_date, rounded_total, order_type,additional_discount_percentage,discount_amount 
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s AND cashier = %s
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, docstatus, cashier, limit, limit_start),
            as_dict=True,
        )
        updatedlist.extend(invoices)    
    else:
        
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number,
                posting_date, rounded_total, order_type,additional_discount_percentage,discount_amount
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s AND cashier = %s
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, status, cashier, limit, limit_start),
            as_dict=True,
        )

        updatedlist.extend(invoices)
    if len(updatedlist) == limit and status != "Recently Paid":
            next = True
            updatedlist.pop()
    else:
            next = False   
    return  { "data":updatedlist,"next":next}



@frappe.whitelist()
def getPosInvoice(status, limit, limit_start):
    branch = getBranch()
    updatedlist = []
    limit = int(limit)+1
    limit_start = int(limit_start)
    if status == "Draft":
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number, 
                posting_date, rounded_total, order_type 
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s 
            AND (invoice_printed = 1 OR (invoice_printed = 0 AND COALESCE(restaurant_table, '') = ''))
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, status, limit,limit_start),
            as_dict=True,
        )
        updatedlist.extend(invoices)
    elif status == "Unbilled":
        
        docstatus = "Draft"
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number, 
                posting_date, rounded_total, order_type 
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s 
            AND (invoice_printed = 0 AND restaurant_table IS NOT NULL)
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, docstatus, limit, limit_start),
            as_dict=True,
        )
        updatedlist.extend(invoices)
    elif status == "Recently Paid":
        docstatus = "Paid"
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number,
                posting_date, rounded_total, order_type,additional_discount_percentage,discount_amount 
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s 
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, docstatus, limit, limit_start),
            as_dict=True,
        )
        updatedlist.extend(invoices)    
    else:
        
        invoices = frappe.db.sql(
            """
            SELECT 
                name, invoice_printed, grand_total, restaurant_table, 
                cashier, waiter, net_total, posting_time, 
                total_taxes_and_charges, customer, status, mobile_number,
                posting_date, rounded_total, order_type,additional_discount_percentage,discount_amount
            FROM `tabPOS Invoice` 
            WHERE branch = %s AND status = %s 
            ORDER BY modified desc
            LIMIT %s OFFSET %s
            """,
            (branch, status, limit, limit_start),
            as_dict=True,
        )

        updatedlist.extend(invoices)
    if len(updatedlist) == limit and status != "Recently Paid":
            next = True
            updatedlist.pop()
    else:
            next = False   
    return  { "data":updatedlist,"next":next}


@frappe.whitelist()
def searchPosInvoice(query,status):
    if not query:
        return {"data": [], "next": False}
    query = query.lower()
    filters = {"status": "Paid" if status == "Recently Paid" else status}
    
    # Add additional conditions for Unbilled status
    if status == "Unbilled":
        filters.update({
            "status":"draft",
            "restaurant_table": ["not in", [None, ""]],  # Check if restaurant_table has value
            "invoice_printed": 0  # Check if invoice_printed is 0
        })
    pos_invoices = frappe.get_all(
        "POS Invoice",
        filters=filters,           
        or_filters=[
            ["name", "like", f"%{query}%"],
            ["customer", "like", f"%{query}%"],
            ["mobile_number", "like", f"%{query}%"],
        ],
        fields=["name", "customer", "grand_total", "posting_date", "posting_time", "order_type", "restaurant_table","status","grand_total","rounded_total","net_total","mobile_number"],
        limit_page_length=10 
    )
    
    return {"data": pos_invoices, "next": len(pos_invoices) == 10}
    

@frappe.whitelist()
def get_select_field_options():
    options = frappe.get_meta("POS Invoice").get_field("order_type").options
    if options:
        return [{"name": option} for option in options.split("\n")]
    else:
        return []


@frappe.whitelist()
def fav_items(customer):
    pos_invoices = frappe.get_all(
        "POS Invoice", filters={"customer": customer}, fields=["name"]
    )
    item_qty = {}

    for invoice in pos_invoices:
        pos_invoice = frappe.get_doc("POS Invoice", invoice.name)
        for item in pos_invoice.items:
            item_name = item.item_name
            qty = item.qty
            if item_name not in item_qty:
                item_qty[item_name] = 0
            item_qty[item_name] += qty

    favorite_items = [
        {"item_name": item_name, "qty": qty} for item_name, qty in item_qty.items()
    ]
    return favorite_items

@frappe.whitelist()
def getCashier(room=None):
    branch = getBranch()
    cashier = None

    if not room:
        return cashier

    try:
        pos_opening_list = frappe.db.sql("""
            SELECT DISTINCT `tabPOS Opening Entry`.name
            FROM `tabPOS Opening Entry`
            INNER JOIN `tabMultiple Rooms`
            ON `tabMultiple Rooms`.parent = `tabPOS Opening Entry`.name
            WHERE `tabPOS Opening Entry`.branch = %s
            AND `tabPOS Opening Entry`.status = 'Open'
            AND `tabPOS Opening Entry`.docstatus = 1
            AND `tabMultiple Rooms`.room = %s
        """, (branch, room), as_dict=True)
        if pos_opening_list:
            cashier = frappe.db.get_value(
                "POS Opening Entry",
                {"name": pos_opening_list[0].name},
                "user",)
    except Exception:
        pass

    return cashier       
    

@frappe.whitelist()
def getPosProfile():
    branchName = getBranch()
    waiter = frappe.session.user
    bill_present = False
    qz_host = None
    printer = None
    cashier = None
    owner = None
    posProfile = frappe.db.exists("POS Profile", {"branch": branchName})
    pos_profiles = frappe.get_doc("POS Profile", posProfile)
    global_defaults = frappe.get_single('Global Defaults')
    disable_rounded_total = global_defaults.disable_rounded_total
    

    if pos_profiles.branch == branchName:
        pos_profile_name = pos_profiles.name
        warehouse = pos_profiles.warehouse
        branch = pos_profiles.branch
        company = pos_profiles.company
        tableAttention = pos_profiles.table_attention_time
        get_cashier = frappe.get_doc("POS Profile", pos_profile_name)
        print_format = pos_profiles.print_format
        paid_limit=pos_profiles.paid_limit
        enable_discount = pos_profiles.custom_enable_discount
        multiple_cashier = pos_profiles.custom_enable_multiple_cashier
        edit_order_type = pos_profiles.custom_edit_order_type
        enable_kot_reprint = pos_profiles.custom_enable_kot_reprint
        # Desktop POS customization settings
        # Not: `or default` ishlatilmaydi — Check field 0 qaytarsa `0 or 1` = 1 bo'ladi!
        def _chk(field, default=1):
            val = pos_profiles.get(field)
            return default if val is None else int(val)

        show_comment  = _chk("custom_show_comment", 1)
        show_ticket   = _chk("custom_show_ticket", 1)
        show_customer = _chk("custom_show_customer", 1)
        show_history  = _chk("custom_show_history", 1)
        show_shifts   = _chk("custom_show_shifts", 1)
        order_type_dine_in        = _chk("custom_order_type_dine_in", 1)
        order_type_take_away      = _chk("custom_order_type_take_away", 1)
        order_type_delivery       = _chk("custom_order_type_delivery", 0)
        order_type_delivery_saboy = _chk("custom_order_type_delivery_saboy", 0)
        order_number_type = pos_profiles.get("custom_order_number_type") or "Stiker"
        item_columns  = _chk("custom_item_columns", 0)
        company_logo   = pos_profiles.custom_company_logo or ""
        receipt_footer = pos_profiles.custom_receipt_footer or ""
        default_customer = pos_profiles.customer or ""
        if multiple_cashier:
            try:
                details = getBranchRoom()
                room = details[0].get('name')
                branch = details[0].get('branch')

                pos_opening_list = frappe.db.sql("""
                    SELECT DISTINCT `tabPOS Opening Entry`.name
                    FROM `tabPOS Opening Entry`
                    INNER JOIN `tabMultiple Rooms`
                    ON `tabMultiple Rooms`.parent = `tabPOS Opening Entry`.name
                    WHERE `tabPOS Opening Entry`.branch = %s
                    AND `tabPOS Opening Entry`.status = 'Open'
                    AND `tabPOS Opening Entry`.docstatus = 1
                    AND `tabMultiple Rooms`.room = %s
                """, (branch, room), as_dict=True)
                if pos_opening_list:
                    pos_opened_cashier = frappe.db.get_value(
                        "POS Opening Entry",
                        {"name": pos_opening_list[0].name},
                        "user",)
                else:
                    pos_opened_cashier = None
                for user_details in get_cashier.applicable_for_users:
                    if user_details.custom_main_cashier:
                        owner = user_details.user

                    if frappe.session.user == owner:
                        cashier = owner
                    else:
                        cashier = pos_opened_cashier
            except Exception:
                # Room/Multiple Rooms mavjud emas — oddiy kassir sifatida davom etish
                cashier = get_cashier.applicable_for_users[0].user if get_cashier.applicable_for_users else frappe.session.user
                owner = cashier
        else:
            cashier = get_cashier.applicable_for_users[0].user
            owner = get_cashier.applicable_for_users[0].user
        
        qz_print = pos_profiles.qz_print
        print_type = None

        for pos_profile in pos_profiles.printer_settings:
            if pos_profile.bill == 1:
                printer = pos_profile.printer
                bill_present = True
                break

        if qz_print == 1:
            print_type = "qz"
            qz_host = pos_profiles.qz_host

        elif bill_present == True:
            print_type = "network"

        else:
            print_type = "socket"

    # Payment methods — POS Profile dan
    payment_methods = [
        p.mode_of_payment for p in (pos_profiles.payments or [])
        if p.mode_of_payment
    ]

    invoice_details = {
        "pos_profile": pos_profile_name,
        "branch": branch,
        "company": company,
        "waiter": waiter,
        "warehouse": warehouse,
        "cashier": cashier,
        "print_format": print_format,
        "qz_print": qz_print,
        "qz_host": qz_host,
        "printer": printer,
        "print_type": print_type,
        "tableAttention": tableAttention,
        "paid_limit":paid_limit,
        "disable_rounded_total":disable_rounded_total,
        "enable_discount": enable_discount,
        "multiple_cashier": multiple_cashier,
        "owner": owner,
        "edit_order_type": edit_order_type,
        "enable_kot_reprint": enable_kot_reprint,
        # Desktop POS customization
        "show_comment": show_comment,
        "show_ticket": show_ticket,
        "show_customer": show_customer,
        "show_history": show_history,
        "show_shifts": show_shifts,
        "order_type_dine_in": order_type_dine_in,
        "order_type_take_away": order_type_take_away,
        "order_type_delivery": order_type_delivery,
        "order_type_delivery_saboy": order_type_delivery_saboy,
        "order_number_type": order_number_type,
        "item_columns": item_columns,
        "company_logo": company_logo,
        "receipt_footer": receipt_footer,
        "default_customer": default_customer,
        "payment_methods": payment_methods,
        "cashiers": get_pos_cashiers(),
    }

    return invoice_details


@frappe.whitelist()
def get_pos_cashiers():
    """Ushbu filialga tegishli faol kassirlar ro'yxati."""
    branch = getBranch()
    pos_profile = frappe.db.get_value("POS Profile", {"branch": branch}, "name")
    if not pos_profile:
        return []

    profile_doc = frappe.get_doc("POS Profile", pos_profile)
    branch_users = [u.user for u in profile_doc.applicable_for_users]

    if not branch_users:
        return []

    cashiers = frappe.get_all(
        "URY POS Cashier",
        filters={"user": ["in", branch_users], "active": 1},
        fields=["name", "full_name", "user", "role"],
    )

    # Har bir kassir uchun PIN ni plain-text sifatida yuborish
    from frappe.utils.password import get_decrypted_password
    for c in cashiers:
        try:
            c["pin"] = get_decrypted_password("URY POS Cashier", c["name"], "pin") or ""
        except Exception:
            c["pin"] = ""
        # Role default safety — eski yozuvlar bo'sh bo'lishi mumkin
        if not c.get("role"):
            c["role"] = "Kassir"

    return cashiers


@frappe.whitelist()
def getPosInvoiceItems(invoice):
    itemDetails = []
    taxDetails = []
    orderdItems = frappe.get_doc("POS Invoice", invoice)
    posItems = orderdItems.items
    for items in posItems:
        item_name = items.item_name
        qty = items.qty
        amount = items.rate
        itemDetails.append(
            {
                "item_name": item_name,
                "qty": qty,
                "amount": amount,
            }
        )
    taxDetail = orderdItems.taxes
    for tax in taxDetail:
        description = tax.description
        rate = tax.tax_amount
        taxDetails.append(
            {
                "description": description,
                "rate": rate,
            }
        )
    return itemDetails, taxDetails


@frappe.whitelist()
def posOpening():
    branchName = getBranch()
    pos_opening_list = frappe.get_all(
        "POS Opening Entry",
        fields=["name", "docstatus", "status", "posting_date"],
        filters={"branch": branchName},
    )
    flag = 1
    for pos_opening in pos_opening_list:
        if pos_opening.status == "Open" and pos_opening.docstatus == 1:
            flag = 0
    if flag == 1:
        frappe.msgprint(title="Message", indicator="red", msg=("Please Open POS Entry"))
    return flag


@frappe.whitelist()
def checkPosOpening():
    """Desktop POS uchun: ochiq kassa borligini tekshirish"""
    try:
        branchName = getBranch()
    except Exception:
        return {"status": "no_branch", "opening_entry": None}

    pos_opening_list = frappe.get_all(
        "POS Opening Entry",
        fields=["name", "user", "posting_date"],
        filters={
            "branch": branchName,
            "status": "Open",
            "docstatus": 1,
        },
        limit_page_length=1,
    )

    if pos_opening_list:
        return {
            "status": "open",
            "opening_entry": pos_opening_list[0].name,
            "user": pos_opening_list[0].user,
        }
    return {"status": "closed", "opening_entry": None}


@frappe.whitelist()
def createPosOpening(pos_profile, company, balance_details):
    """Desktop POS uchun: yangi kassa ochish"""
    import json as _json
    if isinstance(balance_details, str):
        balance_details = _json.loads(balance_details)

    # Desktop POS — restaurant hooklar (main cashier check, room setting) o'tkazib yuborilsin
    frappe.flags.desktop_pos_opening = True

    opening = frappe.new_doc("POS Opening Entry")
    opening.pos_profile = pos_profile
    opening.company = company
    opening.user = frappe.session.user
    opening.posting_date = frappe.utils.nowdate()
    opening.set_posting_time = 1
    opening.posting_time = frappe.utils.nowtime()
    opening.period_start_date = frappe.utils.now()

    for bd in balance_details:
        opening.append("balance_details", {
            "mode_of_payment": bd.get("mode_of_payment"),
            "opening_amount": float(bd.get("opening_amount", 0)),
        })

    opening.insert()
    opening.submit()

    return {
        "name": opening.name,
        "status": opening.status,
        "posting_date": str(opening.posting_date),
    }


@frappe.whitelist()
def getPosClosingData(pos_opening_entry):
    """Desktop POS uchun: kassa yopish uchun ma'lumotlarni hisoblash"""
    opening = frappe.get_doc("POS Opening Entry", pos_opening_entry)

    # Shu opening entry ga tegishli POS Invoice larni topish
    invoices = _get_invoices_for_opening(opening)

    # To'lov turlarini yig'ish
    payment_totals = {}
    for inv in invoices:
        payments = frappe.get_all(
            "Sales Invoice Payment",
            filters={"parent": inv.name, "parenttype": "POS Invoice"},
            fields=["mode_of_payment", "amount"],
        )
        for p in payments:
            mop = p.mode_of_payment
            payment_totals[mop] = payment_totals.get(mop, 0) + float(p.amount)

    # Opening amounts
    opening_amounts = {}
    for bd in opening.balance_details:
        opening_amounts[bd.mode_of_payment] = float(bd.opening_amount)

    # Reconciliation tuzish
    reconciliation = []
    all_modes = set(list(opening_amounts.keys()) + list(payment_totals.keys()))
    for mop in sorted(all_modes):
        opening_amt = opening_amounts.get(mop, 0)
        expected = opening_amt + payment_totals.get(mop, 0)
        reconciliation.append({
            "mode_of_payment": mop,
            "opening_amount": opening_amt,
            "expected_amount": expected,
        })

    return {
        "opening_entry": pos_opening_entry,
        "total_invoices": len(invoices),
        "reconciliation": reconciliation,
    }


def _get_invoices_for_opening(opening):
    """POS Opening Entry ga tegishli invoice larni topish.
    Avval pos_opening_entry ustuni orqali, agar ustun mavjud bo'lmasa
    user + pos_profile + sana bo'yicha qidiradi."""
    try:
        return frappe.get_all(
            "POS Invoice",
            filters={
                "pos_opening_entry": opening.name,
                "docstatus": 1,
                "status": ["!=", "Consolidated"],
            },
            fields=["name", "grand_total", "paid_amount", "posting_date", "customer"],
        )
    except Exception:
        # pos_opening_entry ustuni mavjud emas — user + pos_profile + sana orqali topish
        return frappe.get_all(
            "POS Invoice",
            filters={
                "owner": opening.user,
                "pos_profile": opening.pos_profile,
                "posting_date": opening.posting_date,
                "docstatus": 1,
                "status": ["!=", "Consolidated"],
            },
            fields=["name", "grand_total", "paid_amount", "posting_date", "customer"],
        )


@frappe.whitelist()
def createPosClosing(pos_opening_entry, payment_reconciliation):
    """Desktop POS uchun: kassani yopish"""
    import json as _json
    if isinstance(payment_reconciliation, str):
        payment_reconciliation = _json.loads(payment_reconciliation)

    # Desktop POS — restaurant hooklar (sub cashier, sub pos closing) o'tkazib yuborilsin
    frappe.flags.desktop_pos_closing = True

    closing = frappe.new_doc("POS Closing Entry")
    closing.pos_opening_entry = pos_opening_entry
    closing.posting_date = frappe.utils.nowdate()
    closing.posting_time = frappe.utils.nowtime()

    # Opening entry dan pos_profile, company, user olish
    opening = frappe.get_doc("POS Opening Entry", pos_opening_entry)
    closing.pos_profile = opening.pos_profile
    closing.company = opening.company
    closing.user = opening.user
    closing.period_start_date = opening.posting_date
    closing.period_end_date = frappe.utils.nowdate()

    for pr in payment_reconciliation:
        closing.append("payment_reconciliation", {
            "mode_of_payment": pr.get("mode_of_payment"),
            "opening_amount": float(pr.get("opening_amount", 0)),
            "expected_amount": float(pr.get("expected_amount", 0)),
            "closing_amount": float(pr.get("closing_amount", 0)),
            "difference": float(pr.get("expected_amount", 0)) - float(pr.get("closing_amount", 0)),
        })

    # POS Invoice larni qo'shish
    invoices = _get_invoices_for_opening(opening)
    for inv in invoices:
        closing.append("pos_transactions", {
            "pos_invoice": inv.name,
            "posting_date": inv.posting_date,
            "grand_total": inv.grand_total,
            "customer": inv.customer,
        })

    closing.insert()
    frappe.db.commit()
    closing.submit()

    # ── Z-Report uchun ma'lumotlarni hisoblash ──────────────────────
    # Kassirga ekranda yashirilgan, lekin printerda to'liq chiqadigan ma'lumotlar
    _CASH_KEYS = {"cash", "naqd", "naqd pul", "наличные", "cash in hand"}

    expected_cash = 0.0
    actual_cash = 0.0
    total_sales = 0.0

    full_payments = []
    for pr in payment_reconciliation:
        mop = pr.get("mode_of_payment", "")
        expected_amt = float(pr.get("expected_amount", 0))
        closing_amt = float(pr.get("closing_amount", 0))
        total_sales += expected_amt

        if mop.lower().strip() in _CASH_KEYS:
            expected_cash = expected_amt
            actual_cash = closing_amt

        full_payments.append({
            "mode_of_payment": mop,
            "expected_amount": expected_amt,
            "closing_amount": closing_amt,
        })

    # Agar hech biri naqd emas bo'lsa — birinchisi naqd hisobilanadi
    if expected_cash == 0.0 and payment_reconciliation:
        first = payment_reconciliation[0]
        expected_cash = float(first.get("expected_amount", 0))
        actual_cash = float(first.get("closing_amount", 0))

    cash_diff = actual_cash - expected_cash

    return {
        "name": closing.name,
        "status": "Submitted",
        # Z-report uchun to'liq ma'lumotlar (ekranda yashirilgan, printerda ko'rinadigan)
        "z_report_data": {
            "total_invoices": len(invoices),
            "total_sales": total_sales,
            "expected_cash": expected_cash,
            "actual_cash": actual_cash,
            "cash_diff": cash_diff,
            "payments": full_payments,
        },
    }


@frappe.whitelist()
def getAggregator():
    branchName = getBranch()
    aggregatorList = frappe.get_all(
        "Aggregator Settings",
        fields=["customer"],
        filters={"parent": branchName, "parenttype": "Branch"},
    )
    return aggregatorList


@frappe.whitelist()
def getAggregatorItem(aggregator):
    branchName = getBranch()
    aggregatorItem = []
    aggregatorItemList = []
    priceList = frappe.db.get_value(
        "Aggregator Settings",
        {"customer": aggregator, "parent": branchName, "parenttype": "Branch"},
        "price_list",
    )
    aggregatorItem = frappe.get_all(
        "Item Price",
        fields=["item_code", "item_name", "price_list_rate"],
        filters={"selling": 1, "price_list": priceList},
    )
    aggregatorItemList = [
        {
            "item": item.item_code,
            "item_name": item.item_name,
            "rate": item.price_list_rate,
            "item_image": frappe.db.get_value("Item", item.item, "image"),
        }
        for item in aggregatorItem
        if not frappe.db.get_value("Item", item.item_code, "disabled")
    ]
    return aggregatorItemList

@frappe.whitelist()
def getAggregatorMOP(aggregator):
    branchName = getBranch()
    
    modeOfPayment = frappe.db.get_value(
        "Aggregator Settings",
        {"customer": aggregator, "parent": branchName, "parenttype": "Branch"},
        "mode_of_payments",
    )
    modeOfPaymentsList = []
    modeOfPaymentsList.append(
            {"mode_of_payment": modeOfPayment, "opening_amount": float(0)}
    )
    return modeOfPaymentsList
@frappe.whitelist()
def create_customer(customer_name, mobile_number=None, customer_group="Individual", territory="India"):
    if not customer_name:
        frappe.throw("Customer name is required")
    if not mobile_number:
        frappe.throw("Mobile Number is required")
    try:
        validate_phone_number(mobile_number, throw=True)
    except Exception:
        frappe.throw("Invalid mobile number format")

    """Create a new customer"""
    try:
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "mobile_number": mobile_number,
            "customer_group": customer_group,
            "territory": territory
        })
        customer.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": "Customer created successfully",
            "customer_name": customer_name,
            "mobile_number": mobile_number,
            "customer_group": customer_group,
            "territory": territory
        }

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Customer Creation Failed")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def validate_pos_close(pos_profile): 
    enable_unclosed_pos_check = frappe.db.get_value("POS Profile",pos_profile,"custom_daily_pos_close")
    
    if enable_unclosed_pos_check:
        current_datetime = frappe.utils.now_datetime()
        start_of_day = current_datetime.replace(hour=5, minute=0, second=0, microsecond=0)
        
        if current_datetime > start_of_day:
            previous_day = start_of_day - timedelta(days=1)
            
        else:
            previous_day = start_of_day
    
        unclosed_pos_opening = frappe.db.exists(
            "POS Opening Entry",
            {
                "posting_date": previous_day.date(),
                "status": "Open",
                "pos_profile": pos_profile,
                "docstatus": 1
            }
        )
    
        if unclosed_pos_opening:
            return "Failed"
        
        return "Success"
    
    return "Success"


@frappe.whitelist()
def get_printer_config(pos_profile):
    """Desktop POS uchun printer konfiguratsiyasini qaytaradi.

    Har bir printer uchun {name, driver, width_mm} qaytariladi:
      - driver: "escpos" | "tspl" (DocType da "ESC/POS"|"TSPL" — kichik harfga)
      - width_mm: qog'oz kengligi (default 58)
    """
    def _norm_driver(val):
        v = (val or "").strip().lower()
        if v in ("tspl", "stiker", "label"):
            return "tspl"
        return "escpos"

    def _norm_codepage(val):
        v = (val or "").strip().lower().replace("-", "")
        if v in ("cp866", "ibm866", "pc866", "866"):
            return "cp866"
        return "cp1251"

    def _expand_groups(group_names):
        """Tanlangan Item Group larni descendant lar bilan kengaytirish.

        Agar parent (is_group=1) tanlansa — uning ostidagi barcha leaf
        sub-grouplar avtomatik qo'shiladi. Leaf (is_group=0) bo'lsa —
        o'zi qoladi. Bu Production Unit konfiguratsiyasini soddalashtiradi:
        `All Item Groups` tanlash = barcha mahsulotlar shu unitga boradi.
        """
        if not group_names:
            return []
        result = set()
        for g in group_names:
            if not g:
                continue
            ig = frappe.db.get_value(
                "Item Group", g, ["is_group", "lft", "rgt"], as_dict=True
            )
            if not ig:
                continue
            if ig.is_group:
                # Barcha descendant leaf grouplar (lft/rgt nested-set bilan)
                descendants = frappe.get_all(
                    "Item Group",
                    filters={
                        "lft": [">", ig.lft],
                        "rgt": ["<", ig.rgt],
                        "is_group": 0,
                    },
                    pluck="name",
                )
                result.update(descendants)
            else:
                result.add(g)
        return sorted(result)

    profile_doc = frappe.get_doc("POS Profile", pos_profile)

    customer_printer = {
        "name": getattr(profile_doc, "customer_qz_printer_name", "") or "",
        "driver": _norm_driver(getattr(profile_doc, "customer_qz_printer_driver", "")),
        "width_mm": int(getattr(profile_doc, "customer_qz_printer_width", 0) or 58),
        "codepage": _norm_codepage(getattr(profile_doc, "customer_qz_printer_codepage", "")),
    }

    units = frappe.get_all(
        "URY Production Unit",
        filters={"pos_profile": pos_profile},
        fields=[
            "name", "production", "qz_printer_name",
            "qz_printer_driver", "qz_printer_width", "qz_printer_codepage",
        ],
    )

    production_units = []
    for unit in units:
        raw_groups = frappe.get_all(
            "URY Production Item Groups",
            filters={"parent": unit.name},
            fields=["item_group"],
            pluck="item_group",
        )
        # Parent group tanlangan bo'lsa, ostidagi leaf sub-grouplarni
        # avtomatik qo'shamiz (rekursiv expansion)
        item_groups = _expand_groups(raw_groups)
        production_units.append({
            "name": unit.production or unit.name,
            "printer_name": unit.qz_printer_name or "",
            "driver": _norm_driver(unit.qz_printer_driver),
            "width_mm": int(unit.qz_printer_width or 58),
            "codepage": _norm_codepage(unit.qz_printer_codepage),
            "item_groups": item_groups,
        })

    return {
        "customer_printer": customer_printer,
        "production_units": production_units,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  URY Table / Room API — Stol rejimi (TZ 4.1.3)
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def getTables(branch=None, room=None):
    """Filial (yoki xona) bo'yicha stollar — barchasi (band va bo'sh).

    Args:
        branch: Filial nomi (None bo'lsa joriy session foydalanuvchidan olinadi)
        room: URY Room nomi (None bo'lsa hamma xonalar)

    Returns:
        Stollar ro'yxati layout ma'lumotlari bilan.
    """
    if not branch:
        branch = getBranch()
    filters = {"branch": branch}
    if room:
        filters["restaurant_room"] = room

    tables = frappe.get_all(
        "URY Table",
        filters=filters,
        fields=[
            "name", "restaurant_room", "no_of_seats", "occupied",
            "latest_invoice_time", "is_take_away",
            "layout_x", "layout_y", "layout_width", "layout_height",
            "table_shape",
        ],
        order_by="restaurant_room asc, name asc",
        limit_page_length=500,
    )
    return tables


@frappe.whitelist()
def getRoomsForBranch(branch=None):
    """Filial xonalari ro'yxati.

    Multiple Cashier rejimida kassirning POS Opening Entry'ga
    biriktirilgan xonalari qaytariladi. Aks holda — filialdagi barcha
    xonalar.
    """
    if not branch:
        branch = getBranch()

    # Joriy POS Opening Entry'da Multiple Rooms biriktirilganmi?
    user = frappe.session.user
    opening_name = frappe.db.get_value(
        "POS Opening Entry",
        {"branch": branch, "status": "Open", "docstatus": 1, "user": user},
        "name",
    )
    if opening_name:
        multi_rooms = frappe.get_all(
            "Multiple Rooms",
            filters={"parent": opening_name},
            pluck="room",
        )
        if multi_rooms:
            return frappe.get_all(
                "URY Room",
                filters={"name": ["in", multi_rooms], "branch": branch},
                fields=["name", "branch", "room_type"],
                order_by="name asc",
            )

    # Fallback — filialdagi barcha xonalar
    return frappe.get_all(
        "URY Room",
        filters={"branch": branch},
        fields=["name", "branch", "room_type"],
        order_by="name asc",
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Pending Orders API — To'lov kutilayotgan Draft invoicelar (TZ 4.2.4)
# ═══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def getPendingOrders(order_type=None, only_mine=0, mine_cashier_name=None,
                     limit=50, limit_start=0):
    """Filial bo'yicha to'lov kutilayotgan buyurtmalar (Draft, invoice_printed=0).

    Args:
        order_type: filter by order_type ("Dine In", "Take Away", ...). None = barchasi.
        only_mine: 1 = faqat mine_cashier_name ga tegishli (ofitsant uchun)
        mine_cashier_name: custom_active_cashier qiymati (full_name)
        limit / limit_start: paginatsiya
    """
    branch = getBranch()
    where = [
        "branch = %s",
        "status = 'Draft'",
        "docstatus = 0",
        "invoice_printed = 0",
    ]
    params = [branch]
    if order_type:
        where.append("order_type = %s")
        params.append(order_type)
    if int(only_mine or 0) and mine_cashier_name:
        where.append("custom_active_cashier = %s")
        params.append(mine_cashier_name)

    rows = frappe.db.sql(
        f"""
        SELECT
            name, custom_ticket_number, restaurant_table, order_type,
            customer, mobile_number, custom_active_cashier,
            custom_active_cashier_role,
            grand_total, net_total, rounded_total,
            creation, modified, posting_date, posting_time
        FROM `tabPOS Invoice`
        WHERE {" AND ".join(where)}
        ORDER BY modified DESC
        LIMIT %s OFFSET %s
        """,
        params + [int(limit), int(limit_start)],
        as_dict=True,
    )

    # Stol bo'lsa restaurant_room ham qo'shamiz (display uchun)
    table_names = [r["restaurant_table"] for r in rows if r.get("restaurant_table")]
    rooms_map = {}
    if table_names:
        ts = frappe.db.get_all(
            "URY Table",
            filters={"name": ["in", table_names]},
            fields=["name", "restaurant_room"],
        )
        rooms_map = {t.name: t.restaurant_room for t in ts}
    for r in rows:
        r["room"] = rooms_map.get(r.get("restaurant_table"), "") or ""

    return rows


@frappe.whitelist()
def getPendingOrderCounts(only_mine=0, mine_cashier_name=None):
    """Filter chiplari uchun har order_type bo'yicha son.

    Returns: {"all": 12, "Dine In": 5, "Take Away": 4, "Delivery": 3, ...}
    """
    branch = getBranch()
    where = [
        "branch = %s",
        "status = 'Draft'",
        "docstatus = 0",
        "invoice_printed = 0",
    ]
    params = [branch]
    if int(only_mine or 0) and mine_cashier_name:
        where.append("custom_active_cashier = %s")
        params.append(mine_cashier_name)

    rows = frappe.db.sql(
        f"""
        SELECT order_type, COUNT(*) AS cnt
        FROM `tabPOS Invoice`
        WHERE {" AND ".join(where)}
        GROUP BY order_type
        """,
        params,
        as_dict=True,
    )
    counts = {"all": 0}
    for r in rows:
        ot = r.get("order_type") or "Unknown"
        cnt = int(r.get("cnt") or 0)
        counts[ot] = cnt
        counts["all"] += cnt
    return counts


@frappe.whitelist()
def getPendingOrderDetail(invoice):
    """Pending zakaz uchun to'liq detallar (items + ma'lumotlar).

    PendingOrdersWindow da "💰 To'lov" bossadi → bu API chaqirilib
    items olinadi va CheckoutWindow ochiladi.
    """
    if not invoice:
        frappe.throw(_("Invoice nomi ko'rsatilmagan"))

    doc = frappe.get_doc("POS Invoice", invoice)
    if doc.docstatus != 0:
        frappe.throw(_("Buyurtma allaqachon yakunlangan"))

    items = []
    for it in doc.items:
        items.append({
            "item_code": it.item_code,
            "item_name": it.item_name,
            "qty": float(it.qty or 0),
            "rate": float(it.rate or 0),
            "amount": float(it.amount or 0),
        })
    return {
        "name": doc.name,
        "customer": doc.customer,
        "order_type": doc.order_type,
        "restaurant_table": doc.restaurant_table,
        "custom_ticket_number": doc.custom_ticket_number,
        "custom_active_cashier": doc.custom_active_cashier,
        "custom_active_cashier_role": getattr(doc, "custom_active_cashier_role", "") or "",
        "custom_comments": doc.custom_comments,
        "grand_total": float(doc.grand_total or 0),
        "net_total": float(doc.net_total or 0),
        "rounded_total": float(doc.rounded_total or 0),
        "items": items,
    }


@frappe.whitelist()
def cancelPendingOrder(invoice, reason):
    """Pending (Draft) buyurtmani bekor qilish.

    Effects:
    - POS Invoice cancel/delete (docstatus 0 → mavjudligi sababli o'chiriladi)
    - Cancel KOT (mavjud cancel_kot mantiqi)
    - Stol bo'shaydi (on_cancel hook orqali — Phase 2)
    """
    if not invoice:
        frappe.throw(_("Invoice nomi ko'rsatilmagan"))
    if not reason or not str(reason).strip():
        frappe.throw(_("Bekor qilish sababi kiritilishi shart"))

    doc = frappe.get_doc("POS Invoice", invoice)
    if doc.docstatus != 0:
        frappe.throw(_("Faqat Draft (to'lanmagan) buyurtmalarni bekor qilish mumkin"))

    # Sababni saqlash (audit uchun)
    try:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "POS Invoice",
            "reference_name": invoice,
            "content": f"Pending zakaz bekor qilindi. Sabab: {reason}. Foydalanuvchi: {frappe.session.user}",
        }).insert(ignore_permissions=True)
    except Exception:
        pass

    # Cancel KOT
    try:
        from ury.ury.doctype.ury_order.ury_order import cancel_kot
        cancel_kot(invoice)
    except Exception as e:
        frappe.log_error(f"cancel_kot xatosi: {e}", "cancelPendingOrder")

    # Stolni bo'shatish (qo'lda — on_cancel hook hali yo'q Phase 1 da)
    if doc.restaurant_table:
        try:
            frappe.db.set_value("URY Table", doc.restaurant_table, {
                "occupied": 0,
                "latest_invoice_time": None,
            })
        except Exception:
            pass

    # Draft invoice ni o'chirish (docstatus=0 cancel qilolmaydi, faqat delete)
    frappe.delete_doc("POS Invoice", invoice, ignore_permissions=True, force=1)

    # Realtime — boshqa POSlarga
    frappe.publish_realtime("pending_order_cancelled", {
        "invoice": invoice,
        "reason": reason,
    }, after_commit=True)

    return {"status": "ok", "invoice": invoice}


@frappe.whitelist()
def freeTable(table, reason):
    """Stolni qo'lda bo'shatish (TablePicker dagi '🔓 Bo'shatish').

    Faqat kassir yoki manager ishlatishi kerak.
    """
    if not table:
        frappe.throw(_("Stol ko'rsatilmagan"))
    if not reason or not str(reason).strip():
        frappe.throw(_("Bo'shatish sababi kiritilishi shart"))

    if not frappe.has_permission("URY Table", "write"):
        frappe.throw(_("Sizda stol bo'shatish huquqi yo'q"))

    # Stol mavjudligi tekshiruvi
    if not frappe.db.exists("URY Table", table):
        frappe.throw(_("Stol topilmadi: {0}").format(table))

    frappe.db.set_value("URY Table", table, {
        "occupied": 0,
        "latest_invoice_time": None,
    })

    # Audit log — Comment sifatida saqlash (alohida log doctype shart emas)
    try:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "URY Table",
            "reference_name": table,
            "content": f"Stol qo'lda bo'shatildi. Sabab: {reason}. Foydalanuvchi: {frappe.session.user}",
        }).insert(ignore_permissions=True)
    except Exception:
        pass

    # Real-time event — boshqa POSlarga
    frappe.publish_realtime("table_freed", {
        "table": table,
        "by": frappe.session.user,
        "reason": reason,
    }, after_commit=True)

    return {"status": "ok", "table": table}


@frappe.whitelist()
def cleanupOrphanTables(branch=None):
    """Occupied=1 lekin active Draft invoice yo'q stollarni bo'shatish (TZ 4.6.3).

    POS Closing oldida ishlatiladi — server crash yoki cancel qilinmagan Draft
    tufayli stol band qolib ketgan bo'lishi mumkin.
    """
    if not branch:
        branch = getBranch()

    tables = frappe.get_all(
        "URY Table",
        filters={"branch": branch, "occupied": 1},
        pluck="name",
    )
    freed = []
    for t in tables:
        has_active = frappe.db.exists("POS Invoice", {
            "restaurant_table": t,
            "docstatus": 0,
            "status": "Draft",
            "invoice_printed": 0,
        })
        if not has_active:
            frappe.db.set_value("URY Table", t, {
                "occupied": 0,
                "latest_invoice_time": None,
            })
            freed.append(t)
            frappe.publish_realtime("table_freed", {
                "table": t,
                "by": "cleanup",
                "reason": "orphan",
            }, after_commit=True)

    return {"freed_count": len(freed), "tables": freed}


@frappe.whitelist()
def cancelAllPendingDrafts(branch=None, reason="POS Closing — force"):
    """Filial bo'yicha barcha Draft (to'lanmagan) buyurtmalarni majburiy bekor
    qilish (TZ 4.6.1 — POS Closing force mode).

    Diqqat: faqat admin/manager rolida chaqirilishi kerak — client tomon
    admin PIN bilan tasdiqdan keyin chaqiradi.
    """
    if not branch:
        branch = getBranch()

    drafts = frappe.db.sql_list(
        """
        SELECT name FROM `tabPOS Invoice`
        WHERE branch = %s AND docstatus = 0 AND status = 'Draft'
          AND invoice_printed = 0
        """,
        (branch,),
    )

    cancelled = []
    for inv in drafts:
        try:
            doc = frappe.get_doc("POS Invoice", inv)
            # Cancel KOT (mavjud mantiq)
            try:
                from ury.ury.doctype.ury_order.ury_order import cancel_kot
                cancel_kot(inv)
            except Exception as e:
                frappe.log_error(f"cancel_kot xatosi: {e}", "cancelAllPendingDrafts")

            # Stolni bo'shatish
            if doc.restaurant_table:
                frappe.db.set_value("URY Table", doc.restaurant_table, {
                    "occupied": 0,
                    "latest_invoice_time": None,
                })

            # Audit comment
            try:
                frappe.get_doc({
                    "doctype": "Comment",
                    "comment_type": "Comment",
                    "reference_doctype": "POS Invoice",
                    "reference_name": inv,
                    "content": f"Force cancel (POS Closing). Sabab: {reason}. Foydalanuvchi: {frappe.session.user}",
                }).insert(ignore_permissions=True)
            except Exception:
                pass

            frappe.delete_doc("POS Invoice", inv, ignore_permissions=True, force=1)
            cancelled.append(inv)
        except Exception as e:
            frappe.log_error(f"cancelAllPendingDrafts {inv}: {e}", "POS Closing")

    if cancelled:
        frappe.publish_realtime("pending_orders_force_cancelled", {
            "invoices": cancelled,
            "by": frappe.session.user,
        }, after_commit=True)

    return {"cancelled_count": len(cancelled), "invoices": cancelled}


