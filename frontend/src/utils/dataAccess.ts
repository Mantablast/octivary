export const normalize = (value: unknown) => {
  if (value === null || value === undefined) return '';
  return String(value).trim().toLowerCase();
};

export const resolvePath = (data: any, path?: string) => {
  if (!path) return undefined;
  return path.split('.').reduce((acc, segment) => {
    if (acc === null || acc === undefined) return undefined;
    if (Array.isArray(acc)) {
      const match = /(.+)\[(\d+)\]$/.exec(segment);
      if (match) {
        const idx = Number(match[2]);
        const key = match[1];
        const collection = acc.map((entry) => entry?.[key]);
        return collection[idx];
      }
      return undefined;
    }
    if (typeof acc === 'object') {
      const match = /(.+)\[(\d+)\]$/.exec(segment);
      if (match) {
        const key = match[1];
        const index = Number(match[2]);
        const value = acc?.[key];
        return Array.isArray(value) ? value[index] : undefined;
      }
      return acc?.[segment];
    }
    return undefined;
  }, data);
};
