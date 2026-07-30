import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../apiConfig';

export function StylingScreen({ cartSummary, user, onBack, onRefreshCart }) {
  const [aiStylingData, setAiStylingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('outfit'); // 'outfit' | 'footwear' | 'accessories'
  const [addingSku, setAddingSku] = useState(null);

  const cartId = cartSummary?.cart_id || "IC-042";
  const facialHex = user?.facial_hex || "#C8A882";
  const userStyle = user?.style_profile || "Streetwear";

  const fetchAiStyling = () => {
    setLoading(true);
    fetch(getApiUrl(`/cart/${cartId}/ai_styling?facial_hex=${encodeURIComponent(facialHex)}&user_style=${encodeURIComponent(userStyle)}`))
      .then(res => res.json())
      .then(data => {
        setAiStylingData(data);
      })
      .catch(err => {
        console.error("AI Styling API call error:", err);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAiStyling();
  }, [cartId, facialHex, userStyle, cartSummary?.items?.length]);

  const handleAddToCart = (sku) => {
    setAddingSku(sku);
    fetch(getApiUrl('/cart/scan'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: cartId, epc_id: `SKU-PAIR-${sku}` })
    })
      .then(() => {
        if (onRefreshCart) onRefreshCart();
        fetchAiStyling();
      })
      .finally(() => setAddingSku(null));
  };

  // Determine current active cards to render
  const getActiveCards = () => {
    if (!aiStylingData) return [];
    if (activeTab === 'footwear') return aiStylingData.recommended_footwear || [];
    if (activeTab === 'accessories') return aiStylingData.recommended_accessories || [];

    // 'outfit' tab: show bottomwear recs if topwear in cart, or topwear recs if bottomwear in cart
    const bots = aiStylingData.recommended_bottomwear || [];
    const tops = aiStylingData.recommended_topwear || [];
    return bots.length > 0 ? bots : tops;
  };

  const activeCards = getActiveCards();
  const activeTopwear = aiStylingData?.active_topwear;
  const activeBottomwear = aiStylingData?.active_bottomwear;
  const matchScore = aiStylingData?.outfit_match_score || 94;

  return (
    <div className="flex-1 flex flex-col p-4 gap-3.5 bg-[radial-gradient(ellipse_at_50%_0%,rgba(124,77,255,0.18)_0%,transparent_70%)] bg-[#0D0D0D]">
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="bg-gradient-to-br from-[#7C4DFF] to-[#5533CC] text-white text-[11px] font-bold font-['Rajdhani'] px-2.5 py-1 rounded tracking-widest uppercase shadow-[0_0_12px_rgba(124,77,255,0.4)]">
            ✨ 5-STAGE AI ENGINE
          </div>
          <div className="font-['Rajdhani'] text-xl font-bold text-white tracking-wide">
            AI Style Companion & Outfit Harmony
          </div>
        </div>

        <div className="flex items-center gap-2 bg-[#242428] border border-[rgba(0,245,255,0.2)] rounded-full py-1 px-3">
          <div
            className="w-3.5 h-3.5 rounded-full border border-white/40"
            style={{ backgroundColor: facialHex }}
          />
          <span className="font-['Space_Mono'] text-[11px] text-[#00F5FF] font-bold">
            {aiStylingData?.undertone_label || 'Warm-Golden'} ({facialHex})
          </span>
        </div>
      </div>

      {/* Selected Item Info & Harmony Match Score Bar */}
      <div className="bg-[#242428] border border-[rgba(124,77,255,0.35)] rounded-xl px-4 py-2.5 flex items-center justify-between shadow-[0_4px_15px_rgba(0,0,0,0.5)]">
        <div>
          <div className="font-['Space_Mono'] text-[9px] text-[#606070] tracking-widest uppercase">
            STYLING REFERENCE GARMENT
          </div>
          <div className="text-xs font-bold text-[#00F5FF] mt-0.5">
            {activeTopwear ? `${activeTopwear.name} (Topwear)` : activeBottomwear ? `${activeBottomwear.name} (Bottomwear)` : 'Men\'s Slim Kurta — Blue'}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="font-['Space_Mono'] text-[9px] text-[#606070] uppercase">COLOR HARMONY</div>
            <div className="font-['Rajdhani'] text-lg font-extrabold text-[#00FF88]">{matchScore}% MATCH</div>
          </div>
          <button
            onClick={onBack}
            className="bg-[#1C1C24] border border-[rgba(255,255,255,0.12)] hover:bg-[#2A2A38] text-white text-xs font-bold px-3.5 py-1.5 rounded-lg cursor-pointer transition-colors"
          >
            ← Back to Cart
          </button>
        </div>
      </div>

      {/* Main Content: Left AI Skin Palette Sidebar + Right Outfit Recommendations */}
      <div className="flex-1 flex gap-3.5 min-h-0">
        
        {/* Left Side: AI Skin Tone & Wardrobe Color Palette */}
        <div className="w-72 bg-[#1A1A22] border border-[rgba(0,245,255,0.25)] rounded-2xl p-4 flex flex-col justify-between space-y-3 overflow-y-auto">
          <div>
            <div className="flex items-center gap-2 border-b border-white/10 pb-2.5">
              <div
                className="w-8 h-8 rounded-lg border border-[#00F5FF] flex-shrink-0 flex items-center justify-center shadow-[0_0_10px_rgba(0,245,255,0.3)]"
                style={{ backgroundColor: facialHex }}
              />
              <div>
                <h4 className="font-['Rajdhani'] font-bold text-sm text-white leading-none">Scanned Skin Profile</h4>
                <span className="text-[10px] text-[#00F5FF] font-['Space_Mono']">{undertoneLabel} ({facialHex})</span>
              </div>
            </div>

            {/* Suitable Colors Checklist */}
            <div className="pt-3 space-y-1.5">
              <span className="font-['Rajdhani'] font-bold text-xs text-white tracking-wider uppercase">
                Recommended Wardrobe Palette:
              </span>
              <div className="grid grid-cols-2 gap-1.5 pt-1">
                {['Navy Blue', 'Olive Green', 'Forest Green', 'Burgundy', 'Maroon', 'Charcoal', 'Teal', 'Rust', 'White', 'Mustard'].map((col, idx) => (
                  <div key={idx} className="flex items-center gap-1 text-[10px] text-white bg-[#242430] px-2 py-1 rounded border border-white/5 font-['Space_Mono']">
                    <span className="text-green-400 font-bold">✓</span>
                    <span className="truncate">{col}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-[#241A1A] border border-[#FF9500]/30 p-2.5 rounded-xl text-[10px] text-[#FF9500] font-['Space_Mono'] space-y-0.5">
            <span className="font-bold">⚠️ Colors to Avoid:</span>
            <p className="text-[#A0A0B0] text-[9.5px]">Very pale beige or neon yellow may wash out your complexion.</p>
          </div>
        </div>

        {/* Right Side: Category Navigation Tabs & Recommendations Grid */}
        <div className="flex-1 flex flex-col gap-3 min-h-0">
          {/* Category Navigation Tabs */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('outfit')}
              className={`flex-1 py-2 rounded-xl font-['Rajdhani'] text-xs font-bold tracking-wider uppercase transition-all cursor-pointer flex items-center justify-center gap-2 ${
                activeTab === 'outfit'
                  ? 'bg-gradient-to-r from-[#7C4DFF] to-[#5533CC] text-white shadow-[0_0_15px_rgba(124,77,255,0.4)] border border-[#7C4DFF]'
                  : 'bg-[#1C1C22] text-[#A0A0B0] hover:text-white border border-[rgba(255,255,255,0.07)]'
              }`}
            >
              <span>👖</span>
              <span>COMPLEMENTARY OUTFIT ({activeTopwear ? 'BOTTOMWEAR' : 'TOPWEAR'})</span>
            </button>

            <button
              onClick={() => setActiveTab('footwear')}
              className={`flex-1 py-2 rounded-xl font-['Rajdhani'] text-xs font-bold tracking-wider uppercase transition-all cursor-pointer flex items-center justify-center gap-2 ${
                activeTab === 'footwear'
                  ? 'bg-gradient-to-r from-[#00F5FF] to-[#00C4CC] text-black shadow-[0_0_15px_rgba(0,245,255,0.4)] border border-[#00F5FF]'
                  : 'bg-[#1C1C22] text-[#A0A0B0] hover:text-white border border-[rgba(255,255,255,0.07)]'
              }`}
            >
              <span>👟</span>
              <span>MATCHING FOOTWEAR</span>
            </button>

            <button
              onClick={() => setActiveTab('accessories')}
              className={`flex-1 py-2 rounded-xl font-['Rajdhani'] text-xs font-bold tracking-wider uppercase transition-all cursor-pointer flex items-center justify-center gap-2 ${
                activeTab === 'accessories'
                  ? 'bg-gradient-to-r from-[#FF9500] to-[#FFA000] text-black shadow-[0_0_15px_rgba(255,149,0,0.4)] border border-[#FF9500]'
                  : 'bg-[#1C1C22] text-[#A0A0B0] hover:text-white border border-[rgba(255,255,255,0.07)]'
              }`}
            >
              <span>🎩</span>
              <span>ACCESSORIES</span>
            </button>
          </div>

          {/* Recommendation Cards Grid */}
          <div className="flex-1 flex gap-3 min-h-0">
            {loading ? (
              <div className="flex-1 flex items-center justify-center text-xs text-[#7C4DFF] font-['Space_Mono'] animate-pulse">
                ✨ Querying 5-Stage AI Harmony Engine for {activeTab.toUpperCase()}...
              </div>
            ) : activeCards.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-xs text-[#606070] font-['Space_Mono']">
                No recommendations available for this category.
              </div>
            ) : (
              activeCards.slice(0, 3).map((card, idx) => (
                <div
                  key={card.recommended_sku || idx}
                  className="flex-1 bg-[#242428] border border-[rgba(255,255,255,0.08)] hover:border-[#7C4DFF] rounded-xl p-4 flex flex-col justify-between relative overflow-hidden transition-all shadow-[0_4px_20px_rgba(0,0,0,0.4)] group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-['Space_Mono'] text-[10px] font-bold text-[#00FF88] px-2 py-0.5 rounded bg-[rgba(0,255,136,0.1)] border border-[rgba(0,255,136,0.2)]">
                      #{card.rank || idx + 1} MATCH
                    </span>
                    <span className="font-['Rajdhani'] text-base font-extrabold text-[#00F5FF]">
                      ₹{(card.price || 0).toLocaleString('en-IN')}
                    </span>
                  </div>

                  <div className="my-2 space-y-1">
                    <div className="text-base font-bold text-white font-['Rajdhani'] leading-tight">
                      {card.name}
                    </div>
                    <p className="text-[11px] text-[#A0A0B0] font-['Space_Mono'] leading-relaxed">
                      {card.match_reason}
                    </p>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-[rgba(255,255,255,0.06)]">
                    <div className="flex items-center gap-1.5 text-[10px] font-['Space_Mono'] text-[#606070]">
                      <span>📍</span> {card.aisle_location || 'Aisle A-01'}
                    </div>

                    <button
                      onClick={() => handleAddToCart(card.recommended_sku)}
                      disabled={addingSku === card.recommended_sku}
                      className="w-full py-2 rounded-lg bg-gradient-to-r from-[#00F5FF] to-[#7C4DFF] text-black font-extrabold text-xs font-['Rajdhani'] uppercase tracking-wider hover:opacity-90 transition-all cursor-pointer shadow-[0_0_15px_rgba(0,245,255,0.2)] flex items-center justify-center gap-1.5"
                    >
                      {addingSku === card.recommended_sku ? 'Adding...' : '➕ ADD TO CART'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
