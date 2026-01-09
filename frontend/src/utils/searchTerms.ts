export const SEARCH_TERM_ITEM_PREFIX = 'search_term_item:';
export const TEXT_SEARCH_HUB_KEY = '__text_search__';

export const buildSearchTermItemKey = (baseKey: string, term: string) =>
  `${SEARCH_TERM_ITEM_PREFIX}${baseKey}:${encodeURIComponent(term)}`;

export const parseSearchTermItemKey = (key: string) => {
  if (!key.startsWith(SEARCH_TERM_ITEM_PREFIX)) return null;
  const rest = key.slice(SEARCH_TERM_ITEM_PREFIX.length);
  const separatorIndex = rest.indexOf(':');
  if (separatorIndex < 0) return null;
  const baseKey = rest.slice(0, separatorIndex);
  const term = decodeURIComponent(rest.slice(separatorIndex + 1));
  return { baseKey, term };
};
