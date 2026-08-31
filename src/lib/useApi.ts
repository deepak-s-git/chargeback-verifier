/**
 * `useApi` — a minimal async-data hook with the three states every real fetch
 * has and the mock UI never had: loading, error, and empty. It cancels stale
 * results when the dependency key changes (so switching cases fast never paints
 * the previous case's data) and exposes `reload()` for retry / post-mutation
 * refresh. Errors arrive already reduced to a message by `api.ts`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from './api';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** Re-run the fetcher (e.g. retry after an error, or refresh after a mutation). */
  reload: () => void;
}

/**
 * @param fetcher  Produces the promise to await. Kept in a ref so it need not be
 *                 referentially stable between renders.
 * @param depKey   A primitive that identifies the request (typically the caseId).
 *                 Changing it triggers a fresh fetch and cancels the previous.
 * @param enabled  When false, no request is made (used for lazily-loaded tabs).
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  depKey: string | number,
  enabled = true,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcherRef
      .current()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : 'Something went wrong.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [depKey, enabled, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return { data, loading, error, reload };
}
