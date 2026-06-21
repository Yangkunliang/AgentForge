import request from '@/api/request'
import type { WebSearchResponse } from '@/types'

export const webSearchApi = {
  search: (query: string, maxResults = 5) =>
    request.post<WebSearchResponse>('/tools/web-search', { query, max_results: maxResults }),

  suggest: (prefix: string) =>
    request.get<{ prefix: string; suggestions: string[] }>('/tools/web-search/suggest', {
      params: { prefix },
    }),
}
