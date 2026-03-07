import { useState, useEffect, useRef } from 'react';

/** 数字递增动画 Hook */
export function useCountUp(target: number, duration = 1200): number {
    const [value, setValue] = useState(0);
    const raf = useRef<number>(0);

    useEffect(() => {
        if (target === 0) {
            raf.current = requestAnimationFrame(() => setValue(0));
            return () => cancelAnimationFrame(raf.current);
        }
        const start = performance.now();
        const step = (now: number) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            setValue(Math.round(eased * target));
            if (progress < 1) raf.current = requestAnimationFrame(step);
        };
        raf.current = requestAnimationFrame(step);
        return () => cancelAnimationFrame(raf.current);
    }, [target, duration]);

    return value;
}
