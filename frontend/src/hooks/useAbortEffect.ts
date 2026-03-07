import { useEffect } from 'react';

/**
 * 自动创建并管理 AbortController 的 useEffect wrapper。
 * 组件卸载或依赖变化时自动取消未完成的请求。
 *
 * @example
 * useAbortEffect((signal) => {
 *     dataService.getCurrent(signal).then(setData);
 * }, []);
 */
export function useAbortEffect(
    effect: (signal: AbortSignal) => void | (() => void),
    deps: React.DependencyList
) {
    useEffect(() => {
        const controller = new AbortController();
        const cleanup = effect(controller.signal);
        return () => {
            controller.abort();
            cleanup?.();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);
}
