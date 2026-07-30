import React, { useState, useEffect, useRef } from 'react';
import { X, CheckCircle2, Zap, Camera, AlertCircle, Sparkles } from 'lucide-react';
import { Html5Qrcode } from 'html5-qrcode';
import { getMobileApiUrl } from '../apiConfig';
import { Capacitor } from '@capacitor/core';

export function QRScannerModal({ user, onClose, onSyncComplete }) {
  const [syncing, setSyncing] = useState(false);
  const [successData, setSuccessData] = useState(null);
  const [syncedSessionId, setSyncedSessionId] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [cameraPermissionError, setCameraPermissionError] = useState(false);
  const html5QrCodeRef = useRef(null);
  const isProcessingRef = useRef(false);

  useEffect(() => {
    let isMounted = true;
    const scannerId = "reader-container";

    const startScanner = async () => {
      try {
        const html5QrCode = new Html5Qrcode(scannerId);
        html5QrCodeRef.current = html5QrCode;

        const config = { fps: 10, qrbox: { width: 240, height: 240 } };

        await html5QrCode.start(
          { facingMode: "environment" },
          config,
          (decodedText) => {
            if (isMounted && !isProcessingRef.current) {
              handleDecodedQrText(decodedText);
            }
          },
          () => {
            // Quiet frame scan error (no QR in frame)
          }
        );
      } catch (err) {
        console.error("Camera scanner initialization error:", err);
        if (isMounted) {
          setCameraPermissionError(true);
        }
      }
    };

    const timeout = setTimeout(startScanner, 300);

    return () => {
      isMounted = false;
      clearTimeout(timeout);
      if (html5QrCodeRef.current && html5QrCodeRef.current.isScanning) {
        html5QrCodeRef.current.stop().catch((e) => console.log("Stop error:", e));
      }
    };
  }, []);

  // Strict Cart QR Validation Function
  const parseCartIdFromQr = (qrText) => {
    if (!qrText) return null;
    const cleanText = qrText.trim();

    // 1. Check for URL / URI schema parameters (e.g. innocart://session?cart_id=IC-042 or https://innocart.io/session?cart_id=IC-042)
    if (cleanText.includes('cart_id=')) {
      try {
        const queryString = cleanText.split('?')[1];
        if (queryString) {
          const urlParams = new URLSearchParams(queryString);
          const cartId = urlParams.get('cart_id');
          if (cartId && cartId.trim().length > 0) {
            return cartId.trim().toUpperCase();
          }
        }
      } catch (e) {
        console.error("URL parse error:", e);
      }
    }

    // 2. Check for explicit cart ID formats (e.g. IC-042, CART-042, INNOCART-042)
    if (/^(IC|CART|INNOCART)[-_][A-Z0-9_-]+$/i.test(cleanText)) {
      return cleanText.toUpperCase();
    }

    // 3. Reject random non-cart QR codes
    return null;
  };

  const handleDecodedQrText = async (qrText) => {
    const targetSession = parseCartIdFromQr(qrText);

    if (!targetSession) {
      // Invalid non-cart QR code scanned! Show error and keep camera active
      setErrorMsg('⚠️ Invalid QR Code. Please scan an official InnoCart Kiosk QR Code.');
      setTimeout(() => setErrorMsg(''), 4000);
      return;
    }

    isProcessingRef.current = true;
    setSyncedSessionId(targetSession);

    // Stop scanner camera feed on valid scan
    if (html5QrCodeRef.current && html5QrCodeRef.current.isScanning) {
      try {
        await html5QrCodeRef.current.stop();
      } catch (e) {
        console.error("Stop error:", e);
      }
    }

    setSyncing(true);
    setErrorMsg('');

    try {
      const userPayload = {
        session_id: targetSession,
        user_id: user.user_id || 'USR-001',
        name: user.name || 'Customer',
        mobile: user.mobile || user.email || '+91 98765 43210',
        facial_hex: user.facial_hex || '#D4A373',
        undertone_label: user.undertone_label || 'Warm-Golden'
      };

      let data;
      if (Capacitor.isNativePlatform() && Capacitor.Plugins?.SessionInitiation) {
        try {
          const nativeRes = await Capacitor.Plugins.SessionInitiation.initiateSession({
            ...userPayload,
            backend_url: 'https://innocart-backend.onrender.com'
          });
          data = { status: 'success', detail: nativeRes.message, native: true };
        } catch (nativeErr) {
          console.warn("Native plugin notice, attempting HTTP fetch fallback:", nativeErr);
          const res = await fetch(getMobileApiUrl('/session/initiate'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userPayload)
          });
          data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || 'Failed to sync credentials with cart kiosk.');
          }
        }
      } else {
        const res = await fetch(getMobileApiUrl('/session/initiate'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(userPayload)
        });
        data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Failed to sync credentials with cart kiosk.');
        }
      }

      setSuccessData(data);
      if (onSyncComplete) onSyncComplete(targetSession);
    } catch (err) {
      setErrorMsg(err.message);
      isProcessingRef.current = false;
    } finally {
      setSyncing(false);
    }
  };

  const handleClose = async () => {
    if (html5QrCodeRef.current && html5QrCodeRef.current.isScanning) {
      try {
        await html5QrCodeRef.current.stop();
      } catch (e) {
        console.error("Stop error on close:", e);
      }
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-[#080810]/95 backdrop-blur-xl z-50 flex flex-col justify-between p-6 animate-fade-in overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between pt-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-[rgba(0,245,255,0.15)] border border-[rgba(0,245,255,0.3)] flex items-center justify-center text-[#00F5FF]">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white font-['Rajdhani'] leading-none">Cart QR Scanner</h3>
            <span className="text-[10px] text-[#A0A0B0] font-['Space_Mono']">Scanning for {user.name}</span>
          </div>
        </div>

        <button
          onClick={handleClose}
          className="w-9 h-9 rounded-full bg-[#1C1C1E] border border-[rgba(255,255,255,0.1)] flex items-center justify-center text-white hover:bg-white/20 cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Main Viewfinder / Success Card Section */}
      <div className="flex-1 flex flex-col items-center justify-center my-6">
        {!successData ? (
          <div className="w-full max-w-xs space-y-5 text-center">
            {/* Custom High-Fidelity Scanner Frame */}
            <div className="w-64 h-64 mx-auto relative rounded-3xl border-2 border-[#00F5FF]/40 bg-[#111116] overflow-hidden shadow-[0_0_60px_rgba(0,245,255,0.25)] flex flex-col items-center justify-center">
              
              {/* HTML5 QR Code Video Container */}
              <div id="reader-container" className="w-full h-full object-cover"></div>

              {/* Glowing Corner Reticles */}
              <div className="absolute top-2 left-2 w-7 h-7 border-t-[3px] border-l-[3px] border-[#00F5FF] rounded-tl-xl pointer-events-none z-10"></div>
              <div className="absolute top-2 right-2 w-7 h-7 border-t-[3px] border-r-[3px] border-[#00F5FF] rounded-tr-xl pointer-events-none z-10"></div>
              <div className="absolute bottom-2 left-2 w-7 h-7 border-b-[3px] border-l-[3px] border-[#00F5FF] rounded-bl-xl pointer-events-none z-10"></div>
              <div className="absolute bottom-2 right-2 w-7 h-7 border-b-[3px] border-r-[3px] border-[#00F5FF] rounded-br-xl pointer-events-none z-10"></div>

              {/* Animated Laser Scanning Line */}
              <div className="absolute inset-x-3 h-0.5 bg-gradient-to-r from-transparent via-[#00F5FF] to-transparent shadow-[0_0_15px_#00F5FF] animate-scan-laser pointer-events-none z-10"></div>

              {cameraPermissionError && (
                <div className="absolute inset-0 bg-[#111116] p-4 flex flex-col items-center justify-center text-center space-y-2 z-20">
                  <AlertCircle className="w-8 h-8 text-[#FF3B30]" />
                  <div className="text-xs font-bold text-white">Camera Access Required</div>
                  <div className="text-[10px] text-[#A0A0B0] font-['Space_Mono']">
                    Please allow camera permission in browser/device settings to scan Cart QR codes.
                  </div>
                </div>
              )}
            </div>

            {/* Error Message for Invalid Non-Cart QR Codes */}
            {errorMsg && (
              <div className="p-3 bg-red-950/70 border border-red-500/40 rounded-xl text-red-300 text-xs font-['Space_Mono'] animate-bounce">
                {errorMsg}
              </div>
            )}

            {syncing ? (
              <div className="text-xs text-[#00F5FF] font-['Space_Mono'] animate-pulse font-bold">
                ⚡ InnoCart QR Detected! Syncing profile for {user.name}...
              </div>
            ) : (
              <div className="text-xs text-[#A0A0B0] font-['Exo_2'] leading-relaxed">
                Point camera at the Session QR Code on the InnoCart 7" Touchscreen Kiosk.
              </div>
            )}
          </div>
        ) : (
          /* Success Confirmation Card */
          <div className="w-full max-w-xs bg-[#141418] border-2 border-[#00E676] rounded-3xl p-6 text-center space-y-4 shadow-[0_0_40px_rgba(0,230,118,0.2)] animate-scale-up">
            <div className="w-16 h-16 rounded-full bg-[rgba(0,230,118,0.15)] border-2 border-[#00E676] mx-auto flex items-center justify-center text-[#00E676]">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div>
              <h4 className="text-xl font-bold font-['Rajdhani'] text-white">Cart Session Linked!</h4>
              <p className="text-xs text-[#A0A0B0] mt-1 font-['Space_Mono']">
                Session <span className="text-[#00F5FF] font-bold">{syncedSessionId || 'IC-042'}</span> synced.
              </p>
            </div>

            <div className="bg-[#1C1C1E] p-3 rounded-2xl border border-[rgba(255,255,255,0.08)] text-left text-xs space-y-1.5 font-['Space_Mono']">
              <div className="flex justify-between text-[#A0A0B0]">
                <span>Customer:</span>
                <span className="text-white font-bold">{user.name}</span>
              </div>
              <div className="flex justify-between text-[#A0A0B0]">
                <span>Contact:</span>
                <span className="text-white font-bold">{user.mobile || user.email}</span>
              </div>
              <div className="flex justify-between text-[#A0A0B0]">
                <span>Undertone:</span>
                <span className="text-[#00F5FF] font-bold">{user.undertone_label || 'Warm-Golden'}</span>
              </div>
              <div className="flex justify-between text-[#A0A0B0]">
                <span>Skin Hex:</span>
                <span className="text-white font-bold flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: user.facial_hex || '#D4A373' }} />
                  {user.facial_hex || '#D4A373'}
                </span>
              </div>
            </div>

            <button
              onClick={handleClose}
              className="w-full py-3 rounded-xl bg-[#00E676] text-black font-bold text-sm tracking-wider uppercase font-['Rajdhani'] shadow-[0_0_20px_rgba(0,230,118,0.3)] cursor-pointer"
            >
              Done & Return Home
            </button>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="text-center pb-2">
        <p className="text-[11px] text-[#A0A0B0] flex items-center justify-center gap-1">
          <Sparkles className="w-3.5 h-3.5 text-[#00F5FF]" /> Strictly validates official InnoCart Session QR Codes
        </p>
      </div>
    </div>
  );
}
