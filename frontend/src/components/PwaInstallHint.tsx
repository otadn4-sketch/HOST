import { useEffect, useState } from 'react';
import { Smartphone, X } from 'lucide-react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

function isStandalone() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone)
  );
}

export function PwaInstallHint() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [iosHint, setIosHint] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    if (sessionStorage.getItem('eytan-pwa-dismiss') === '1') return;

    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const mobile = /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);

    const onPrompt = (event: Event) => {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
      setVisible(true);
    };
    window.addEventListener('beforeinstallprompt', onPrompt);

    if (ios) {
      setIosHint(true);
      setVisible(true);
    } else if (mobile) {
      setVisible(true);
    }

    return () => window.removeEventListener('beforeinstallprompt', onPrompt);
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    sessionStorage.setItem('eytan-pwa-dismiss', '1');
    setVisible(false);
  };

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setVisible(false);
  };

  return (
    <div className="fixed bottom-4 right-4 left-4 z-40 mx-auto max-w-md rounded-2xl border border-[#E8D9C4] bg-white p-4 shadow-xl sm:right-6 sm:left-auto">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#4A2C17] text-white">
          <Smartphone size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-black text-[#4A2C17]">نصب نسخه اپلیکیشن</p>
          <p className="mt-1 text-[11px] leading-5 text-[#6B5344]">
            {iosHint
              ? 'در Safari از دکمه اشتراک‌گذاری، «Add to Home Screen» / «افزودن به صفحه اصلی» را بزنید تا مثل اپ باز شود.'
              : 'این سامانه را روی صفحه اصلی گوشی نصب کنید تا بدون نوار مرورگر، مثل اپلیکیشن باز شود.'}
          </p>
          <div className="mt-3 flex items-center gap-2">
            {deferred && (
              <button
                type="button"
                onClick={() => void install()}
                className="rounded-lg bg-[#4A2C17] px-3 py-1.5 text-[11px] font-black text-white"
              >
                نصب اپلیکیشن
              </button>
            )}
            <button type="button" onClick={dismiss} className="text-[11px] font-bold text-[#8B5A2B]">
              بعداً
            </button>
          </div>
        </div>
        <button type="button" onClick={dismiss} className="rounded-lg p-1 text-[#6B5344] hover:bg-[#F7F1E8]" aria-label="بستن">
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
