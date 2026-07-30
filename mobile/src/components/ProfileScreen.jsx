import React, { useState } from 'react';
import { ArrowLeft, User, Mail, Sparkles, Shield, Palette, Check, Save } from 'lucide-react';
import { getApiUrl } from '../apiConfig';

const FACIAL_HEX_PRESETS = [
  { hex: '#D4A373', label: 'Warm-Golden' },
  { hex: '#E0AC69', label: 'Cool-Rosy' },
  { hex: '#C68642', label: 'Deep-Warm' },
  { hex: '#F1C27D', label: 'Neutral-Beige' },
  { hex: '#8D5524', label: 'Deep-Golden' },
  { hex: '#FFDBAC', label: 'Fair-Cool' },
];

export function ProfileScreen({ user, onBack, onUpdateUser }) {
  const [facialHex, setFacialHex] = useState(user.facial_hex || '#D4A373');
  const [undertoneLabel, setUndertoneLabel] = useState(user.undertone_label || 'Warm-Golden');
  const [savedMsg, setSavedMsg] = useState('');

  const handleSave = () => {
    const updatedUser = {
      ...user,
      facial_hex: facialHex,
      undertone_label: undertoneLabel
    };
    localStorage.setItem('innocart_user', JSON.stringify(updatedUser));
    onUpdateUser(updatedUser);
    setSavedMsg('Styling preferences saved successfully!');
    setTimeout(() => setSavedMsg(''), 3000);
  };

  return (
    <div className="w-full min-h-screen bg-[#080810] flex flex-col justify-between p-5 pb-10 overflow-y-auto">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 pt-4">
          <button
            onClick={onBack}
            className="p-2 rounded-xl bg-[#1C1C1E] border border-[rgba(255,255,255,0.1)] text-white hover:bg-white/20"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h2 className="text-xl font-bold font-['Rajdhani'] text-white">Personal Styling Profile</h2>
        </div>

        {/* User Card Header */}
        <div className="bg-[#141418] border border-[rgba(0,245,255,0.2)] rounded-3xl p-5 flex items-center gap-4 shadow-[0_0_20px_rgba(0,245,255,0.08)]">
          <div
            className="w-16 h-16 rounded-2xl border-2 border-[#00F5FF] p-0.5 flex items-center justify-center flex-shrink-0 shadow-[0_0_20px_rgba(0,245,255,0.3)]"
            style={{ backgroundColor: facialHex }}
          >
            <span className="font-bold text-lg text-black">{user.name ? user.name[0].toUpperCase() : 'U'}</span>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white font-['Rajdhani']">{user.name}</h3>
            <p className="text-xs text-[#A0A0B0] font-['Space_Mono']">{user.email}</p>
            {user.last_login_at && (
              <p className="text-[10px] text-[#00F5FF] font-['Space_Mono'] mt-0.5">
                Last Sign-In: {user.last_login_at}
              </p>
            )}
            <div className="mt-1.5 flex flex-wrap gap-1.5 items-center">
              <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[rgba(124,77,255,0.2)] border border-[rgba(124,77,255,0.4)] text-[#7C4DFF] text-[10px] font-['Space_Mono'] font-bold">
                <Sparkles className="w-3 h-3 text-[#7C4DFF]" /> {undertoneLabel}
              </div>
              {user.skin_texture && (
                <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[rgba(0,245,255,0.15)] border border-[rgba(0,245,255,0.3)] text-[#00F5FF] text-[10px] font-['Space_Mono'] font-bold">
                  ✨ {user.skin_texture} ({Math.round((user.skin_texture_score || 0.85) * 100)}%)
                </div>
              )}
            </div>
          </div>
        </div>

        {savedMsg && (
          <div className="p-3 bg-green-950/50 border border-green-500/30 rounded-xl text-[#00E676] text-xs text-center font-['Space_Mono']">
            ✓ {savedMsg}
          </div>
        )}

        {/* Undertone Palette Selector */}
        <div className="bg-[#141418] border border-[rgba(255,255,255,0.08)] rounded-2xl p-4 space-y-3">
          <label className="text-xs font-bold text-white font-['Rajdhani'] flex items-center gap-2">
            <Palette className="w-4 h-4 text-[#00F5FF]" /> Skin Undertone & Hex Classification
          </label>
          <div className="grid grid-cols-3 gap-2">
            {FACIAL_HEX_PRESETS.map((preset) => (
              <button
                key={preset.hex}
                type="button"
                onClick={() => {
                  setFacialHex(preset.hex);
                  setUndertoneLabel(preset.label);
                }}
                className={`p-2.5 rounded-xl border flex flex-col items-center text-center transition-all ${
                  facialHex === preset.hex
                    ? 'border-[#00F5FF] bg-[rgba(0,245,255,0.15)] shadow-[0_0_15px_rgba(0,245,255,0.2)]'
                    : 'border-[rgba(255,255,255,0.08)] bg-[#1C1C1E] opacity-70'
                }`}
              >
                <span className="w-6 h-6 rounded-full border border-white/20 mb-1" style={{ backgroundColor: preset.hex }} />
                <span className="text-[10px] font-bold text-white leading-tight">{preset.label}</span>
                <span className="text-[9px] text-[#A0A0B0] font-['Space_Mono']">{preset.hex}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        className="w-full mt-6 py-3.5 rounded-xl bg-gradient-to-r from-[#00F5FF] to-[#1A1AFF] text-black font-bold text-sm tracking-wider uppercase font-['Rajdhani'] shadow-[0_0_25px_rgba(0,245,255,0.3)] hover:opacity-90 flex items-center justify-center gap-2"
      >
        <Save className="w-4 h-4" /> Save Profile
      </button>
    </div>
  );
}

