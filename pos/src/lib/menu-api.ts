import { call } from './frappe-sdk';

const CACHE_TTL = 4 * 60 * 60 * 1000; // 4 hours

interface MenuCache {
  items: MenuItem[];
  timestamp: number;
}

const getMenuCacheKey = (posProfile: string, orderType: string | null): string =>
  `menu_cache_${posProfile}_${orderType || 'default'}`;

export interface MenuItem {
  item: string;
  item_name: string;
  item_image: string | null;
  rate: number | string;
  course: string;
  trending?: boolean;
  popular?: boolean;
  recommended?: boolean;
  description?: string;
  special_dish?: 1 | 0;
}

export interface GetMenuResponse {
  message: {
    items: MenuItem[];
  };
}

export interface GetAggregatorMenuResponse {
  message: MenuItem[];
}

export const getRestaurantMenu = async (posProfile: string, room: string | null, order_type: string | null) => {
  const cacheKey = getMenuCacheKey(posProfile, order_type);

  // Offline: faqat cache'dan qaytarish
  if (!navigator.onLine) {
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const { items }: MenuCache = JSON.parse(cached);
        return items;
      }
    } catch {}
    throw new Error('Offline: menu cache mavjud emas');
  }

  // Online: yangi emas bo'lsa cache ishlatish
  try {
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      const { items, timestamp }: MenuCache = JSON.parse(cached);
      if (Date.now() - timestamp < CACHE_TTL) {
        return items;
      }
    }
  } catch {}

  // Serverdan yuklash va cache'ga saqlash
  try {
    const response = await call.get<GetMenuResponse>(
      'ury.ury_pos.api.getRestaurantMenu',
      {
        pos_profile: posProfile,
        room: room,
        order_type: order_type
      }
    );
    const items = response.message.items;
    localStorage.setItem(cacheKey, JSON.stringify({ items, timestamp: Date.now() } as MenuCache));
    return items;
  } catch (error: any) {
    if (error._server_messages) {
      const messages = JSON.parse(error._server_messages);
      const message = JSON.parse(messages[0]);
      throw new Error(message.message);
    }
    throw error;
  }
};

export const getAggregatorMenu = async (aggregator: string) => {
  try {
    const response = await call.get<GetAggregatorMenuResponse>(
      'ury.ury_pos.api.getAggregatorItem',
      {
        aggregator
      }
    );
    return response.message;
  } catch (error: any) {
    if (error._server_messages) {
      const messages = JSON.parse(error._server_messages);
      const message = JSON.parse(messages[0]);
      throw new Error(message.message);
    }
    throw error;
  }
}; 