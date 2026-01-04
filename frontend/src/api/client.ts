export async function fetchJson<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const base = import.meta.env.VITE_API_BASE || '';
  const response = await fetch(`${base}${path}`, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
