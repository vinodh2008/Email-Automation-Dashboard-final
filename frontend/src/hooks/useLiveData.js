import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useGlobalRefresh } from '../context/RefreshContext';

export const useLiveData = (fetchFn, pollingInterval = null, dependencies = [], enabled = true) => {
  const refreshContext = useGlobalRefresh();
  const globalRefreshKey = refreshContext ? refreshContext.refreshKey : 0;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isPolling, setIsPolling] = useState(false);

  const depsKey = useMemo(() => JSON.stringify(dependencies), [dependencies]);

  const fetchData = useCallback(async (isSilentPoll = false) => {
    if (!isSilentPoll) {
      setLoading(true);
    }
    setIsPolling(isSilentPoll);

    try {
      const fetchStartTime = Date.now();
      const result = await fetchFn();

      setData(prev => {
        if (!isSilentPoll || !prev) return result;

        const mergeArray = (prevArr, newArr) => {
          return newArr.map(newItem => {
            const prevItem = prevArr.find(p => p.id === newItem.id || p.task_id === newItem.task_id);
            if (prevItem && prevItem._lastLocalMutation && prevItem._lastLocalMutation > fetchStartTime) {
              return prevItem;
            }
            return newItem;
          });
        };

        if (Array.isArray(result) && Array.isArray(prev)) return mergeArray(prev, result);
        if (result?.data && Array.isArray(result.data) && prev?.data) {
          return { ...result, data: mergeArray(prev.data, result.data) };
        }
        return result;
      });

      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      if (!isSilentPoll) {
        // Never expose raw errors to the user — show friendly messages only
        const status = err?.response?.status;
        if (status === 404) {
          setError('This feature is not available yet.');
        } else if (status === 401 || status === 403) {
          setError('You do not have permission to view this data.');
        } else if (status >= 500) {
          setError('Something went wrong. Please try again later.');
        } else if (!err?.response) {
          setError('Unable to connect to the server. Please check your connection.');
        } else {
          setError('Unable to load data. Please try again.');
        }
      } else {
        // Silent poll errors should not crash or show UI errors
        console.error('[useLiveData] Poll error:', err?.message || err);
      }
    } finally {
      setLoading(false);
      setIsPolling(false);
    }
  }, [fetchFn]);

  useEffect(() => {
    let mounted = true;
    let pollTimer;
    let currentInterval = pollingInterval;
    let consecutiveErrors = 0;

    const executePoll = async () => {
      if (!mounted) return;
      try {
        await fetchData(true);
        consecutiveErrors = 0;
        if (currentInterval !== pollingInterval && pollingInterval) {
           currentInterval = pollingInterval;
           clearInterval(pollTimer);
           pollTimer = setInterval(executePoll, currentInterval);
        }
      } catch (err) {
        const status = err?.response?.status;
        consecutiveErrors++;

        if (status === 404) {
          currentInterval = 60000;
          clearInterval(pollTimer);
          pollTimer = setInterval(executePoll, currentInterval);
        } else if (consecutiveErrors > 3) {
           currentInterval = Math.min((currentInterval || 5000) * 2, 60000);
           clearInterval(pollTimer);
           pollTimer = setInterval(executePoll, currentInterval);
        }
      }
    };

    const initialFetch = async () => {
      try {
        await fetchData(false);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 404) {
          currentInterval = 60000;
        }
      }

      if (mounted && currentInterval) {
        pollTimer = setInterval(executePoll, currentInterval);
      }
    };

    if (!enabled) {
      setLoading(false);
      setData(null);
      setError(null);
      return () => { mounted = false; };
    }

    initialFetch();

    let eventSource;
    try {
      const token = localStorage.getItem('token');
      const sseUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/events/stream${token ? `?token=${token}` : ''}`;
      eventSource = new EventSource(sseUrl);

      eventSource.addEventListener('sync_completed', () => {
        if (mounted) {
          fetchData(true).catch(() => {});
        }
      });
    } catch (e) {
      console.warn('[useLiveData] SSE connection fallback:', e);
    }

    return () => {
      mounted = false;
      if (pollTimer) clearInterval(pollTimer);
      if (eventSource) eventSource.close();
    };
  }, [depsKey, fetchData, pollingInterval, globalRefreshKey, enabled]);

  const refresh = () => fetchData(false).catch(() => {});

  const updateItem = useCallback((idField, idValue, updatedFields) => {
    setData(prev => {
      const updateArray = (arr) => arr.map(item =>
        item[idField] === idValue ? { ...item, ...updatedFields, _lastLocalMutation: Date.now() } : item
      );

      if (Array.isArray(prev)) return updateArray(prev);
      if (prev?.data && Array.isArray(prev.data)) return { ...prev, data: updateArray(prev.data) };
      return prev;
    });
  }, []);

  const removeItem = useCallback((idField, idValue) => {
    setData(prev => {
      const filterArray = (arr) => arr.filter(item => item[idField] !== idValue);
      if (Array.isArray(prev)) return filterArray(prev);
      if (prev?.data && Array.isArray(prev.data)) return { ...prev, data: filterArray(prev.data), total: (prev.total || 1) - 1 };
      return prev;
    });
  }, []);

  const addItem = useCallback((newItem) => {
    setData(prev => {
      const itemWithMeta = { ...newItem, _lastLocalMutation: Date.now() };
      if (Array.isArray(prev)) return [itemWithMeta, ...prev];
      if (prev?.data && Array.isArray(prev.data)) return { ...prev, data: [itemWithMeta, ...prev.data], total: (prev.total || 0) + 1 };
      return prev;
    });
  }, []);

  return { data, loading: enabled ? loading : false, error, lastUpdated, refresh, isPolling, updateItem, removeItem, addItem };
};
