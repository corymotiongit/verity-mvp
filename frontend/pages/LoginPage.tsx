import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Check, ArrowRight, ArrowLeft, Sun, Moon, AlertCircle } from 'lucide-react';
import { toggleTheme } from '../services/themeStore';
import { useTheme } from '../services/useTheme';
import { authV2Api } from '../services/api';

type LoginStep = 'PHONE' | 'OTP' | 'SUCCESS';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
    // Local MVP convenience:
    // - default to mock auth in dev builds so the demo isn't blocked by n8n/WhatsApp.
    // - can be overridden via VITE_AUTH_MOCK=true/false.
        const rawAuthMock = (import.meta as any).env?.VITE_AUTH_MOCK;
        const AUTH_MOCK = typeof rawAuthMock === 'string'
                ? rawAuthMock === 'true'
                : (import.meta as any).env?.DEV === true;
  const [step, setStep] = useState<LoginStep>('PHONE');
  const [phoneNumber, setPhoneNumber] = useState('');
    const [userId, setUserId] = useState<string>('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
    const theme = useTheme();
    const isDark = theme === 'dark';
  
  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Check if already authenticated
  useEffect(() => {
    if (localStorage.getItem('verity_token')) {
        navigate('/files', { replace: true });
    }
  }, [navigate]);

    // Theme Toggle Logic
    const onToggleTheme = () => toggleTheme();

  // Handle Phone Submit
    const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (phoneNumber.length < 10) {
        setError('Ingresa un número de 10 dígitos.');
        return;
    }
    
    setLoading(true);
    setError(null);

    try {
      // wa_id canonical for this MVP = E.164-ish phone string
      const derivedUserId = `+52${phoneNumber}`;
      setUserId(derivedUserId);

      // In v2, requesting/sending the OTP happens via WhatsApp/n8n out-of-band.
      // Frontend just proceeds to OTP validation.
      setStep('OTP');
    } catch (err: any) {
      setError(err?.message || 'No se pudo continuar.');
    } finally {
      setLoading(false);
    }
  };

  // Handle OTP Verification
    const verifyOtp = async () => {
    const code = otp.join('');
    if (code.length !== 6) return;

    // Local MVP mock: accept fixed OTP without calling backend.
    if (AUTH_MOCK) {
        if (code === '123456') {
            localStorage.setItem('verity_token', 'local-dev-token');
            setStep('SUCCESS');
            setTimeout(() => {
                navigate('/files', { replace: true });
            }, 200);
            return;
        }

        setError('Código incorrecto. Intenta de nuevo.');
        setOtp(['', '', '', '', '', '']);
        otpInputRefs.current[0]?.focus();
        return;
    }

    setLoading(true);
    setError(null);

    try {
      await authV2Api.otpValidate(userId, code);
      setStep('SUCCESS');
      setTimeout(() => {
        navigate('/files', { replace: true });
      }, 800);
      return;
    } catch (err: any) {
      const msg = err?.message || 'No se pudo validar el código.';
      setError(msg);
      setOtp(['', '', '', '', '', '']);
      otpInputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  // OTP Input Handlers
  const handleOtpChange = (index: number, value: string) => {
        const v = (value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
        if (!v) {
                const cleared = [...otp];
                cleared[index] = '';
                setOtp(cleared);
                return;
        }

    const newOtp = [...otp];
        newOtp[index] = v.substring(v.length - 1); // Take last valid char
    setOtp(newOtp);

    // Auto advance
    if (value && index < 5) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
    }
    if (e.key === 'Enter') {
        verifyOtp();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedRaw = e.clipboardData.getData('text') || '';
    const pasted = pastedRaw.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6).split('');
    if (!pasted.length) return;

    const newOtp = [...otp];
    pasted.forEach((char, i) => {
        if (i < 6) newOtp[i] = char;
    });
    setOtp(newOtp);
    // Focus the next empty input or the last one
    const nextIndex = Math.min(pasted.length, 5);
    otpInputRefs.current[nextIndex]?.focus();
  };

  const maskedPhone = `+52 155 **** **${phoneNumber.slice(-2)}`;

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-base relative p-4">
        {/* Theme Toggle */}
        <button 
            onClick={onToggleTheme}
            className="absolute top-6 right-6 p-2 rounded-full text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
        >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* Main Card */}
        <div className="w-full max-w-[400px] bg-bg-surface border border-border-default rounded-2xl shadow-2xl p-8 md:p-12 animate-in fade-in zoom-in duration-300">
            
            {/* Header / Logo */}
            <div className="flex flex-col items-center mb-8">
                <div className="w-12 h-12 bg-accent-success rounded-xl flex items-center justify-center shadow-glow-success mb-4">
                    <span className="font-bold text-bg-base text-2xl">V</span>
                </div>
                {step === 'SUCCESS' ? (
                     <h2 className="text-xl font-bold text-text-primary">¡Bienvenido!</h2>
                ) : (
                    <span className="font-sans font-semibold text-lg tracking-tight text-text-primary">Verity</span>
                )}
            </div>

            {/* Step 1: Phone Input */}
            {step === 'PHONE' && (
                <form onSubmit={handlePhoneSubmit} className="space-y-6 animate-in slide-in-from-right duration-300">
                    <div className="text-center space-y-2">
                        <h1 className="text-xl font-bold text-text-primary">Inicia sesión</h1>
                        <p className="text-sm text-text-muted">Ingresa tu número para recibir un código OTP vía WhatsApp.</p>
                    </div>

                    <div className="space-y-2">
                        <div className="flex gap-3">
                             <div className="flex items-center justify-center gap-1 bg-bg-elevated border border-border-default rounded-lg px-3 py-2 w-24">
                                <span className="text-xl leading-none">🇲🇽</span>
                                <span className="text-sm font-medium text-text-secondary">+52</span>
                             </div>
                             <input 
                                type="tel"
                                value={phoneNumber}
                                onChange={(e) => {
                                    const val = e.target.value.replace(/\D/g, '');
                                    if(val.length <= 10) setPhoneNumber(val);
                                }}
                                placeholder="Número (10 dígitos)"
                                className="flex-1 bg-bg-base border border-border-default rounded-lg px-3 py-2 text-text-primary focus:border-accent-success focus:outline-none placeholder-text-muted transition-all"
                                disabled={loading}
                                autoFocus
                             />
                        </div>
                    </div>

                    <button 
                        type="submit"
                        disabled={loading || phoneNumber.length < 10}
                        className="w-full flex items-center justify-center gap-2 bg-accent-success text-bg-base font-bold py-3 rounded-lg hover:bg-accent-success/90 disabled:opacity-50 disabled:cursor-not-allowed shadow-glow-success transition-all"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                            <>Enviar código <ArrowRight className="w-4 h-4" /></>
                        )}
                    </button>

                    {error && (
                        <div className="flex items-center justify-center gap-2 text-accent-danger text-xs animate-in fade-in slide-in-from-top-1">
                            <AlertCircle className="w-3 h-3" />
                            <span>{error}</span>
                        </div>
                    )}

                    <p className="text-[10px] text-center text-text-muted">
                        Al continuar, aceptas nuestros <a href="#" className="underline hover:text-text-primary">Términos de Servicio</a> y <a href="#" className="underline hover:text-text-primary">Política de Privacidad</a>.
                    </p>
                </form>
            )}

            {/* Step 2: OTP Input */}
            {step === 'OTP' && (
                <div className="space-y-6 animate-in slide-in-from-right duration-300">
                    <div className="text-center space-y-2">
                        <h1 className="text-xl font-bold text-text-primary">Verifica tu código</h1>
                        <p className="text-sm text-text-muted">Revisa WhatsApp en <span className="font-semibold">{maskedPhone}</span> y escribe el código.</p>
                    </div>

                    <div className="space-y-4">
                        <div className="flex justify-center gap-2" onPaste={handlePaste}>
                            {otp.map((digit, index) => (
                                <input
                                    key={index}
                                    ref={(el) => (otpInputRefs.current[index] = el)}
                                    type="text"
                                    inputMode="text"
                                    autoCapitalize="characters"
                                    maxLength={1}
                                    value={digit}
                                    onChange={(e) => handleOtpChange(index, e.target.value)}
                                    onKeyDown={(e) => handleOtpKeyDown(index, e)}
                                    className="w-10 h-12 text-center text-lg font-semibold bg-bg-base border border-border-default rounded-lg text-text-primary focus:border-accent-success focus:outline-none"
                                    disabled={loading}
                                    autoFocus={index === 0}
                                />
                            ))}
                        </div>

                        <button
                            type="button"
                            onClick={verifyOtp}
                            disabled={loading || otp.join('').length !== 6}
                            className="w-full flex items-center justify-center gap-2 bg-accent-success text-bg-base font-bold py-3 rounded-lg hover:bg-accent-success/90 disabled:opacity-50 disabled:cursor-not-allowed shadow-glow-success transition-all"
                        >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Verificar'}
                        </button>

                        {error && (
                            <div className="flex items-center justify-center gap-2 text-accent-danger text-xs animate-in fade-in slide-in-from-top-1">
                                <AlertCircle className="w-3 h-3" />
                                <span>{error}</span>
                            </div>
                        )}

                        <div className="flex items-center justify-end">
                            <button
                                type="button"
                                onClick={() => {
                                    setStep('PHONE');
                                    setError(null);
                                    setOtp(['', '', '', '', '', '']);
                                }}
                                className="flex items-center gap-1 text-xs text-text-muted hover:text-text-primary transition-colors"
                            >
                                <ArrowLeft className="w-3 h-3" /> Cambiar número
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Step 3: Success */}
            {step === 'SUCCESS' && (
                <div className="flex flex-col items-center justify-center py-8 space-y-6 animate-in zoom-in duration-300">
                    <div className="w-20 h-20 bg-accent-success rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.4)]">
                        <Check className="w-10 h-10 text-white stroke-[3]" />
                    </div>
                    <p className="text-text-muted text-center animate-pulse">Redirigiendo a tus archivos...</p>
                </div>
            )}
        </div>
    </div>
  );
};

export default LoginPage;