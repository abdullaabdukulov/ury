import frappe
from frappe.model.document import Document


class URYPOSCashier(Document):
    def before_save(self):
        # PIN 4 xonali bo'lishi shart
        if self.pin and (not self.pin.isdigit() or len(self.pin) != 4):
            frappe.throw("PIN faqat 4 ta raqamdan iborat bo'lishi kerak.")
