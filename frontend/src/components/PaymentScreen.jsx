import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../apiConfig';

export function PaymentScreen({ cartId, cartSummary, onBack, onPaymentComplete }) {
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [timeLeft, setTimeLeft] = useState(107); // 01:47 left
  const amountToPay = cartSummary?.cart_total || 3346;

  useEffect(() => {
    // Generate UPI QR code URL or fetch checkout QR from backend
    fetch(getApiUrl(`/cart/${cartId}/checkout/qr`), { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data && data.qr_url) {
          setQrCodeUrl(data.qr_url);
        } else {
          setQrCodeUrl(`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=upi://pay?pa=innocart@razorpay%26pn=InnoCart%26am=${amountToPay}%26cu=INR%26tn=Cart_${cartId}`);
        }
      })
      .catch(() => {
        setQrCodeUrl(`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=upi://pay?pa=innocart@razorpay%26pn=InnoCart%26am=${amountToPay}%26cu=INR%26tn=Cart_${cartId}`);
      });
  }, [cartId, amountToPay]);

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

  const handleSimulatePayment = () => {
    fetch(getApiUrl('/payments/mock_pay'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: cartId, txn_id: "RZP8821049" })
    })
      .then(() => onPaymentComplete("RZP8821049"))
      .catch(() => onPaymentComplete("RZP8821049"));
  };

  return (
    <div className="flex-1 flex items-center justify-center gap-12 px-10 py-5 bg-[radial-gradient(ellipse_at_50%_50%,rgba(26,26,255,0.1)_0%,transparent_70%)] bg-[#0D0D0D] overflow-hidden">
      {/* Left Column: Amount & WebSocket Status */}
      <div className="flex flex-col gap-3.5 flex-1 max-w-[360px]">
        <div className="font-['Rajdhani'] text-2xl font-bold leading-tight tracking-wide text-white">
          Scan &<br />
          <span className="text-[#00F5FF]">Pay Instantly</span>
        </div>

        <div className="bg-[#1C1C1E] border border-[rgba(0,245,255,0.12)] rounded-xl p-3.5">
          <div className="font-['Space_Mono'] text-[10px] text-[#606070] tracking-widest uppercase">
            AMOUNT TO PAY
          </div>
          <div className="font-['Rajdhani'] text-4xl font-bold text-[#00F5FF] mt-0.5">
            ₹{amountToPay.toLocaleString('en-IN')}
          </div>
          <div className="text-xs text-[#00E676] mt-0.5 font-medium">
            ✓ You saved ₹200 with INNO200
          </div>
        </div>

        {/* Supported UPI Apps */}
        <div className="flex gap-2">
          <div className="bg-[#2E2E34] border border-[rgba(255,255,255,0.07)] rounded-lg px-3 py-1.5 text-[11px] font-semibold text-[#A0A0B0] flex items-center gap-1">
            📱 GPay
          </div>
          <div className="bg-[#2E2E34] border border-[rgba(255,255,255,0.07)] rounded-lg px-3 py-1.5 text-[11px] font-semibold text-[#A0A0B0] flex items-center gap-1">
            📱 PhonePe
          </div>
          <div className="bg-[#2E2E34] border border-[rgba(255,255,255,0.07)] rounded-lg px-3 py-1.5 text-[11px] font-semibold text-[#A0A0B0] flex items-center gap-1">
            📱 Paytm
          </div>
          <div className="bg-[#2E2E34] border border-[rgba(255,255,255,0.07)] rounded-lg px-3 py-1.5 text-[11px] font-semibold text-[#A0A0B0]">
            + more
          </div>
        </div>

        {/* WebSocket Payment Listener Status */}
        <div className="bg-[rgba(0,230,118,0.08)] border border-[rgba(0,230,118,0.2)] rounded-lg px-3 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#00E676] shadow-[0_0_6px_#00E676] animate-rfid-blink"></div>
            <span className="text-[10px] text-[#A0A0B0]">WebSocket listening for payment</span>
          </div>
          <span className="font-['Space_Mono'] text-xs text-[#00E676] font-bold">
            {formatTimer(timeLeft)} left
          </span>
        </div>

        {/* Back & Dev Simulate Buttons */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={onBack}
            className="bg-[#1C1C1E] border border-[rgba(255,255,255,0.07)] text-[#A0A0B0] text-xs px-3.5 py-1.5 rounded-lg cursor-pointer hover:text-white"
          >
            ← Back
          </button>
          <button
            onClick={handleSimulatePayment}
            className="bg-[#00E676] text-black text-xs font-bold font-['Rajdhani'] px-3.5 py-1.5 rounded-lg tracking-wider uppercase cursor-pointer hover:opacity-90"
          >
            ⚡ Simulate Pay Confirm
          </button>
        </div>
      </div>

      {/* Right Column: Payment QR Frame */}
      <div className="flex flex-col items-center gap-3">
        <div className="w-[170px] h-[170px] bg-white rounded-xl p-2.5 relative shadow-[0_0_40px_rgba(0,245,255,0.25),0_0_80px_rgba(0,245,255,0.1)] flex items-center justify-center">
          {qrCodeUrl && (
            <img src={qrCodeUrl} alt="UPI QR" className="w-full h-full object-contain rounded" />
          )}
          {/* Animated Laser Scanning Line */}
          <div className="absolute inset-x-2.5 h-0.5 bg-gradient-to-r from-transparent via-[#00F5FF] to-transparent shadow-[0_0_15px_#00F5FF] animate-scan-line"></div>
        </div>

        <div className="font-['Space_Mono'] text-[10px] text-[#606070] text-center tracking-wider leading-relaxed uppercase">
          innocart · CART {cartId}<br />
          UPI · ₹{amountToPay.toFixed(2)}
        </div>
      </div>
    </div>
  );
}
