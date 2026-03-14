import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Footer from './components/Footer';
import Header from './components/Header';
import Orders from './pages/Orders';
import POS from './pages/POS';
import AuthGuard from './components/AuthGuard';
import POSOpeningProvider from './components/POSOpeningProvider';
import ScreenSizeProvider from './components/ScreenSizeProvider';
import { ToastProvider, showToast } from './components/ui/toast';
import { usePOSStore } from './store/pos-store';
import { useCallback, useEffect } from 'react';
import { getTotalPendingCount } from './lib/offline-queue';

/**
 * Haqiqiy internet ulanishini tekshirish.
 * navigator.onLine faqat tarmoq interfeysi borligini tekshiradi — ishonchsiz.
 * Bu funksiya real HTTP request qiladi: istalgan javob = online, TypeError = offline.
 */
async function checkConnectivity(): Promise<boolean> {
  try {
    // /api/ routelari SW tomonidan bypass qilinadi (real network request)
    await fetch('/api/method/frappe.ping', { cache: 'no-store' });
    return true; // Istalgan HTTP javob (hatto 404) = server yetimli = online
  } catch {
    return false; // TypeError = tarmoq xatosi = offline
  }
}

function App() {
  const {
    initializeApp,
    setOnlineStatus,
    syncOfflineQueue,
  } = usePOSStore();

  useEffect(() => {
    initializeApp();
  }, [initializeApp]);

  const handleConnectivity = useCallback(async () => {
    const online = await checkConnectivity();

    const { isOnline: wasOnline } = usePOSStore.getState();

    // Holat o'zgargan bo'lsa yangilash
    if (online !== wasOnline) {
      setOnlineStatus(online);
    }

    if (online) {
      const pendingBefore = getTotalPendingCount();
      if (pendingBefore > 0) {
        const { syncedCount, errors } = await syncOfflineQueue();
        if (syncedCount > 0) {
          showToast.success(`${syncedCount} ta buyurtma server bilan sinxronlandi!`);
        }
        if (errors.length > 0) {
          showToast.error(`${errors.length} ta buyurtma sync bo'lmadi: ${errors[0]}`);
        }
      }
    }
  }, [setOnlineStatus, syncOfflineQueue]);

  useEffect(() => {
    let mounted = true;

    const safeCheck = async () => {
      if (mounted) await handleConnectivity();
    };

    // Darhol tekshirish (app yuklanganda ham pending bo'lishi mumkin)
    safeCheck();

    // Har 30 soniyada haqiqiy connectivity tekshirish
    const interval = setInterval(safeCheck, 30000);

    // Browser eventlari — tezkor trigger (lekin asosiy tekshirish safeCheck)
    window.addEventListener('online', safeCheck);
    window.addEventListener('offline', () => setOnlineStatus(false));

    return () => {
      mounted = false;
      clearInterval(interval);
      window.removeEventListener('online', safeCheck);
      window.removeEventListener('offline', () => setOnlineStatus(false));
    };
  }, [handleConnectivity, setOnlineStatus]);

  return (
    <>
      <ToastProvider />
      <ScreenSizeProvider>
        <AuthGuard>
          <POSOpeningProvider>
            <Router basename="/pos">
              <div className="flex flex-col h-screen bg-gray-100 font-inter">
                <Header />
                <div className="flex-1 overflow-hidden">
                  <Routes>
                    <Route path="/" element={<POS/>} />
                    <Route path="/orders" element={<Orders />} />
                  </Routes>
                </div>
                <Footer />
              </div>
            </Router>
          </POSOpeningProvider>
        </AuthGuard>
      </ScreenSizeProvider>
    </>
  );
}

export default App;
