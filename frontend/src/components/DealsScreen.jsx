import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../apiConfig';

export function DealsScreen({ cartId, cartSummary, onBack, onRefreshCart, onProceedPayment }) {
  const [appliedDeal, setAppliedDeal] = useState('INNO200');
  const [timeLeft, setTimeLeft] = useState(292); // 04:52 in seconds

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const handleApplyDeal = (code) => {
    fetch(getApiUrl(`/cart/${cartId}/deals/apply`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deal_code: code })
    })
      .then(res => res.json())
      .then(() => {
        setAppliedDeal(code);
        if (onRefreshCart) onRefreshCart();
      })
      .catch(() => setAppliedDeal(code));
  };

  const cartTotal = cartSummary?.cart_total || 3346;
  const savings = appliedDeal === 'INNO200' ? 200 : appliedDeal === 'LOYAL100' ? 100 : 200;

  return (
    <div className="flex-1 flex flex-col p-4 gap-3.5 bg-[#0D0D0D]">
      {/* Deals Sub-Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="bg-[#FFB300] text-black text-[11px] font-bold font-['Rajdhani'] px-2.5 py-1 rounded tracking-widest uppercase animate-badge-pulse">
            ⚡ RUSH DEALS
          </div>
          <div className="font-['Rajdhani'] text-xl font-bold text-white tracking-wide">
            Exclusive Offers for You
          </div>
        </div>

        <div className="font-['Space_Mono'] text-xs text-[#FFB300] bg-[rgba(255,179,0,0.1)] border border-[rgba(255,179,0,0.2)] rounded-md px-2.5 py-1">
          ⏱ Expires in {formatTimer(timeLeft)}
        </div>
      </div>

      {/* 2x2 Deals Grid */}
      <div className="flex-1 grid grid-cols-2 gap-2.5 min-h-0">
        {/* Deal 1: INNO200 */}
        <div
          className={`bg-[#242428] rounded-xl p-3.5 flex flex-col gap-1.5 relative overflow-hidden cursor-pointer transition-colors border ${
            appliedDeal === 'INNO200'
              ? 'border-[#00E676] bg-[rgba(0,230,118,0.05)]'
              : 'border-[rgba(255,255,255,0.07)] hover:border-[#FFB300]'
          }`}
          onClick={() => handleApplyDeal('INNO200')}
        >
          <div className={`absolute top-0 left-0 w-1 h-full rounded-l ${appliedDeal === 'INNO200' ? 'bg-[#00E676]' : 'bg-[#FFB300]'}`} />
          <div className={`font-['Rajdhani'] text-2xl font-bold leading-none ${appliedDeal === 'INNO200' ? 'text-[#00E676]' : 'text-[#FFB300]'}`}>
            ₹200 OFF
          </div>
          <div className="text-[11px] text-[#A0A0B0]">
            On orders above ₹2,500 — Auto applied
          </div>
          <div className="font-['Space_Mono'] text-[10px] text-[#606070] bg-[#1C1C1E] px-2 py-0.5 rounded w-fit mt-auto">
            INNO200
          </div>
          <button className={`absolute bottom-2.5 right-2.5 border-none rounded-md px-2.5 py-1 text-[10px] font-bold cursor-pointer transition-all ${
            appliedDeal === 'INNO200' ? 'bg-[#00E676] text-black' : 'bg-[#FFB300] text-black'
          }`}>
            {appliedDeal === 'INNO200' ? '✓ Applied' : 'Apply'}
          </button>
        </div>

        {/* Deal 2: FOOT15 */}
        <div
          className={`bg-[#242428] rounded-xl p-3.5 flex flex-col gap-1.5 relative overflow-hidden cursor-pointer transition-colors border ${
            appliedDeal === 'FOOT15'
              ? 'border-[#00E676] bg-[rgba(0,230,118,0.05)]'
              : 'border-[rgba(255,255,255,0.07)] hover:border-[#FFB300]'
          }`}
          onClick={() => handleApplyDeal('FOOT15')}
        >
          <div className="absolute top-0 left-0 w-1 h-full bg-[#FFB300] rounded-l" />
          <div className="font-['Rajdhani'] text-2xl font-bold leading-none text-[#FFB300]">
            15% OFF
          </div>
          <div className="text-[11px] text-[#A0A0B0]">
            On Footwear — Add shoes to avail
          </div>
          <div className="font-['Space_Mono'] text-[10px] text-[#606070] bg-[#1C1C1E] px-2 py-0.5 rounded w-fit mt-auto">
            FOOT15
          </div>
          <button className="absolute bottom-2.5 right-2.5 bg-[#FFB300] text-black border-none rounded-md px-2.5 py-1 text-[10px] font-bold cursor-pointer">
            {appliedDeal === 'FOOT15' ? '✓ Applied' : 'Apply'}
          </button>
        </div>

        {/* Deal 3: LOYAL100 */}
        <div
          className={`bg-[#242428] rounded-xl p-3.5 flex flex-col gap-1.5 relative overflow-hidden cursor-pointer transition-colors border ${
            appliedDeal === 'LOYAL100'
              ? 'border-[#00E676] bg-[rgba(0,230,118,0.05)]'
              : 'border-[rgba(255,255,255,0.07)] hover:border-[#FFB300]'
          }`}
          onClick={() => handleApplyDeal('LOYAL100')}
        >
          <div className="absolute top-0 left-0 w-1 h-full bg-[#FFB300] rounded-l" />
          <div className="font-['Rajdhani'] text-2xl font-bold leading-none text-[#FFB300]">
            ₹100 OFF
          </div>
          <div className="text-[11px] text-[#A0A0B0]">
            On your 2nd visit this week
          </div>
          <div className="font-['Space_Mono'] text-[10px] text-[#606070] bg-[#1C1C1E] px-2 py-0.5 rounded w-fit mt-auto">
            LOYAL100
          </div>
          <button className="absolute bottom-2.5 right-2.5 bg-[#FFB300] text-black border-none rounded-md px-2.5 py-1 text-[10px] font-bold cursor-pointer">
            {appliedDeal === 'LOYAL100' ? '✓ Applied' : 'Apply'}
          </button>
        </div>

        {/* Deal 4: ACCFREE */}
        <div
          className={`bg-[#242428] rounded-xl p-3.5 flex flex-col gap-1.5 relative overflow-hidden cursor-pointer transition-colors border ${
            appliedDeal === 'ACCFREE'
              ? 'border-[#00E676] bg-[rgba(0,230,118,0.05)]'
              : 'border-[rgba(255,255,255,0.07)] hover:border-[#FFB300]'
          }`}
          onClick={() => handleApplyDeal('ACCFREE')}
        >
          <div className="absolute top-0 left-0 w-1 h-full bg-[#FFB300] rounded-l" />
          <div className="font-['Rajdhani'] text-2xl font-bold leading-none text-[#FFB300]">
            FREE
          </div>
          <div className="text-[10px] text-[#A0A0B0]">
            Accessories under ₹299 free with ₹3000+ cart
          </div>
          <div className="font-['Space_Mono'] text-[10px] text-[#606070] bg-[#1C1C1E] px-2 py-0.5 rounded w-fit mt-auto">
            ACCFREE
          </div>
          <button className="absolute bottom-2.5 right-2.5 bg-[#FFB300] text-black border-none rounded-md px-2.5 py-1 text-[10px] font-bold cursor-pointer">
            {appliedDeal === 'ACCFREE' ? '✓ Applied' : 'Apply'}
          </button>
        </div>
      </div>

      {/* Footer Savings Bar & Action */}
      <div className="flex items-center justify-between pt-1">
        <div className="bg-[rgba(0,230,118,0.1)] border border-[rgba(0,230,118,0.25)] rounded-xl px-3.5 py-2 flex items-center gap-3">
          <div>
            <div className="font-['Space_Mono'] text-[10px] text-[#606070] uppercase">YOU SAVE</div>
            <div className="font-['Rajdhani'] text-xl font-bold text-[#00E676]">₹{savings}</div>
          </div>
          <div className="w-px h-7 bg-[rgba(255,255,255,0.07)]"></div>
          <div>
            <div className="font-['Space_Mono'] text-[10px] text-[#606070] uppercase">FINAL TOTAL</div>
            <div className="font-['Rajdhani'] text-xl font-bold text-[#00F5FF]">₹{cartTotal.toLocaleString('en-IN')}</div>
          </div>
        </div>

        <button
          onClick={onProceedPayment}
          className="bg-gradient-to-br from-[#1A1AFF] to-[#0000CC] border border-[rgba(0,245,255,0.3)] hover:shadow-[0_8px_24px_rgba(0,245,255,0.2)] text-white font-['Rajdhani'] text-base font-bold px-7 py-3 rounded-xl tracking-widest uppercase cursor-pointer transition-all"
        >
          PAY NOW →
        </button>
      </div>
    </div>
  );
}
