import React from 'react';
import { Sparkles, Zap } from 'lucide-react';

export function WelcomeScreen({ cartId }) {
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=innocart://session?cart_id=${cartId}`;

  return (
    <div className="flex-1 flex items-center justify-between px-14 py-8 bg-[radial-gradient(ellipse_at_30%_50%,rgba(26,26,255,0.18)_0%,transparent_60%),radial-gradient(ellipse_at_70%_80%,rgba(0,245,255,0.08)_0%,transparent_50%)] bg-[#0D0D0D] relative overflow-hidden">
      
      {/* Left Column: Headline & Onboarding Steps */}
      <div className="flex flex-col gap-5 max-w-md z-10">
        <div className="inline-flex items-center gap-2 bg-[#1C1C1E] border border-[rgba(0,245,255,0.2)] text-[#00F5FF] text-[11px] font-['Space_Mono'] font-bold px-3 py-1.5 rounded-full w-fit">
          <Zap className="w-3.5 h-3.5 text-[#FFB300]" /> Autonomous Shopping Cart Kiosk
        </div>

        <div className="font-['Rajdhani'] text-5xl font-bold leading-none tracking-wider text-white">
          Smart.<br />
          Scan. <span className="text-[#00F5FF]">Shop.</span>
        </div>

        <p className="text-[#A0A0B0] text-xs leading-relaxed max-w-[320px]">
          Welcome to InnoCart! Scan the QR code with your InnoCart app to pair your profile and begin shopping.
        </p>

        <div className="flex flex-col gap-2.5 mt-1">
          <div className="flex items-center gap-3 text-xs text-[#A0A0B0]">
            <div className="w-5 h-5 rounded-full bg-[#1A1AFF] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
              1
            </div>
            <span>Open <strong className="text-white">InnoCart Companion</strong> app on your phone</span>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#A0A0B0]">
            <div className="w-5 h-5 rounded-full bg-[#1A1AFF] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
              2
            </div>
            <span>Tap <strong className="text-white">Scan Cart QR</strong></span>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#A0A0B0]">
            <div className="w-5 h-5 rounded-full bg-[#1A1AFF] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
              3
            </div>
            <span>Point phone camera at the QR code on this screen</span>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#A0A0B0]">
            <div className="w-5 h-5 rounded-full bg-[#1A1AFF] text-white font-bold text-[10px] flex items-center justify-center flex-shrink-0">
              4
            </div>
            <span>Profile pairs instantly — start dropping garments</span>
          </div>
        </div>
      </div>

      {/* Right Column: High-Contrast Session QR Code Frame */}
      <div className="flex flex-col items-center gap-4 z-10">
        <div className="w-[180px] h-[180px] bg-white rounded-2xl p-3 relative animate-qr-pulse flex items-center justify-center shadow-[0_0_40px_rgba(0,245,255,0.25)]">
          <img src={qrUrl} alt="Scan Cart QR" className="w-full h-full object-contain rounded-lg" />
          
          {/* Corner Reticles */}
          <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-[#00F5FF] rounded-tl-lg"></div>
          <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-[#00F5FF] rounded-tr-lg"></div>
          <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-[#00F5FF] rounded-bl-lg"></div>
          <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-[#00F5FF] rounded-br-br-lg"></div>
        </div>

        <div className="text-center space-y-1">
          <div className="font-['Space_Mono'] text-[11px] text-[#606070] tracking-widest uppercase">
            CART #{cartId}
          </div>
          <div className="text-xs text-[#00F5FF] font-bold tracking-wider animate-blink flex items-center justify-center gap-1">
            <Sparkles className="w-3.5 h-3.5" /> SCAN WITH PHONE CAMERA TO START
          </div>
        </div>
      </div>
    </div>
  );
}
