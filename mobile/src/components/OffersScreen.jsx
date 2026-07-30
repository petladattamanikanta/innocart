import React from 'react';
import { Tag, Sparkles, ArrowLeft, ShoppingBag, Zap, CheckCircle2, ShieldAlert } from 'lucide-react';

export function OffersScreen({ user, onNavigateToCart, onApplyDeal }) {
  const undertone = user?.undertone_label || 'Warm-Golden';

  const OFFERS = [
    {
      code: 'ETHNIC20',
      title: '20% OFF ON ETHNIC WEAR',
      desc: 'Exclusive offer tailored for Warm-Golden undertone skin profiles on Kurtas & Sherwanis.',
      discount: '20% OFF',
      tag: 'PERSONALIZED',
      bgColor: 'from-[#800020]/30 to-[#FFD700]/10',
      borderColor: 'border-[#FFD700]/40',
      accentColor: '#FFD700'
    },
    {
      code: 'RUSH10',
      title: 'RUSH HOUR EXTRA 10% DISCOUNT',
      desc: 'Applicable on all Topwear & Footwear dropped into cavity within next 15 mins.',
      discount: '10% OFF',
      tag: 'RUSH DEAL',
      bgColor: 'from-[#FF3B5C]/20 to-[#FF9500]/10',
      borderColor: 'border-[#FF3B5C]/40',
      accentColor: '#FF3B5C'
    },
    {
      code: 'STREETSTYLE',
      title: '₹300 FLAT OFF ON STREETWEAR',
      desc: 'Valid on Oversized Hoodies, Joggers & Chunky Neon Sneakers.',
      discount: '₹300 OFF',
      tag: 'STREETWEAR',
      bgColor: 'from-[#7C4DFF]/30 to-[#00F5FF]/10',
      borderColor: 'border-[#7C4DFF]/40',
      accentColor: '#7C4DFF'
    },
    {
      code: 'BUY2GET10',
      title: 'COMBO SAVINGS: ₹500 OFF ON 2+ ITEMS',
      desc: 'Automatically pairs Topwear & Bottomwear for maximum color harmony.',
      discount: '₹500 OFF',
      tag: 'COMBO OFFER',
      bgColor: 'from-[#00FF88]/20 to-[#00F5FF]/10',
      borderColor: 'border-[#00FF88]/40',
      accentColor: '#00FF88'
    }
  ];

  return (
    <div className="w-full min-h-screen bg-[#080810] flex flex-col justify-between pb-24 text-white">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-[#0D0D14]/95 backdrop-blur-md border-b border-[rgba(0,245,255,0.12)] p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onNavigateToCart}
            className="p-2 rounded-xl bg-[#14141E] border border-[rgba(255,255,255,0.08)] text-[#00F5FF] hover:bg-[#1C1C2A] cursor-pointer"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-base font-bold font-['Rajdhani'] tracking-wide">RUSH DEALS & OFFERS</h2>
            <p className="text-[11px] text-[#A0A0B0] font-['Space_Mono']">
              Personalized for {user?.name} ({undertone})
            </p>
          </div>
        </div>

        <button
          onClick={onNavigateToCart}
          className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#00F5FF] to-[#7C4DFF] text-black font-extrabold text-xs font-['Space_Mono'] flex items-center gap-1.5 cursor-pointer shadow-[0_0_15px_rgba(0,245,255,0.3)]"
        >
          <ShoppingBag className="w-4 h-4" />
          <span>VIEW CART</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {/* Undertone Banner */}
        <div className="bg-gradient-to-r from-[#141424] via-[#1C1C30] to-[#141424] border border-[rgba(0,245,255,0.25)] rounded-2xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[rgba(0,245,255,0.1)] border border-[rgba(0,245,255,0.3)] flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-[#00F5FF]" />
          </div>
          <div>
            <div className="text-xs font-bold text-white font-['Rajdhani'] flex items-center gap-2">
              <span>AI COLOR HARMONY ENGINE ACTIVE</span>
              <span className="text-[9px] bg-[#00FF88] text-black font-extrabold px-1.5 py-0.2 rounded uppercase">MATCHED</span>
            </div>
            <p className="text-[11px] text-[#A0A0B0] font-['Space_Mono'] mt-0.5 leading-relaxed">
              Offers are customized for your facial HEX <strong className="text-[#00F5FF]">{user?.facial_hex || '#D4A373'}</strong> to maximize undertone contrast.
            </p>
          </div>
        </div>

        {/* Offer Cards */}
        <div className="space-y-3.5">
          {OFFERS.map((offer, idx) => (
            <div
              key={idx}
              className={`bg-gradient-to-br ${offer.bgColor} border ${offer.borderColor} rounded-2xl p-4 space-y-3 shadow-lg relative overflow-hidden`}
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span
                    className="text-[9px] font-['Space_Mono'] font-extrabold px-2 py-0.5 rounded uppercase"
                    style={{ backgroundColor: `${offer.accentColor}25`, color: offer.accentColor, border: `1px solid ${offer.accentColor}55` }}
                  >
                    {offer.tag}
                  </span>
                  <h3 className="text-sm font-extrabold text-white font-['Rajdhani'] tracking-wide pt-1">
                    {offer.title}
                  </h3>
                </div>
                <div className="text-right">
                  <div className="text-base font-extrabold font-['Rajdhani']" style={{ color: offer.accentColor }}>
                    {offer.discount}
                  </div>
                </div>
              </div>

              <p className="text-xs text-[#C0C0D0] font-['Space_Mono'] leading-relaxed">
                {offer.desc}
              </p>

              <div className="flex items-center justify-between pt-2 border-t border-white/10">
                <div className="flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5 text-[#00F5FF]" />
                  <span className="text-xs font-bold font-['Space_Mono'] text-[#00F5FF] tracking-wider">
                    {offer.code}
                  </span>
                </div>

                <button
                  onClick={() => {
                    if (onApplyDeal) onApplyDeal(offer.code);
                    onNavigateToCart();
                  }}
                  className="px-4 py-2 rounded-xl bg-white text-black font-extrabold text-xs font-['Space_Mono'] hover:bg-[#00F5FF] transition-all flex items-center gap-1.5 cursor-pointer shadow-md"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-black" />
                  <span>APPLY & VIEW CART</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Redirect Button to Cart */}
      <div className="p-4 bg-[#0D0D14]/90 backdrop-blur-md border-t border-[rgba(0,245,255,0.2)]">
        <button
          onClick={onNavigateToCart}
          className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-[#00F5FF] via-[#7C4DFF] to-[#1A1AFF] text-black font-extrabold text-sm tracking-widest uppercase font-['Rajdhani'] flex items-center justify-center gap-2 cursor-pointer shadow-[0_0_20px_rgba(0,245,255,0.3)]"
        >
          <ShoppingBag className="w-5 h-5 text-black" />
          <span>RETURN TO CART ITEMS SECTION</span>
        </button>
      </div>
    </div>
  );
}
