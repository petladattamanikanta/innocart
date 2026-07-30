import React, { useState, useEffect } from 'react';
import { HomeScreen } from './components/HomeScreen';
import { CartScreen } from './components/CartScreen';
import { OffersScreen } from './components/OffersScreen';
import { ProfileScreen } from './components/ProfileScreen';
import { AuthScreen } from './components/AuthScreen';
import { QRScannerModal } from './components/QRScannerModal';
import { Home, ShoppingBag, Sparkles, User } from 'lucide-react';
import { Capacitor } from '@capacitor/core';
import { getApiUrl } from './apiConfig';

export default function App() {
  const [user, setUser] = useState(null);
  const [activeScreen, setActiveScreen] = useState('cart'); // Default to 'cart' or 'home'
  const [isScannerOpen, setIsScannerOpen] = useState(false);
  const [activeCartSession, setActiveCartSession] = useState('IC-042');
  const [cartItemCount, setCartItemCount] = useState(0);

  useEffect(() => {
    const storedUser = localStorage.getItem('innocart_user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (err) {
        console.error("Failed to parse user session", err);
      }
    }

    if (Capacitor.isNativePlatform() && Capacitor.Plugins?.SessionInitiation) {
      Capacitor.Plugins.SessionInitiation.getLaunchSession().then((res) => {
        if (res && res.has_deep_link && res.cart_id) {
          setActiveCartSession(res.cart_id);
          setIsScannerOpen(true);
        }
      }).catch((err) => console.log("Native deep link check error:", err));
    }
  }, []);

  // Poll backend for cart count badge
  useEffect(() => {
    const fetchCartCount = async () => {
      try {
        const res = await fetch(getApiUrl(`/cart/${activeCartSession || 'IC-042'}`));
        if (res.ok) {
          const data = await res.json();
          setCartItemCount(data?.items?.length || 0);
        }
      } catch (err) {
        // Silent catch for background poll
      }
    };
    fetchCartCount();
    const interval = setInterval(fetchCartCount, 2000);
    return () => clearInterval(interval);
  }, [activeCartSession]);

  const handleLogout = () => {
    localStorage.removeItem('innocart_token');
    localStorage.removeItem('innocart_user');
    setUser(null);
    setActiveCartSession('IC-042');
  };

  if (!user) {
    return <AuthScreen onAuthSuccess={(usr) => setUser(usr)} />;
  }

  return (
    <div className="w-full min-h-screen bg-[#080810] flex justify-center items-start overflow-y-auto">
      <div className="w-full max-w-md min-h-screen bg-[#0D0D12] relative overflow-y-auto shadow-[0_0_50px_rgba(0,0,0,0.8)] pb-16">
        
        {/* Render Active Screen */}
        {activeScreen === 'home' && (
          <HomeScreen
            user={user}
            activeCartSession={activeCartSession}
            onOpenScanner={() => setIsScannerOpen(true)}
            onOpenProfile={() => setActiveScreen('profile')}
            onNavigateToCart={() => setActiveScreen('cart')}
            onLogout={handleLogout}
          />
        )}

        {activeScreen === 'cart' && (
          <CartScreen
            user={user}
            activeCartSession={activeCartSession}
            onNavigateToOffers={() => setActiveScreen('offers')}
            onOpenScanner={() => setIsScannerOpen(true)}
          />
        )}

        {activeScreen === 'offers' && (
          <OffersScreen
            user={user}
            onNavigateToCart={() => setActiveScreen('cart')}
          />
        )}

        {activeScreen === 'profile' && (
          <ProfileScreen
            user={user}
            onBack={() => setActiveScreen('home')}
            onUpdateUser={(updated) => setUser(updated)}
          />
        )}

        {/* QR Scanner Modal overlay */}
        {isScannerOpen && (
          <QRScannerModal
            user={user}
            onClose={() => setIsScannerOpen(false)}
            onSyncComplete={(sessionId) => {
              setActiveCartSession(sessionId);
              setActiveScreen('cart');
            }}
          />
        )}

        {/* Bottom Navigation Tab Bar */}
        <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-[#0D0D14]/95 backdrop-blur-lg border-t border-[rgba(0,245,255,0.15)] flex items-center justify-around py-2.5 px-3 z-40">
          
          <button
            onClick={() => setActiveScreen('home')}
            className={`flex flex-col items-center gap-1 transition-all cursor-pointer ${
              activeScreen === 'home' ? 'text-[#00F5FF]' : 'text-[#606070] hover:text-[#A0A0B0]'
            }`}
          >
            <Home className="w-5 h-5" />
            <span className="text-[10px] font-['Space_Mono'] font-bold">HOME</span>
          </button>

          <button
            onClick={() => setActiveScreen('cart')}
            className={`flex flex-col items-center gap-1 transition-all cursor-pointer relative ${
              activeScreen === 'cart' ? 'text-[#00F5FF]' : 'text-[#606070] hover:text-[#A0A0B0]'
            }`}
          >
            <div className="relative">
              <ShoppingBag className="w-5 h-5" />
              {cartItemCount > 0 && (
                <span className="absolute -top-1.5 -right-2 w-4 h-4 rounded-full bg-[#00FF88] text-black font-extrabold text-[9px] font-['Space_Mono'] flex items-center justify-center animate-pulse shadow-[0_0_8px_#00FF88]">
                  {cartItemCount}
                </span>
              )}
            </div>
            <span className="text-[10px] font-['Space_Mono'] font-bold">CART</span>
          </button>

          <button
            onClick={() => setActiveScreen('offers')}
            className={`flex flex-col items-center gap-1 transition-all cursor-pointer ${
              activeScreen === 'offers' ? 'text-[#FF9500]' : 'text-[#606070] hover:text-[#A0A0B0]'
            }`}
          >
            <Sparkles className="w-5 h-5" />
            <span className="text-[10px] font-['Space_Mono'] font-bold">OFFERS</span>
          </button>

          <button
            onClick={() => setActiveScreen('profile')}
            className={`flex flex-col items-center gap-1 transition-all cursor-pointer ${
              activeScreen === 'profile' ? 'text-[#00F5FF]' : 'text-[#606070] hover:text-[#A0A0B0]'
            }`}
          >
            <User className="w-5 h-5" />
            <span className="text-[10px] font-['Space_Mono'] font-bold">PROFILE</span>
          </button>
        </div>

      </div>
    </div>
  );
}
