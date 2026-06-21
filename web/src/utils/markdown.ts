/**
 * Markdown 渲染工具
 * 使用 marked + highlight.js 做完整渲染，DOMPurify 做 XSS 过滤
 */
import { marked, type Renderer } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'

// ── 配置 marked ──────────────────────────────────────────────

const renderer: Partial<Renderer> = {
  // 代码块：注入语言标签 + 复制按钮占位（由组件事件处理）
  code({ text, lang }) {
    const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
    const highlighted = hljs.highlight(text, { language }).value
    return `
<div class="code-block" data-lang="${language}">
  <div class="code-block__header">
    <span class="code-block__lang">${language}</span>
    <button class="code-block__copy" data-code="${encodeURIComponent(text)}">复制</button>
  </div>
  <pre><code class="hljs language-${language}">${highlighted}</code></pre>
</div>`
  },

  // 行内代码
  codespan({ text }) {
    return `<code class="inline-code">${text}</code>`
  },

  // 图片：加懒加载 + 点击放大标记
  image({ href, title, text }) {
    const titleAttr = title ? ` title="${title}"` : ''
    return `<img src="${href}" alt="${text}"${titleAttr} class="chat-image" loading="lazy" data-zoomable />`
  },

  // 链接：新标签打开，防钓鱼
  link({ href, title, text }) {
    const titleAttr = title ? ` title="${title}"` : ''
    return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`
  },
}

marked.use({
  renderer: renderer as Renderer,
  gfm: true,       // GitHub Flavored Markdown（表格、任务列表等）
  breaks: true,    // 单换行转 <br>
})

// ── 思考过程解析 ─────────────────────────────────────────────

export interface ParsedMessage {
  /** 思考过程原始文本（来自 <think>...</think>），可能为空 */
  thinking: string
  /** 主体内容（去掉 think 块后的剩余部分） */
  body: string
}

/**
 * 解析消息，提取 <think>...</think> 思考过程
 * 支持流式（think 块未闭合时也能提取已有内容）
 */
export function parseThinking(raw: string): ParsedMessage {
  const openTag = '<think>'
  const closeTag = '</think>'

  const start = raw.indexOf(openTag)
  if (start === -1) {
    return { thinking: '', body: raw }
  }

  const contentStart = start + openTag.length
  const end = raw.indexOf(closeTag, contentStart)

  if (end === -1) {
    // think 块还未闭合（流式中）
    return {
      thinking: raw.slice(contentStart),
      body: raw.slice(0, start),
    }
  }

  return {
    thinking: raw.slice(contentStart, end).trim(),
    body: (raw.slice(0, start) + raw.slice(end + closeTag.length)).trim(),
  }
}

// ── 渲染入口 ─────────────────────────────────────────────────

/**
 * 将 markdown 字符串渲染为安全 HTML
 */
export function renderMarkdown(md: string): string {
  const html = marked.parse(md) as string
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ['data-lang', 'data-code', 'data-zoomable', 'loading', 'target', 'rel'],
    ADD_TAGS: ['button'],
  })
}
