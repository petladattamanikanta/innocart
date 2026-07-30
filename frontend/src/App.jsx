import React, { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { getApiUrl } from './apiConfig';
import { WelcomeScreen } from './components/WelcomeScreen';
import { ShoppingScreen } from './components/ShoppingScreen';
import { StylingScreen } from './components/StylingScreen';
import { DealsScreen } from './components/DealsScreen';
import { PaymentScreen } from './components/PaymentScreen';
import { SuccessScreen } from './components/SuccessScreen';

export default function App() {
  const [cartId] = useState("IC-042");
  const [activeScreen, setActiveScreen] = useState('welcome');
  const [user, setUser] = useState(null); // Synced profile
  const [pairingToast, setPairingToast] = useState(null);
  const [cartSummary, setCartSummary] = useState({
    items: [],
    cart_total: 0.0,
    raw_total: 0.0,
    discount_amount: 0.0,
    item_count: 0
  });
  const [lastTxnId, setLastTxnId] = useState(null);
  const [currentTime, setCurrentTime] = useState("");

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleProfileCaptured = useCallback((userData) => {
    setUser(userData);
    setPairingToast(`Welcome ${userData.name}! Skin undertone paired successfully.`);
    setTimeout(() => {
      setPairingToast(null);
      setActiveScreen('shopping');
    }, 1500);
  }, []);

  const handleWebSocketMessage = useCallback((data) => {
    console.log("WebSocket event received on touchscreen:", data);
    if (data.type === 'cart_update') {
      setCartSummary({
        items: data.items || [],
        cart_total: data.cart_total || 0.0,
        raw_total: data.raw_total || 0.0,
        discount_amount: data.discount_amount || 0.0,
        item_count: data.item_count || 0
      });
      if ((data.item_count > 0 || (data.items && data.items.length > 0)) && activeScreen === 'welcome') {
        setActiveScreen('shopping');
      }
    } else if (data.type === 'user_profile_synced') {
      handleProfileCaptured(data.user);
    } else if (data.type === 'payment_confirmed') {
      setLastTxnId(data.txn_id || "TXN_RZP8821049");
      setActiveScreen('success');
    }
  }, [activeScreen, handleProfileCaptured]);

  const { isConnected, isReconnecting } = useWebSocket(cartId, handleWebSocketMessage);

  const fetchCartSummary = useCallback(() => {
    fetch(getApiUrl(`/cart/${cartId}`))
      .then(res => res.json())
      .then(data => {
        if (data) {
          setCartSummary(data);

          // Auto-pair on cart screen if customer profile bound via mobile QR scan
          if (data.customer_name && data.customer_name !== "Valued Customer" && !user) {
            const syncedUser = {
              name: data.customer_name,
              mobile: data.customer_phone || "+918074346103",
              facial_hex: data.facial_hex || "#D4A373",
              undertone_label: data.undertone_label || "Warm-Golden"
            };
            setUser(syncedUser);
            setPairingToast(`Welcome ${data.customer_name}! Profile paired with cart.`);
            setTimeout(() => {
              setPairingToast(null);
              setActiveScreen('shopping');
            }, 1000);
          }
        }
      })
      .catch(err => console.error("Fetch cart summary error:", err));
  }, [cartId, user]);

  useEffect(() => {
    fetchCartSummary();
    const interval = setInterval(fetchCartSummary, 2500);
    return () => clearInterval(interval);
  }, [fetchCartSummary]);

  const handleRemoveItem = (sku, epcId) => {
    fetch(getApiUrl('/cart/remove'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: cartId, sku, epc_id: epcId })
    }).then(fetchCartSummary);
  };

  const handleUpdateQty = (sku, quantity) => {
    fetch(getApiUrl('/cart/qty'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: cartId, sku, quantity })
    }).then(fetchCartSummary);
  };

  const handleResetSession = () => {
    fetch(getApiUrl(`/cart/${cartId}`), { method: 'DELETE' })
      .then(() => {
        fetchCartSummary();
        setUser(null);
        setActiveScreen('welcome');
      });
  };

  return (
    <div className="w-full min-h-screen bg-[#080810] flex flex-col items-center justify-center p-6">
      {/* 800x480 KIOSK DEVICE FRAME */}
      <div className="device-wrap flex justify-center w-full">
        <div className="w-[800px] h-[480px] bg-[#111114] rounded-2xl border-2 border-[rgba(0,245,255,0.2)] shadow-[0_0_0_6px_#1a1a1f,0_0_0_8px_#252530,0_0_60px_rgba(0,245,255,0.08),0_40px_80px_rgba(0,0,0,0.8)] overflow-hidden relative flex flex-col">
          
          {/* Reconnecting Warning */}
          {isReconnecting && (
            <div className="absolute top-11 inset-x-0 bg-[#FFB300] text-black font-['Space_Mono'] font-bold text-[10px] py-1 text-center z-50 animate-pulse">
              ⚠️ RFID Cart Wi-Fi Re-establishing...
            </div>
          )}

          {/* Pairing Success Toast Notification */}
          {pairingToast && (
            <div className="absolute top-14 inset-x-12 bg-gradient-to-r from-[#00E676] to-[#00F5FF] text-black font-['Rajdhani'] font-bold text-sm py-2 px-4 rounded-xl text-center shadow-2xl z-50 animate-bounce">
              ✓ {pairingToast}
            </div>
          )}

          {/* TOP BAR HEADER */}
          <div className="h-11 bg-[#1C1C1E] border-b border-[rgba(0,245,255,0.12)] flex items-center justify-between px-5 flex-shrink-0 relative z-20">
            <div className="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-[#00F5FF] to-transparent opacity-40"></div>
            
            <div className="flex items-center gap-3">
              <span className="font-['Rajdhani'] text-lg font-bold tracking-widest bg-gradient-to-r from-[#00F5FF] to-[#1A1AFF] bg-clip-text text-transparent">
                INNOCART
              </span>
              <span className="w-px h-4 bg-[rgba(255,255,255,0.1)]"></span>
              <span className="font-['Space_Mono'] text-[10px] text-[#606070] tracking-wider uppercase">
                CART #{cartId}
              </span>
            </div>

            <div className="flex items-center gap-4">
              {user ? (
                <div className="flex items-center gap-2 bg-[#2E2E34] border border-[rgba(0,245,255,0.2)] rounded-full py-0.5 px-3">
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] text-black"
                    style={{ backgroundColor: user.facial_hex || '#00F5FF' }}
                  >
                    {user.name ? user.name[0].toUpperCase() : 'U'}
                  </div>
                  <span className="text-[11px] font-bold text-white">{user.name}</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-[#00F5FF] font-['Space_Mono'] text-[10px]">
                  <span>📶</span>
                </div>
              )}
              <span className="font-['Space_Mono'] text-[10px] text-[#606070]">{currentTime}</span>
            </div>
          </div>

          {/* DYNAMIC SCREEN RENDERER */}
          <div className="flex-1 flex flex-col overflow-hidden relative">
            {activeScreen === 'welcome' && (
              <WelcomeScreen
                cartId={cartId}
                onStart={() => setActiveScreen('shopping')}
                onSimulateScan={(userData) => handleProfileCaptured(userData)}
              />
            )}
            {activeScreen === 'shopping' && (
              <ShoppingScreen
                cartSummary={cartSummary}
                user={user}
                onOpenStyling={() => setActiveScreen('styling')}
                onOpenDeals={() => setActiveScreen('deals')}
                onProceedPayment={() => setActiveScreen('payment')}
                onRemoveItem={handleRemoveItem}
                onUpdateQty={handleUpdateQty}
              />
            )}
            {activeScreen === 'styling' && (
              <StylingScreen
                cartSummary={cartSummary}
                user={user}
                onBack={() => setActiveScreen('shopping')}
              />
            )}
            {activeScreen === 'deals' && (
              <DealsScreen
                cartId={cartId}
                cartSummary={cartSummary}
                onBack={() => setActiveScreen('shopping')}
                onRefreshCart={fetchCartSummary}
                onProceedPayment={() => setActiveScreen('payment')}
              />
            )}
            {activeScreen === 'payment' && (
              <PaymentScreen
                cartId={cartId}
                cartSummary={cartSummary}
                onBack={() => setActiveScreen('shopping')}
                onPaymentComplete={(txnId) => {
                  setLastTxnId(txnId);
                  setActiveScreen('success');
                }}
              />
            )}
            {activeScreen === 'success' && (
              <SuccessScreen
                cartId={cartId}
                cartSummary={cartSummary}
                txnId={lastTxnId}
                onReset={handleResetSession}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
