import { usePOSStore } from '../store/pos-store';
import { cn } from '../lib/utils';
import { Button } from './ui';
import { TICKET_ORDER_TYPES, ORDER_TYPES, type OrderType } from '../data/order-types';
import { Hash } from 'lucide-react';

interface OrderTypeSelectProps {
  disabled?: boolean;
}

const OrderTypeSelect = ({ disabled }: OrderTypeSelectProps) => {
  const {
    selectedOrderType,
    setSelectedOrderType,
    isUpdatingOrder,
    ticketNumber,
    setTicketNumber,
  } = usePOSStore();

  const needsTicket = TICKET_ORDER_TYPES.includes(selectedOrderType);

  const handleOrderTypeSelect = (type: OrderType) => {
    setSelectedOrderType(type);
  };

  const handleTicketChange = (value: string) => {
    const cleaned = value.replace(/[^0-9]/g, '');
    setTicketNumber(cleaned);
  };

  return (
    <div>
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-2 px-2">
        {ORDER_TYPES.map(({ label, value, icon: Icon }) => {
          const isDisabled = disabled || isUpdatingOrder;

          return (
            <Button
              key={value}
              onClick={() => handleOrderTypeSelect(value)}
              variant={selectedOrderType === value ? 'default' : 'outline'}
              className={cn(
                'h-fit flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap bg-white border transition-colors',
                selectedOrderType === value
                  ? 'text-primary-700 bg-primary-50 border-primary-600 hover:bg-primary-50'
                  : 'text-gray-700 border-gray-200 hover:bg-gray-50',
                isDisabled && 'opacity-50 cursor-not-allowed'
              )}
              disabled={isDisabled}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Button>
          );
        })}
      </div>

      {needsTicket && (
        <div className="mt-2 flex items-center gap-2">
          <Hash className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <input
            type="number"
            min="1"
            max="999"
            value={ticketNumber}
            onChange={e => handleTicketChange(e.target.value)}
            placeholder="Stiker raqami"
            disabled={disabled || isUpdatingOrder}
            className="w-32 h-8 border border-gray-200 rounded-lg px-3 py-1 text-sm font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
          />
        </div>
      )}
    </div>
  );
};

export default OrderTypeSelect;
