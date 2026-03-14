import type { SyncOrderRequest } from './order-api';

export interface OfflineOrder {
  id: string;
  timestamp: number;
  orderData: SyncOrderRequest;
  status: 'pending' | 'failed';
  retries: number;
  payment?: OfflinePaymentData;
}

const QUEUE_KEY = 'offline_queue';

const generateId = (): string => {
  return `offline_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
};

export const getQueue = (): OfflineOrder[] => {
  try {
    const raw = localStorage.getItem(QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const saveQueue = (queue: OfflineOrder[]): void => {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
};

export const enqueueOrder = (orderData: SyncOrderRequest): string => {
  const queue = getQueue();
  const id = generateId();
  queue.push({ id, timestamp: Date.now(), orderData, status: 'pending', retries: 0 });
  saveQueue(queue);
  return id;
};

export const removeFromQueue = (id: string): void => {
  saveQueue(getQueue().filter(e => e.id !== id));
};

export const markFailed = (id: string): void => {
  saveQueue(
    getQueue().map(e =>
      e.id === id ? { ...e, status: 'failed' as const, retries: e.retries + 1 } : e
    )
  );
};

export const getPendingCount = (): number => {
  return getQueue().filter(e => e.status === 'pending').length;
};

export const attachPaymentToOfflineOrder = (id: string, paymentData: OfflinePaymentData): void => {
  saveQueue(
    getQueue().map(e =>
      e.id === id ? { ...e, payment: paymentData } : e
    )
  );
};

// ─── Payment Queue ────────────────────────────────────────────────────────────

export interface OfflinePaymentData {
  invoice: string;
  customer: string;
  cashier: string | undefined;
  owner: string;
  pos_profile: string;
  table: string | null;
  payments: Array<{ mode_of_payment: string; amount: number }>;
  additionalDiscount: number | null;
}

export interface OfflinePayment {
  id: string;
  timestamp: number;
  paymentData: OfflinePaymentData;
  status: 'pending' | 'failed';
  retries: number;
}

const PAYMENT_QUEUE_KEY = 'offline_payment_queue';

export const getPaymentQueue = (): OfflinePayment[] => {
  try {
    const raw = localStorage.getItem(PAYMENT_QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const savePaymentQueue = (queue: OfflinePayment[]): void => {
  localStorage.setItem(PAYMENT_QUEUE_KEY, JSON.stringify(queue));
};

export const enqueuePayment = (paymentData: OfflinePaymentData): string => {
  const queue = getPaymentQueue();
  const id = `payment_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  queue.push({ id, timestamp: Date.now(), paymentData, status: 'pending', retries: 0 });
  savePaymentQueue(queue);
  return id;
};

export const removePayment = (id: string): void => {
  savePaymentQueue(getPaymentQueue().filter(e => e.id !== id));
};

export const markPaymentFailed = (id: string): void => {
  savePaymentQueue(
    getPaymentQueue().map(e =>
      e.id === id ? { ...e, status: 'failed' as const, retries: e.retries + 1 } : e
    )
  );
};

export const getPendingPaymentCount = (): number => {
  return getPaymentQueue().filter(e => e.status === 'pending').length;
};

export const getTotalPendingCount = (): number => {
  return getPendingCount() + getPendingPaymentCount();
};
