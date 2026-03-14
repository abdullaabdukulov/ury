import { StateCreator } from 'zustand';
import { OrderType } from '../../data/order-types';
import { call } from '../../lib/frappe-sdk';
import { getPOSInvoices, getPOSInvoiceItems, POSInvoiceItem, POSInvoiceTax } from '../../lib/invoice-api';
import { searchPosInvoice } from '../../lib/invoice-api';
import { getQueue } from '../../lib/offline-queue';

export interface POSInvoice {
  name: string;
  invoice_printed: number;
  grand_total: number;
  restaurant_table: string | null;
  cashier: string;
  waiter: string;
  net_total: number;
  posting_time: string;
  total_taxes_and_charges: number;
  customer: string;
  status: 'Draft' | 'Unbilled' | 'Recently Paid' | 'Paid' | 'Consolidated' | 'Return';
  mobile_number: string;
  posting_date: string;
  rounded_total: number;
  order_type: OrderType;
  // Offline orders uchun maxsus bayroq
  _offline?: boolean;
  _offlineItems?: POSInvoiceItem[];
}

export interface OrdersState {
  orders: POSInvoice[];
  orderLoading: boolean;
  error: string | null;
  pagination: {
    currentPage: number;
    hasNextPage: boolean;
    itemsPerPage: number;
  };
  selectedStatus: 'Draft' | 'Unbilled' | 'Recently Paid' | 'Paid' | 'Consolidated' | 'Return';
  selectedOrder: POSInvoice | null;
  selectedOrderItems: POSInvoiceItem[];
  selectedOrderTaxes: POSInvoiceTax[];
  selectedOrderLoading: boolean;
  selectedOrderError: string | null;
  orderSearchQuery: string;
}

export interface OrdersActions {
  fetchOrders: (page?: number) => Promise<void>;
  updateOrderStatus: (orderId: string, status: POSInvoice['status']) => Promise<void>;
  goToNextPage: () => Promise<void>;
  goToPreviousPage: () => Promise<void>;
  setSelectedStatus: (status: POSInvoice['status']) => Promise<void>;
  selectOrder: (order: POSInvoice) => Promise<void>;
  clearSelectedOrder: () => void;
  setOrderSearchQuery: (query: string) => void;
}

export type OrdersSlice = OrdersState & OrdersActions;

const ITEMS_PER_PAGE = 10;

/** Offline queue orderlarini POSInvoice formatiga o'girish */
function buildOfflineOrders(): POSInvoice[] {
  return getQueue()
    .filter(e => e.status === 'pending')
    .map(e => {
      const total = e.orderData.items.reduce((s, i) => s + (i.rate * i.qty), 0);
      return {
        name: e.id,
        invoice_printed: 0,
        grand_total: total,
        restaurant_table: null,
        cashier: e.orderData.cashier || '',
        waiter: e.orderData.waiter || '',
        net_total: total,
        posting_time: new Date(e.timestamp).toTimeString().slice(0, 8),
        total_taxes_and_charges: 0,
        customer: e.orderData.customer || '',
        status: 'Draft' as const,
        mobile_number: '',
        posting_date: new Date(e.timestamp).toISOString().slice(0, 10),
        rounded_total: total,
        order_type: e.orderData.order_type as OrderType,
        _offline: true,
        _offlineItems: e.orderData.items.map(i => ({
          item_name: i.item_name,
          qty: i.qty,
          amount: i.rate * i.qty,
        })),
      };
    });
}

export const createOrdersSlice: StateCreator<
  OrdersSlice,
  [],
  [],
  OrdersSlice
> = (set, get) => ({
  // Initial state
  orders: [],
  orderLoading: false,
  error: null,
  pagination: {
    currentPage: 1,
    hasNextPage: false,
    itemsPerPage: ITEMS_PER_PAGE,
  },
  selectedStatus: 'Draft',
  selectedOrder: null,
  selectedOrderItems: [],
  selectedOrderTaxes: [],
  selectedOrderLoading: false,
  selectedOrderError: null,
  orderSearchQuery: '',

  // Actions
  fetchOrders: async (page = 1) => {
    try {
      set({ orderLoading: true, error: null });
      const { orderSearchQuery, selectedStatus } = get();

      const posProfile = sessionStorage.getItem('posProfile');
      const profile = posProfile ? JSON.parse(posProfile) : null;
      const paidLimit = profile?.paid_limit;

      if (orderSearchQuery && orderSearchQuery.trim()) {
        const res = await searchPosInvoice(orderSearchQuery, selectedStatus);
        const serverOrders: POSInvoice[] = res.data || [];
        // Qidiruv paytida offline orderlarni ham qo'shish (faqat Draft filtrida)
        const offlineOrders = selectedStatus === 'Draft' ? buildOfflineOrders() : [];
        set({
          orders: [...offlineOrders, ...serverOrders],
          pagination: { currentPage: 1, hasNextPage: false, itemsPerPage: ITEMS_PER_PAGE },
          orderLoading: false
        });
        return;
      }

      const limitStart = (page - 1) * ITEMS_PER_PAGE;
      const { invoices, hasMore } = await getPOSInvoices({
        status: selectedStatus,
        limit: ITEMS_PER_PAGE,
        limit_start: limitStart,
        paid_limit: paidLimit
      });

      // Draft status bo'lsa offline queue orderlarini prepend qilish
      const offlineOrders = selectedStatus === 'Draft' ? buildOfflineOrders() : [];

      set({
        orders: [...offlineOrders, ...invoices],
        pagination: { currentPage: page, hasNextPage: hasMore, itemsPerPage: ITEMS_PER_PAGE },
        orderLoading: false
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch orders',
        orderLoading: false
      });
    }
  },

  goToNextPage: async () => {
    const { pagination, orderLoading } = get();
    if (!orderLoading && pagination.hasNextPage) {
      await get().fetchOrders(pagination.currentPage + 1);
    }
  },

  goToPreviousPage: async () => {
    const { pagination, orderLoading } = get();
    if (!orderLoading && pagination.currentPage > 1) {
      await get().fetchOrders(pagination.currentPage - 1);
    }
  },

  setSelectedStatus: async (status) => {
    set({ selectedStatus: status });
    get().clearSelectedOrder();
    await get().fetchOrders(1);
  },

  selectOrder: async (order) => {
    // Offline order — serverga so'rov yubormasdan, queue'dagi itemlarni ko'rsatish
    if (order._offline) {
      set({
        selectedOrder: order,
        selectedOrderItems: order._offlineItems || [],
        selectedOrderTaxes: [],
        selectedOrderLoading: false,
        selectedOrderError: null,
      });
      return;
    }

    try {
      set({
        selectedOrder: order,
        selectedOrderLoading: true,
        selectedOrderError: null
      });

      const { items, taxes } = await getPOSInvoiceItems(order.name);

      set({
        selectedOrderItems: items,
        selectedOrderTaxes: taxes,
        selectedOrderLoading: false
      });
    } catch (error) {
      set({
        selectedOrderError: error instanceof Error ? error.message : 'Failed to fetch order details',
        selectedOrderLoading: false
      });
    }
  },

  clearSelectedOrder: () => {
    set({
      selectedOrder: null,
      selectedOrderItems: [],
      selectedOrderTaxes: [],
      selectedOrderError: null
    });
  },

  updateOrderStatus: async (orderId: string, status: POSInvoice['status']) => {
    try {
      set({ orderLoading: true, error: null });

      await call.post('ury.ury_pos.api.updatePosInvoiceStatus', {
        invoice: orderId,
        status,
      });

      await get().fetchOrders(get().pagination.currentPage);
      set({ orderLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update order status',
        orderLoading: false
      });
    }
  },

  setOrderSearchQuery: (query) => set({ orderSearchQuery: query }),
});
