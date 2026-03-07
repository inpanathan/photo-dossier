import { useCallback, useEffect, useRef, useState } from 'react';
import { getJob, type Job } from '../api/client';

/** Poll a job until it reaches a terminal state. */
export function useJobPoller(jobId: string | null, intervalMs = 1000) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number>();

  const poll = useCallback(async () => {
    if (!jobId) return;
    try {
      const j = await getJob(jobId);
      setJob(j);
      if (['completed', 'failed', 'cancelled'].includes(j.status)) {
        clearInterval(timerRef.current);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to poll job');
      clearInterval(timerRef.current);
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    poll();
    timerRef.current = window.setInterval(poll, intervalMs);
    return () => clearInterval(timerRef.current);
  }, [jobId, intervalMs, poll]);

  return { job, error };
}
