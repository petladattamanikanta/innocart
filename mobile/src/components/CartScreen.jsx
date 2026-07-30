import React, { useState, useEffect } from 'react';
import { ShoppingBag, Trash2, Plus, Minus, Tag, Zap, ChevronRight, ShieldCheck, Sparkles, RefreshCw, CreditCard, Shirt, Footprints, Crown } from 'lucide-react';
import { getApiUrl } from '../apiConfig';

export function CartScreen({ user, activeCartSession, onNavigateToOffers, onOpenScanner }) {
  const [cartData, setCartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [appliedCode, setAppliedCode] = useState(null);
  const [promoInput, setPromoInput] = useState('');
  const [promoError, setPromoError] = useState('');
  const [promoSuccess, setPromoSuccess] = useState('');
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);

  // Dedicated AI Cart Styling State
  const [aiStylingData, setAiStylingData] = useState(null);
  const [aiMode, setAiMode] = useState('outfit'); // 'outfit' | 'footwear' | 'accessories'
  const [aiLoading, setAiLoading] = useState(false);

  const sessionId = activeCartSession || 'IC-042';

  const fetchCartData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const res = await fetch(getApiUrl(`/cart/${sessionId}`));
      if (res.ok) {
        const data = await res.json();
        setCartData(data);
      }
    } catch (err) {
      console.error("Cart sync error:", err);
    } flex: {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Live Auto Polling every 1.5s for Cart Summary
  useEffect(() => {
    fetchCartData();
    const interval = setInterval(fetchCartData, 1500);
    return () => clearInterval(interval);
  }, [sessionId]);

  const items = cartData?.items || [];
  const rawTotal = cartData?.raw_total || 0;

  // Trigger Dedicated Backend Function GET /api/cart/{session_id}/ai_styling
  useEffect(() => {
    if (items.length === 0) {
      setAiStylingData(null);
      return;
    }

    const fetchCartAiStyling = async () => {
      setAiLoading(true);
      const facialHex = user?.facial_hex || '#C8A882';
      const userStyle = user?.style_profile || 'Streetwear';
      try {
        const res = await fetch(getApiUrl(`/cart/${sessionId}/ai_styling?facial_hex=${encodeURIComponent(facialHex)}&user_style=${encodeURIComponent(userStyle)}`));
        if (res.ok) {
          const data = await res.json();
          setAiStylingData(data);
        }
      } catch (err) {
        console.error("AI Cart Styling backend function error:", err);
      } finally {
        setAiLoading(false);
      }
    };

    fetchCartAiStyling();
  }, [items.length, sessionId, user?.facial_hex]);

  const handleUpdateQty = async (sku, currentQty, delta) => {
    const newQty = currentQty + delta;
    if (newQty <= 0) {
      handleRemoveItem(sku);
      return;
    }
    try {
      await fetch(getApiUrl('/cart/qty'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, sku, quantity: newQty })
      });
      fetchCartData();
    } catch (err) {
      console.error("Qty update error:", err);
    }
  };

  const handleRemoveItem = async (sku) => {
    try {
      await fetch(getApiUrl('/cart/remove'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, sku })
      });
      fetchCartData();
    } catch (err) {
      console.error("Remove item error:", err);
    }
  };

  const handleAddSuggestedItem = async (sku) => {
    try {
      await fetch(getApiUrl('/cart/scan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, epc_id: `SKU-PAIR-${sku}` })
      });
      fetchCartData();
    } catch (err) {
      console.error("Add suggested item error:", err);
    }
  };

  const handleApplyPromo = () => {
    const code = promoInput.trim().toUpperCase();
    if (!code) return;
    if (code === 'ETHNIC20' || code === 'RUSH10' || code === 'STREETSTYLE' || code === 'BUY2GET10') {
      setAppliedCode(code);
      setPromoSuccess(`Offer '${code}' applied successfully!`);
      setPromoError('');
    } else {
      setPromoError('Invalid coupon code. Try ETHNIC20 or RUSH10.');
      setPromoSuccess('');
    }
  };

  const calculateDiscount = () => {
    if (!rawTotal) return 0;
    if (appliedCode === 'ETHNIC20') return Math.round(rawTotal * 0.20);
    if (appliedCode === 'RUSH10') return Math.round(rawTotal * 0.10);
    if (appliedCode === 'STREETSTYLE') return 300;
    if (appliedCode === 'BUY2GET10') return 500;
    return cartData?.discount_amount || 0;
  };

  const discount = calculateDiscount();
  const finalTotal = Math.max(0, rawTotal - discount);

  // Active suggestions list based on selected AI Mode
  const getActiveSuggestions = () => {
    if (!aiStylingData) return [];
    if (aiMode === 'footwear') return aiStylingData.recommended_footwear || [];
    if (aiMode === 'accessories') return aiStylingData.recommended_accessories || [];
    // 'outfit': combine bottomwear or topwear recommendations
    const bots = aiStylingData.recommended_bottomwear || [];
    const tops = aiStylingData.recommended_topwear || [];
    return bots.length > 0 ? bots : tops;
  };

  const activeSuggestions = getActiveSuggestions();

  return (
    <div className="w-full min-h-screen bg-[#080810] flex flex-col justify-between pb-24 text-white">
      {/* Top Cart Bar */}
      <div className="sticky top-0 z-20 bg-[#0D0D14]/95 backdrop-blur-md border-b border-[rgba(0,245,255,0.12)] p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00F5FF]/20 to-[#7C4DFF]/20 border border-[rgba(0,245,255,0.3)] flex items-center justify-center">
            <ShoppingBag className="w-5 h-5 text-[#00F5FF]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold font-['Rajdhani'] tracking-wide">MY SMART CART</h2>
              <span className="text-[10px] font-['Space_Mono'] font-bold text-[#00FF88] px-2 py-0.5 rounded bg-[rgba(0,255,136,0.1)] border border-[rgba(0,255,136,0.2)] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00FF88] animate-pulse"></span>
                #{sessionId}
              </span>
            </div>
            <p className="text-[11px] text-[#A0A0B0] font-['Space_Mono']">
              {items.length} {items.length === 1 ? 'Garment' : 'Garments'} in Cavity
            </p>
          </div>
        </div>

        <button
          onClick={() => fetchCartData(true)}
          className={`p-2.5 rounded-xl bg-[#14141E] border border-[rgba(255,255,255,0.08)] text-[#00F5FF] hover:bg-[#1C1C2A] transition-all cursor-pointer ${
            refreshing ? 'animate-spin' : ''
          }`}
          title="Refresh Cart"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {/* Live Cavity Sync Banner */}
        <div className="bg-gradient-to-r from-[#141420] via-[#1A1A2A] to-[#141420] border border-[rgba(0,245,255,0.2)] rounded-2xl p-3.5 flex items-center justify-between shadow-[0_4px_20px_rgba(0,245,255,0.05)]">
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#00FF88] shadow-[0_0_10px_#00FF88]"></div>
            <span className="text-xs font-['Space_Mono'] text-[#D8E4FF] font-medium">
              UHF RFID Cavity Reader Synchronized
            </span>
          </div>
          <span className="text-[10px] font-['Space_Mono'] text-[#00F5FF] bg-[rgba(0,245,255,0.1)] px-2 py-0.5 rounded font-bold">
            REALTIME
          </span>
        </div>

        {/* Offers & Rush Deals Banner */}
        <div
          onClick={onNavigateToOffers}
          className="bg-gradient-to-r from-[#FF9500]/15 via-[#7C4DFF]/15 to-[#00F5FF]/15 border border-[#FF9500]/30 rounded-2xl p-3.5 flex items-center justify-between cursor-pointer hover:border-[#FF9500]/60 transition-all shadow-[0_0_15px_rgba(255,149,0,0.1)]"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#FF9500]/20 border border-[#FF9500]/40 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-[#FFB300] animate-bounce" />
            </div>
            <div>
              <div className="text-xs font-bold text-white font-['Rajdhani'] flex items-center gap-2">
                <span>RUSH DEALS & SKIN TONE OFFERS</span>
                <span className="text-[9px] bg-[#FF3B5C] text-white px-1.5 py-0.2 rounded font-extrabold uppercase">HOT</span>
              </div>
              <p className="text-[10px] text-[#A0A0B0] font-['Space_Mono']">
                Curated for undertone: <strong className="text-[#00F5FF]">{aiStylingData?.undertone_label || 'Warm-Golden'}</strong>
              </p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-[#FFB300]" />
        </div>

        {/* Scanned Cart Item List */}
        {loading ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-10 h-10 border-2 border-[#00F5FF] border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="text-xs text-[#A0A0B0] font-['Space_Mono']">Scanning InnoCart RFID Cavity...</p>
          </div>
        ) : items.length === 0 ? (
          /* Empty Cart State */
          <div className="bg-[#101018] border border-[rgba(255,255,255,0.06)] rounded-3xl p-8 text-center space-y-4 my-4">
            <div className="w-20 h-20 rounded-full bg-[#181824] border border-[rgba(0,245,255,0.2)] flex items-center justify-center mx-auto shadow-[0_0_30px_rgba(0,245,255,0.1)]">
              <ShoppingBag className="w-9 h-9 text-[#4A587A]" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white font-['Rajdhani']">Your Cart is Empty</h3>
              <p className="text-xs text-[#A0A0B0] font-['Space_Mono'] mt-1 max-w-xs mx-auto leading-relaxed">
                Drop garments into the physical InnoCart cavity or click <strong className="text-[#00FF88]">⏬ Drop Tag</strong> in the Hardware Simulator.
              </p>
            </div>
            <div className="pt-2 flex flex-col gap-2">
              <button
                onClick={onNavigateToOffers}
                className="w-full py-3 rounded-xl bg-[rgba(0,245,255,0.1)] border border-[rgba(0,245,255,0.3)] text-[#00F5FF] font-bold text-xs font-['Space_Mono'] hover:bg-[rgba(0,245,255,0.2)] transition-all"
              >
                EXPLORE RUSH DEALS & STYLES
              </button>
            </div>
          </div>
        ) : (
          /* Populated Cart Items */
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-bold text-[#A0A0B0] font-['Space_Mono'] uppercase tracking-wider">
                SCANNED GARMENTS ({items.length})
              </span>
              <span className="text-[10px] text-[#00F5FF] font-['Space_Mono']">
                Auto-synced with Supabase DB
              </span>
            </div>

            {items.map((item, index) => (
              <div
                key={item.sku || index}
                className="bg-[#12121A] border border-[rgba(0,245,255,0.15)] rounded-2xl p-4 flex items-center justify-between gap-3 shadow-[0_4px_15px_rgba(0,0,0,0.4)] hover:border-[rgba(0,245,255,0.35)] transition-all"
              >
                <div className="relative flex-shrink-0">
                  <div
                    className="w-14 h-14 rounded-xl border border-[rgba(255,255,255,0.15)] flex items-center justify-center overflow-hidden bg-[#1A1A24]"
                    style={{ boxShadow: `0 0 15px ${item.major_color_hex || '#00F5FF'}33` }}
                  >
                    {item.image_url ? (
                      <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                    ) : (
                      <div
                        className="w-full h-full flex items-center justify-center font-bold text-xs text-white"
                        style={{ backgroundColor: item.major_color_hex || '#2A2A3A' }}
                      >
                        {item.name ? item.name[0] : 'G'}
                      </div>
                    )}
                  </div>
                  <span className="absolute -bottom-1 -right-1 text-[8px] font-['Space_Mono'] font-bold px-1.5 py-0.2 rounded bg-[#7C4DFF] text-white">
                    {item.style_profile || 'Style'}
                  </span>
                </div>

                <div className="flex-1 min-w-0 space-y-1">
                  <h4 className="text-sm font-bold text-white font-['Rajdhani'] leading-snug truncate">
                    {item.name}
                  </h4>
                  <div className="flex items-center gap-2 flex-wrap text-[10px] font-['Space_Mono'] text-[#A0A0B0]">
                    <span className="px-1.5 py-0.2 rounded bg-[#1C1C28] text-[#00F5FF]">
                      {item.garment_category || 'Topwear'}
                    </span>
                    {item.pattern && <span className="text-[#FF9500] font-medium">{item.pattern}</span>}
                    {item.sku && <span className="text-[#606070] truncate">{item.sku}</span>}
                  </div>
                  <div className="text-sm font-extrabold text-[#00F5FF] font-['Rajdhani'] pt-0.5">
                    ₹{(item.price || 0).toLocaleString('en-IN')}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleRemoveItem(item.sku)}
                    className="p-1.5 text-[#606070] hover:text-[#FF3B5C] transition-colors cursor-pointer"
                    title="Remove item"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <div className="flex items-center gap-1.5 bg-[#1A1A26] border border-[rgba(255,255,255,0.08)] rounded-lg p-1">
                    <button
                      onClick={() => handleUpdateQty(item.sku, item.quantity || 1, -1)}
                      className="w-5 h-5 rounded bg-[#242434] text-white flex items-center justify-center text-xs hover:bg-[#303045] cursor-pointer"
                    >
                      <Minus className="w-3 h-3" />
                    </button>
                    <span className="font-['Space_Mono'] text-xs font-bold w-4 text-center text-white">
                      {item.quantity || 1}
                    </span>
                    <button
                      onClick={() => handleUpdateQty(item.sku, item.quantity || 1, 1)}
                      className="w-5 h-5 rounded bg-[#242434] text-white flex items-center justify-center text-xs hover:bg-[#303045] cursor-pointer"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* AI STYLING BACKEND FUNCTION RECOMMENDATION DRAWER */}
        {items.length > 0 && (
          <div className="bg-[#10101C] border border-[rgba(180,77,255,0.35)] rounded-2xl p-4 space-y-3 shadow-[0_0_25px_rgba(180,77,255,0.12)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#B44DFF] animate-spin" />
                <h4 className="text-xs font-bold text-white font-['Rajdhani'] uppercase tracking-wider">
                  AI OUTFIT COMPANION ({aiStylingData?.undertone_label || 'Warm-Golden'})
                </h4>
              </div>
              <span className="text-[10px] font-['Space_Mono'] font-bold text-[#00FF88] bg-[rgba(0,255,136,0.1)] px-2 py-0.5 rounded border border-[rgba(0,255,136,0.2)]">
                {aiStylingData?.outfit_match_score || 94}% MATCH
              </span>
            </div>

            {/* Category Switcher Tabs */}
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => setAiMode('outfit')}
                className={`py-1.5 rounded-lg font-['Space_Mono'] text-[10px] font-bold flex items-center justify-center gap-1 cursor-pointer transition-all ${
                  aiMode === 'outfit'
                    ? 'bg-[#B44DFF] text-white shadow-[0_0_10px_rgba(180,77,255,0.4)]'
                    : 'bg-[#181826] text-[#A0A0B0] hover:text-white'
                }`}
              >
                <Shirt className="w-3 h-3" />
                <span>OUTFIT</span>
              </button>

              <button
                onClick={() => setAiMode('footwear')}
                className={`py-1.5 rounded-lg font-['Space_Mono'] text-[10px] font-bold flex items-center justify-center gap-1 cursor-pointer transition-all ${
                  aiMode === 'footwear'
                    ? 'bg-[#00F5FF] text-black shadow-[0_0_10px_rgba(0,245,255,0.4)]'
                    : 'bg-[#181826] text-[#A0A0B0] hover:text-white'
                }`}
              >
                <Footprints className="w-3 h-3" />
                <span>FOOTWEAR</span>
              </button>

              <button
                onClick={() => setAiMode('accessories')}
                className={`py-1.5 rounded-lg font-['Space_Mono'] text-[10px] font-bold flex items-center justify-center gap-1 cursor-pointer transition-all ${
                  aiMode === 'accessories'
                    ? 'bg-[#FF9500] text-black shadow-[0_0_10px_rgba(255,149,0,0.4)]'
                    : 'bg-[#181826] text-[#A0A0B0] hover:text-white'
                }`}
              >
                <Crown className="w-3 h-3" />
                <span>ACCESSORIES</span>
              </button>
            </div>

            {/* AI Recommendation Cards List */}
            {aiLoading ? (
              <div className="py-4 text-center text-xs text-[#A0A0B0] font-['Space_Mono']">
                Executing GET /api/cart/{sessionId}/ai_styling backend function...
              </div>
            ) : activeSuggestions.length === 0 ? (
              <div className="py-3 text-center text-xs text-[#A0A0B0] font-['Space_Mono']">
                No matching recommendations found for this category.
              </div>
            ) : (
              <div className="space-y-2.5 pt-1">
                {activeSuggestions.map((s, idx) => (
                  <div
                    key={s.recommended_sku || idx}
                    className="bg-[#181828] border border-[rgba(255,255,255,0.08)] rounded-xl p-3 flex items-center justify-between gap-2 hover:border-[rgba(0,245,255,0.3)] transition-all"
                  >
                    <div className="flex items-center gap-2.5 flex-1 min-w-0">
                      <div className="w-9 h-9 rounded-lg bg-[#202030] flex items-center justify-center text-xs font-bold text-[#00F5FF] flex-shrink-0">
                        #{s.rank}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-white font-['Rajdhani'] truncate">{s.name}</div>
                        <p className="text-[10px] text-[#A0A0B0] font-['Space_Mono'] truncate">{s.match_reason}</p>
                        <div className="text-xs font-extrabold text-[#00F5FF] font-['Rajdhani']">
                          ₹{(s.price || 0).toLocaleString('en-IN')}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Promo Voucher Code Input */}
        {items.length > 0 && (
          <div className="bg-[#12121A] border border-[rgba(255,255,255,0.08)] rounded-2xl p-4 space-y-2">
            <div className="flex items-center gap-2">
              <Tag className="w-4 h-4 text-[#FFB300]" />
              <span className="text-xs font-bold text-white font-['Space_Mono'] uppercase">APPLY OFFER CODE</span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={promoInput}
                onChange={(e) => setPromoInput(e.target.value)}
                placeholder="e.g. ETHNIC20, RUSH10"
                className="flex-1 bg-[#181824] border border-[rgba(255,255,255,0.1)] rounded-xl px-3 py-2 text-xs font-['Space_Mono'] text-white uppercase outline-none focus:border-[#00F5FF]"
              />
              <button
                onClick={handleApplyPromo}
                className="px-4 py-2 bg-gradient-to-r from-[#00F5FF] to-[#7C4DFF] text-black font-extrabold text-xs font-['Space_Mono'] rounded-xl hover:opacity-90 transition-all cursor-pointer"
              >
                APPLY
              </button>
            </div>
            {promoError && <p className="text-[11px] text-[#FF3B5C] font-['Space_Mono']">{promoError}</p>}
            {promoSuccess && <p className="text-[11px] text-[#00FF88] font-['Space_Mono']">{promoSuccess}</p>}
          </div>
        )}

        {/* Payment Summary */}
        {items.length > 0 && (
          <div className="bg-[#12121A] border border-[rgba(0,245,255,0.15)] rounded-2xl p-4 space-y-3 font-['Space_Mono']">
            <h4 className="text-xs font-bold text-[#A0A0B0] uppercase tracking-wider">PAYMENT SUMMARY</h4>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between text-[#A0A0B0]">
                <span>Items Subtotal</span>
                <span className="text-white font-bold">₹{rawTotal.toLocaleString('en-IN')}</span>
              </div>
              {discount > 0 && (
                <div className="flex justify-between text-[#00FF88]">
                  <span>Applied Offer Discount</span>
                  <span className="font-bold">- ₹{discount.toLocaleString('en-IN')}</span>
                </div>
              )}
              <div className="flex justify-between text-[#A0A0B0]">
                <span>Smart Checkout Service Fee</span>
                <span className="text-[#00FF88] font-bold">FREE</span>
              </div>
              <div className="border-t border-[rgba(255,255,255,0.08)] pt-2 flex justify-between text-sm">
                <span className="font-bold text-white">Total Payable Amount</span>
                <span className="font-extrabold text-[#00F5FF] text-base font-['Rajdhani']">
                  ₹{finalTotal.toLocaleString('en-IN')}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Fixed Bottom Checkout Button */}
      {items.length > 0 && (
        <div className="fixed bottom-16 left-0 right-0 max-w-md mx-auto p-4 bg-[#0D0D14]/90 backdrop-blur-md border-t border-[rgba(0,245,255,0.2)] z-30">
          <button
            onClick={() => setIsCheckoutOpen(true)}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#00F5FF] via-[#7C4DFF] to-[#1A1AFF] text-black font-extrabold text-base tracking-widest uppercase font-['Rajdhani'] shadow-[0_0_30px_rgba(0,245,255,0.4)] hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 cursor-pointer"
          >
            <CreditCard className="w-5 h-5 text-black" />
            <span>PAY ₹{finalTotal.toLocaleString('en-IN')} · CHECKOUT NOW</span>
          </button>
        </div>
      )}

      {/* Checkout Modal */}
      {isCheckoutOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-end justify-center p-4">
          <div className="w-full max-w-md bg-[#12121C] border border-[rgba(0,245,255,0.3)] rounded-3xl p-6 space-y-5 animate-in slide-in-from-bottom duration-300">
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.1)] pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-[#00FF88]" />
                <h3 className="text-lg font-bold text-white font-['Rajdhani']">INNO PAY SMART CHECKOUT</h3>
              </div>
              <button onClick={() => setIsCheckoutOpen(false)} className="text-[#A0A0B0] text-sm">✕</button>
            </div>

            <div className="space-y-3 text-xs font-['Space_Mono']">
              <div className="p-3 rounded-xl bg-[#1A1A28] border border-[rgba(0,245,255,0.15)] flex justify-between items-center">
                <div>
                  <div className="text-[10px] text-[#A0A0B0]">CUSTOMER SESSION</div>
                  <div className="font-bold text-white">{user.name} (#{sessionId})</div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-[#A0A0B0]">TOTAL DUE</div>
                  <div className="font-extrabold text-[#00F5FF] text-base">₹{finalTotal.toLocaleString('en-IN')}</div>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#181824] space-y-2">
                <div className="text-[11px] font-bold text-white">PAYMENT METHOD</div>
                <div className="grid grid-cols-2 gap-2">
                  <button className="py-2.5 px-3 rounded-lg bg-[rgba(0,245,255,0.15)] border border-[#00F5FF] text-[#00F5FF] font-bold text-[11px] text-center">
                    UPI / Razorpay
                  </button>
                  <button className="py-2.5 px-3 rounded-lg bg-[#222232] border border-[rgba(255,255,255,0.1)] text-[#A0A0B0] text-[11px] text-center">
                    InnoCart RFID Auto
                  </button>
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                alert(`✓ Payment of ₹${finalTotal.toLocaleString('en-IN')} Successful! Your InnoCart Session #${sessionId} is complete.`);
                setIsCheckoutOpen(false);
              }}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#00FF88] to-[#00F5FF] text-black font-extrabold text-base tracking-widest uppercase font-['Rajdhani'] shadow-[0_0_30px_rgba(0,255,136,0.4)] cursor-pointer"
            >
              CONFIRM & PAY ₹{finalTotal.toLocaleString('en-IN')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
