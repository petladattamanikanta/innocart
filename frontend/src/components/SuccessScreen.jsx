import React from 'react';

export function SuccessScreen({ cartId, cartSummary, txnId, onReset }) {
  const amountPaid = cartSummary?.cart_total || 3346;
  const itemCount = cartSummary?.item_count || 4;
  const savings = cartSummary?.discount_amount || 200;

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6 bg-[radial-gradient(ellipse_at_50%_40%,rgba(0,230,118,0.12)_0%,transparent_60%)] bg-[#0D0D0D] overflow-hidden text-center">
      {/* Glowing Green Success Checkmark Ring */}
      <div className="w-[90px] h-[90px] rounded-full bg-[rgba(0,230,118,0.1)] border-2 border-[#00E676] flex items-center justify-center text-4xl text-[#00E676] shadow-[0_0_40px_rgba(0,230,118,0.3)] animate-success-pop">
        ✓
      </div>

      {/* Success Title */}
      <div className="font-['Rajdhani'] text-3xl font-bold text-[#00E676] tracking-widest uppercase">
        PAYMENT SUCCESSFUL
      </div>

      {/* Subtitle */}
      <div className="text-xs text-[#A0A0B0] leading-relaxed">
        ₹{amountPaid.toLocaleString('en-IN')} paid via GPay · Txn #{txnId || 'RZP8821049'}<br />
        Your bill has been sent to your InnoCart app.
      </div>

      {/* Summary Chips */}
      <div className="flex gap-2.5 flex-wrap justify-center mt-1">
        <div className="bg-[#242428] border border-[rgba(255,255,255,0.07)] rounded-lg px-4 py-2 text-xs text-[#A0A0B0] flex items-center gap-1.5">
          <span className="text-[#00E676]">📄</span> Bill sent to mobile
        </div>
        <div className="bg-[#242428] border border-[rgba(255,255,255,0.07)] rounded-lg px-4 py-2 text-xs text-[#A0A0B0] flex items-center gap-1.5">
          <span className="text-[#00E676]">🛍️</span> {itemCount} items purchased
        </div>
        <div className="bg-[#242428] border border-[rgba(255,255,255,0.07)] rounded-lg px-4 py-2 text-xs text-[#A0A0B0] flex items-center gap-1.5">
          <span className="text-[#00E676]">💰</span> Saved ₹{savings}
        </div>
      </div>

      {/* Exit Action Button */}
      <button
        onClick={onReset}
        className="mt-2 bg-gradient-to-br from-[#00994D] to-[#006633] border border-[rgba(0,230,118,0.3)] hover:shadow-[0_0_20px_rgba(0,230,118,0.4)] text-white font-['Rajdhani'] text-sm font-bold px-7 py-3 rounded-xl tracking-widest uppercase cursor-pointer transition-all animate-blink"
      >
        📲 TAP NFC AT EXIT TO CHECKOUT
      </button>
    </div>
  );
}
