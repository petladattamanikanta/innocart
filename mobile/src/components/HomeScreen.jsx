import React from 'react';
import { QrCode, LogOut, Zap, ShoppingBag, Sparkles } from 'lucide-react';

export function HomeScreen({ user, activeCartSession, onOpenScanner, onOpenProfile, onNavigateToCart, onLogout }) {
  return (
    <div className="w-full min-h-screen bg-[#080810] flex flex-col justify-between relative p-6 overflow-y-auto">
      {/* Customer Header */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between bg-[#141418] border border-[rgba(0,245,255,0.15)] rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-full border-2 border-[#00F5FF] p-0.5 flex items-center justify-center shadow-[0_0_15px_rgba(0,245,255,0.3)] cursor-pointer"
              onClick={onOpenProfile}
            >
              <div
                className="w-full h-full rounded-full flex items-center justify-center font-bold text-sm text-black"
                style={{ backgroundColor: user.facial_hex || '#D4A373' }}
              >
                {user.name ? user.name[0].toUpperCase() : 'U'}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white font-['Rajdhani']">{user.name}</h2>
                <span className="px-2 py-0.5 rounded bg-[rgba(0,245,255,0.15)] text-[#00F5FF] text-[10px] font-['Space_Mono'] font-bold uppercase">
                  {user.undertone_label || 'Warm-Golden'}
                </span>
              </div>
              <p className="text-xs text-[#A0A0B0] font-['Space_Mono']">
                {user.mobile || user.email || '+91 98765 43210'}
              </p>
            </div>
          </div>

          <button
            onClick={onLogout}
            className="p-2.5 rounded-xl bg-[#1C1C1E] border border-[rgba(255,255,255,0.08)] text-[#A0A0B0] hover:text-red-400 cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        {/* Primary Action Card: Scan Cart QR Code */}
        <div className="bg-[#141418] border border-[rgba(0,245,255,0.25)] rounded-3xl p-6 text-center space-y-5 shadow-[0_0_40px_rgba(0,245,255,0.1)]">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[rgba(0,245,255,0.1)] border border-[rgba(0,245,255,0.2)]">
            <Zap className="w-3.5 h-3.5 text-[#FFB300]" />
            <span className="font-['Space_Mono'] text-[11px] text-[#00F5FF] font-bold tracking-wider uppercase">
              {activeCartSession ? `PAIRED TO CART #${activeCartSession}` : 'TOUCHSCREEN SCANNER READY'}
            </span>
          </div>

          <div>
            <h3 className="text-2xl font-bold text-white font-['Rajdhani'] tracking-wide">
              {activeCartSession ? `Cart #${activeCartSession} Active` : 'Scan Cart Kiosk QR Code'}
            </h3>
            <p className="text-xs text-[#A0A0B0] mt-1 leading-relaxed max-w-xs mx-auto">
              {activeCartSession
                ? `Customer profile (${user.name}) and skin undertone (${user.undertone_label}) are paired with Cart #${activeCartSession}. Drop garments into cavity!`
                : 'Point your camera at the Session QR Code displayed on the InnoCart 7" Touchscreen Kiosk.'}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="space-y-2.5 pt-1">
            <button
              onClick={onOpenScanner}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#00F5FF] via-[#7C4DFF] to-[#1A1AFF] text-black font-extrabold text-base tracking-widest uppercase font-['Rajdhani'] shadow-[0_0_30px_rgba(0,245,255,0.4)] hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 cursor-pointer"
            >
              <QrCode className="w-6 h-6 text-black" />
              <span>SCAN CART QR CODE</span>
            </button>

            {activeCartSession && (
              <button
                onClick={onNavigateToCart}
                className="w-full py-3.5 rounded-2xl bg-[#1A1A28] border border-[rgba(0,245,255,0.3)] text-[#00F5FF] font-extrabold text-sm tracking-widest uppercase font-['Rajdhani'] hover:bg-[rgba(0,245,255,0.15)] transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                <ShoppingBag className="w-4 h-4 text-[#00F5FF]" />
                <span>VIEW LIVE CART PRODUCTS SECTION (SCREEN 2)</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="text-center pt-6 pb-2">
        <p className="text-[11px] text-[#606070] font-['Space_Mono'] uppercase tracking-wider">
          InnoCart Companion App v2.0 · Realtime Cavity Sync
        </p>
      </div>
    </div>
  );
}
