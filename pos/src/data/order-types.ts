import { Phone, ShoppingBag, Truck, Utensils } from "lucide-react";

export type OrderType = "Shu yerda" | "Saboy" | "Dastavka" | "Dastavka Saboy";

export type OrderTypes= {
    label: string;
    value: OrderType;
    icon: React.ElementType;
}

export const ORDER_TYPES: OrderTypes[] = [
    {
        label: "Shu yerda",
        value: "Shu yerda",
        icon: Utensils
    },
    {
        label: "Saboy",
        value: "Saboy",
        icon: ShoppingBag
    },
    {
        label: "Dastavka",
        value: "Dastavka",
        icon: Truck
    },
    {
        label: "Dastavka Saboy",
        value: "Dastavka Saboy",
        icon: Phone
    }
]

export const DINE_IN = "Shu yerda"
export const DEFAULT_ORDER_TYPE = "Shu yerda"
export const DEFAULT_PAYMENT_MODE = "Cash"
export const TICKET_ORDER_TYPES: OrderType[] = ["Shu yerda", "Saboy"]

export type OrderStatusType = "Draft" | "Unbilled" | "Recently Paid" | "Paid" | "Consolidated" | "Return";

// Base status types that are always available
export const BASE_ORDER_STATUS_TYPES = [
    {
        label: "Draft",
        value: "Draft"
    },
    {
        label: "Unbilled",
        value: "Unbilled"
    }
];

// Recently Paid status that appears when paid_limit > 0
export const RECENTLY_PAID_STATUS_TYPE = [
    {
        label: "Recently Paid",
        value: "Recently Paid"
    }
];

// Extended status types that are only available when view_all_status is enabled
export const EXTENDED_ORDER_STATUS_TYPES = [
    {
        label: "Paid",
        value: "Paid"
    },
    {
        label: "Consolidated",
        value: "Consolidated"
    },
    {
        label: "Return",
        value: "Return"
    }
];

// Function to get order status types based on POS profile settings
export const getOrderStatusTypes = (viewAllStatus?: number, paidLimit?: number) => {
    let statusTypes = [...BASE_ORDER_STATUS_TYPES];

    // Add Recently Paid if paid_limit > 0
    if (paidLimit && paidLimit > 0) {
        statusTypes.push(...RECENTLY_PAID_STATUS_TYPE);
    }

    // Add extended statuses if view_all_status is enabled
    if (viewAllStatus === 1) {
        statusTypes.push(...EXTENDED_ORDER_STATUS_TYPES);
    }

    return statusTypes;
};

// Legacy export for backward compatibility
export const ORDER_STATUS_TYPES = BASE_ORDER_STATUS_TYPES;
