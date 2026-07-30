import React from 'react';

export function ShoppingScreen({ cartSummary, user, onOpenStyling, onOpenDeals, onProceedPayment, onRemoveItem, onUpdateQty }) {
  const items = cartSummary?.items || [];
  const itemCount = cartSummary?.item_count || items.length;
  const cartTotal = cartSummary?.cart_total || 0.0;
  const lastItem = items.length > 0 ? items[items.length - 1] : null;

  return (
    <div className="flex-1 flex overflow-hidden bg-[#0D0D0D]">
      {/* Left: Live Bill Panel */}
      <div className="flex-1 flex flex-col overflow-hidden border-r border-[rgba(255,255,255,0.07)]">
        {/* Bill Header */}
        <div className="px-5 py-3 bg-[#242428] border-b border-[rgba(255,255,255,0.07)] flex items-center justify-between flex-shrink-0">
          <div className="font-['Rajdhani'] text-xs font-bold tracking-widest text-[#00F5FF] uppercase">
            Live Bill
          </div>
          <div className="bg-[#1A1AFF] text-white text-[11px] font-bold px-2 py-0.5 rounded-full">
            {itemCount} {itemCount === 1 ? 'item' : 'items'}
          </div>
        </div>

        {/* Bill Items List */}
        <div className="flex-1 overflow-y-auto bill-items-scroll">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 text-[#606070]">
              <div className="text-3xl mb-2">🛒</div>
              <div className="font-['Space_Mono'] text-xs text-[#A0A0B0] uppercase tracking-wider">
                Cart Cavity Empty
              </div>
              <div className="text-[11px] mt-1">
                Drop RFID-tagged garments into the cart cavity to instantly scan.
              </div>
            </div>
          ) : (
            items.map((item, idx) => (
              <div
                key={item.sku || idx}
                className="flex items-center gap-3 px-5 py-2.5 border-b border-[rgba(255,255,255,0.07)] hover:bg-[#242428] transition-colors animate-slide-in"
              >
                {/* Color Dot */}
                <div
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor:
                      item.color_family === 'Blue' ? '#1A73E8' :
                      item.color_family === 'Khaki' ? '#795548' :
                      item.color_family === 'Green' ? '#388E3C' :
                      item.color_family === 'White' ? '#F5F5F5' : '#00F5FF'
                  }}
                />
                
                {/* Item Details */}
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-white truncate">
                    {item.name}
                  </div>
                  <div className="font-['Space_Mono'] text-[10px] text-[#606070] mt-0.5 truncate">
                    EPC: {item.epc_id || `E280110${idx}`} · SIZE M · ZUDIO
                  </div>
                </div>

                {/* Price & Remove */}
                <div className="font-['Rajdhani'] text-sm font-bold text-white flex-shrink-0">
                  ₹{(item.line_total || item.price || 0).toLocaleString('en-IN')}
                </div>

                <button
                  onClick={() => onRemoveItem(item.sku, item.epc_id)}
                  className="w-5 h-5 rounded-full bg-[rgba(255,59,48,0.15)] border border-[rgba(255,59,48,0.3)] text-[#FF3B30] text-[12px] flex items-center justify-center cursor-pointer hover:bg-[rgba(255,59,48,0.3)] flex-shrink-0"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>

        {/* Bill Footer */}
        <div className="px-5 py-3 bg-[#242428] border-t border-[rgba(255,255,255,0.07)] flex-shrink-0">
          <div className="flex justify-between items-center">
            <div>
              <div className="font-['Space_Mono'] text-[11px] text-[#606070] tracking-wider uppercase">
                SUBTOTAL ({itemCount} ITEMS)
              </div>
              <div className="font-['Space_Mono'] text-[10px] text-[#606070] mt-0.5">
                Tax included
              </div>
            </div>
            <div className="font-['Rajdhani'] text-2xl font-bold text-[#00F5FF]">
              ₹{cartTotal.toLocaleString('en-IN')}
            </div>
          </div>
        </div>
      </div>

      {/* Right: Action & Hardware Telemetry Panel (220px) */}
      <div className="w-[220px] bg-[#1C1C1E] p-4 flex flex-col gap-2.5 flex-shrink-0">
        {/* RFID Status Box */}
        <div className="bg-[#242428] border border-[rgba(0,245,255,0.12)] rounded-lg p-2.5 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#00E676] shadow-[0_0_8px_#00E676] animate-rfid-blink flex-shrink-0"></div>
          <div>
            <div className="text-[10px] font-semibold text-[#A0A0B0]">UHF RFID Active</div>
            <div className="font-['Space_Mono'] text-[9px] text-[#606070] mt-0.5">IMPINJ E710 · 865MHz</div>
          </div>
        </div>

        {/* Last Scanned Box */}
        <div className="bg-[rgba(0,230,118,0.07)] border border-[rgba(0,230,118,0.2)] rounded-lg p-2.5">
          <div className="font-['Space_Mono'] text-[9px] text-[#606070] uppercase tracking-wider">
            Last Scanned
          </div>
          <div className="text-xs font-bold text-[#00E676] mt-1 truncate">
            {lastItem ? lastItem.name : 'Waiting for tag...'}
          </div>
          <div className="font-['Space_Mono'] text-[9px] text-[#606070] mt-0.5">
            {lastItem ? `${lastItem.epc_id || 'E280110F'} · Just now` : '0 tags in antenna beam'}
          </div>
        </div>

        {/* AI Styling Trigger Button */}
        <button
          onClick={onOpenStyling}
          className="bg-gradient-to-br from-[#7C4DFF] to-[#5533CC] border border-[rgba(124,77,255,0.4)] rounded-xl p-3.5 flex items-center gap-2.5 cursor-pointer hover:-translate-y-0.5 hover:shadow-[0_8px_20px_rgba(124,77,255,0.3)] transition-all text-left"
        >
          <div className="text-xl">✨</div>
          <div>
            <div className="font-['Rajdhani'] text-xs font-bold text-white tracking-wider">
              GO WITH AI STYLING
            </div>
            <div className="text-[9px] text-white/60 mt-0.5">
              Get personalised outfit suggestions
            </div>
          </div>
        </button>

        <div className="flex-1"></div>

        {/* Rush Deals Action */}
        <button
          onClick={onOpenDeals}
          className="bg-[#FFB300] hover:bg-[#FFA000] text-black font-['Rajdhani'] text-xs font-bold py-2 px-3 rounded-lg tracking-wider uppercase transition-all"
        >
          ⚡ View Rush Deals
        </button>

        {/* Checkout Button */}
        <button
          onClick={onProceedPayment}
          disabled={itemCount === 0}
          className="bg-gradient-to-br from-[#1A1AFF] to-[#0000CC] border border-[rgba(0,245,255,0.3)] rounded-xl p-3.5 font-['Rajdhani'] text-sm font-bold text-white tracking-widest uppercase hover:-translate-y-0.5 hover:shadow-[0_8px_20px_rgba(26,26,255,0.4)] transition-all disabled:opacity-40 disabled:pointer-events-none"
        >
          CHECKOUT →
        </button>
      </div>
    </div>
  );
}
