export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch('/api' + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-Tfprep': '1', ...options.headers },
  });
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(response.ok
      ? 'The course server returned an unreadable response. Reload the page and try again.'
      : `The course server could not complete this request (HTTP ${response.status}). Try again; if it continues, check the server logs.`);
  }
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'The request could not be completed. Check the details and try again.');
  return data;
}

export const post = (path: string, data?: any) => api(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) });

export type Question = {
  id: string; domain_id: string; objectives: string[]; type: 'single' | 'multiple' | 'boolean';
  prompt: string; code?: string; choices: Record<string, string>; correct?: string[]; rationale?: Record<string, string>;
};

export type Exercise = {
  id: string; title: string; description: string;
  cases?: { prompt: string; choices: string[]; correct: string; explanation: string }[];
};

export type Domain = {
  id: string; title: string; subtitle: string; minutes: number; lab_minutes: number;
  objectives: string[]; lab_id: string; difficulty: string; delta: { before: string; after: string };
  exercises: Exercise[]; checkpoints: Question[]; challenge: string;
  cost: { target_usd: number; assumptions: string; free_tier_guaranteed: boolean };
};
