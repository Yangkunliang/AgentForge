<script setup lang="ts">
import { ref } from 'vue'
import { webSearchApi } from '@/api/modules/webSearch'
import type { WebSearchResult } from '@/types'

const searchQuery = ref('')
const searchResults = ref<WebSearchResult[]>([])
const loading = ref(false)
const error = ref('')

async function search() {
  if (!searchQuery.value.trim()) return
  loading.value = true
  error.value = ''
  searchResults.value = []
  try {
    const res = await webSearchApi.search(searchQuery.value)
    searchResults.value = res.results
  } catch (e: any) {
    error.value = e.response?.data?.detail || '搜索失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="web-search-widget">
    <div class="web-search-header">
      <h3>🌐 网络搜索</h3>
    </div>

    <div class="web-search-input">
      <input
        v-model="searchQuery"
        placeholder="输入搜索关键词..."
        @keyup.enter="search"
      />
      <button @click="search" :disabled="loading">
        {{ loading ? '搜索中...' : '搜索' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="searchResults.length" class="results">
      <div v-for="item in searchResults" :key="item.url" class="result-item">
        <a :href="item.url" target="_blank" class="result-link">{{ item.title }}</a>
        <p class="result-snippet">{{ item.snippet }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.web-search-widget {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  background: #f9f9f9;
}

.web-search-header {
  margin-bottom: 12px;
}

.web-search-input {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;

  input {
    flex: 1;
    padding: 8px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
  }

  button {
    padding: 8px 16px;
    background: #6366f1;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;

    &:disabled {
      background: #c7d2fe;
    }
  }
}

.results {
  .result-item {
    margin-bottom: 12px;

    .result-link {
      color: #4f46e5;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }

    .result-snippet {
      color: #6b7280;
      font-size: 13px;
      margin: 4px 0 0;
    }
  }
}

.error {
  color: #ef4444;
  margin-top: 8px;
}
</style>
