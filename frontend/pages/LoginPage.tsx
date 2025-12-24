import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Check, ArrowRight, ArrowLeft, Sun, Moon, AlertCircle } from 'lucide-react';
import { toggleTheme } from '../services/themeStore';
import { useTheme } from '../services/useTheme';
import { otpApi } from '../services/api';

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
    console.log('🔍 AUTH_MOCK:', AUTH_MOCK, 'rawAuthMock:', rawAuthMock, 'DEV:', (import.meta as any).env?.DEV);
  const [step, setStep] = useState<LoginStep>('PHONE');
  const [phoneNumber, setPhoneNumber] = useState('');
    const [userId, setUserId] = useState<string>('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
    const [debugOtp, setDebugOtp] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(60);
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

  // Timer Logic
  useEffect(() => {
    let timer: any;
    if (step === 'OTP' && countdown > 0) {
      timer = setInterval(() => setCountdown((prev) => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [step, countdown]);

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
        const derivedUserId = `+52${phoneNumber}`;
        setUserId(derivedUserId);

        // Generar código para mostrar en pantalla
        const res = await otpApi.request(derivedUserId, derivedUserId);
        
        if (!res?.ok) {
            setError(res?.error || 'No se pudo generar el código.');
            setLoading(false);
            return;
        }

        // Mostrar código en pantalla
        const code = (res as any)?.verifyCode;
        if (code) {
            setDebugOtp(code);
        }

        setStep('OTP');
        setCountdown(300); // 5 minutos
        
        // Iniciar polling para verificar si usuario envió código por WhatsApp
        const pollInterval = setInterval(async () => {
            const statusRes = await otpApi.checkVerified(derivedUserId, code);
            if (statusRes?.verified) {
                clearInterval(pollInterval);
                // Auto-autenticar
                if (statusRes.sessionToken) {
                    localStorage.setItem('verity_token', statusRes.sessionToken);
                    setStep('SUCCESS');
                    setTimeout(() => navigate('/files', { replace: true }), 800);
                }
            }
        }, 2000); // Poll cada 2 segundos

        // Limpiar polling después de 5 minutos
        setTimeout(() => clearInterval(pollInterval), 300000);
        
    } catch (err: any) {
        setError(err?.message || 'No se pudo generar el código.');
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
            const res = await otpApi.validate(userId, code);
            if (res?.ok && res.sessionToken) {
                localStorage.setItem('verity_token', res.sessionToken);
                setStep('SUCCESS');
                setTimeout(() => {
                    navigate('/files', { replace: true });
                }, 800);
                return;
            }

            const errCode = res?.error;
            if (errCode === 'OTP_EXPIRED') {
                setError('El código expiró. Solicita uno nuevo.');
            } else if (errCode === 'OTP_LOCKED') {
                setError('Demasiados intentos. Intenta más tarde.');
            } else {
                setError('Código incorrecto. Intenta de nuevo.');
            }
            setOtp(['', '', '', '', '', '']);
            otpInputRefs.current[0]?.focus();
        } catch (err: any) {
            setError(err?.message || 'No se pudo validar el código.');
        } finally {
            setLoading(false);
        }
  };

  // OTP Input Handlers
  const handleOtpChange = (index: number, value: string) => {
    if (isNaN(Number(value))) return;
    
    const newOtp = [...otp];
    newOtp[index] = value.substring(value.length - 1); // Take last char
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
    const pastedData = e.clipboardData.getData('text').slice(0, 6).split('');
    if (pastedData.every(char => !isNaN(Number(char)))) {
        const newOtp = [...otp];
        pastedData.forEach((char, i) => {
            if (i < 6) newOtp[i] = char;
        });
        setOtp(newOtp);
        // Focus the next empty input or the last one
        const nextIndex = Math.min(pastedData.length, 5);
        otpInputRefs.current[nextIndex]?.focus();
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
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
                        <h1 className="text-xl font-bold text-text-primary">Envía este código</h1>
                        <p className="text-sm text-text-muted">Por WhatsApp a <span className="font-semibold">Shadowcat</span></p>
                    </div>

                    <div className="space-y-4">
                        {/* Código para enviar */}
                        {debugOtp && (
                            <div className="bg-bg-elevated border-2 border-accent-success rounded-xl p-6 text-center space-y-3">
                                <p className="text-xs text-text-muted uppercase tracking-wider font-semibold">Tu código de verificación</p>
                                <div className="font-mono text-4xl font-bold text-accent-success tracking-widest">
                                    {debugOtp}
                                </div>
                                <button
                                    onClick={() => {
                                        const waNumber = '5215662837947';
                                        const waLink = `https://wa.me/${waNumber}?text=${debugOtp}`;
                                        window.open(waLink, '_blank');
                                    }}
                                    className="w-full bg-[#25D366] text-white font-semibold py-3 rounded-lg hover:bg-[#1fb854] transition-all flex items-center justify-center gap-2"
                                >
                                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.890-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>
                                    Abrir WhatsApp
                                </button>
                                <p className="text-xs text-text-muted">Copia el código y envíalo, o usa el botón</p>
                            </div>
                        )}

                        <div className="text-center">
                            <p className="text-sm text-text-muted mb-2">Esperando verificación...</p>
                            <div className="flex justify-center">
                                <Loader2 className="w-6 h-6 animate-spin text-accent-success" />
                            </div>
                        </div>

                        {error && (
                            <div className="flex items-center justify-center gap-2 text-accent-danger text-xs animate-in fade-in slide-in-from-top-1">
                                <AlertCircle className="w-3 h-3" />
                                <span>{error}</span>
                            </div>
                        )}
                    </div>

                    <div className="text-center text-xs text-text-muted mt-4">
                        <button onClick={() => setStep('PHONE')} className="underline hover:text-text-primary">
                            ← Cambiar número
                        </button>
                    </div>
                </div>
            )}
                            <span className="text-xs text-text-muted">Reenviar en <span className="font-mono text-text-secondary">{formatTime(countdown)}</span></span>
                        ) : (
                            <button 
                                onClick={() => {
                                        setCountdown(60);
                                        if (!loading) {
                                            setError(null);
                                            if (AUTH_MOCK) {
                                                const mock = '123456';
                                                setDebugOtp(mock);
                                                setOtp(mock.split(''));
                                            } else {
                                                otpApi.request(userId, userId).catch(() => {
                                                    setError('No se pudo reenviar el código.');
                                                });
                                            }
                                        }
                                }}
                                className="text-xs font-medium text-accent-info hover:underline"
                            >
                                Reenviar código
                            </button>
                        )}

                        <button 
                            onClick={() => {
                                setStep('PHONE');
                                setError(null);
                                setLoading(false);
                            }}
                            className="flex items-center gap-1 text-xs text-text-muted hover:text-text-primary transition-colors"
                        >
                            <ArrowLeft className="w-3 h-3" /> Cambiar número
                        </button>
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