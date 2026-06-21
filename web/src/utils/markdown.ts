/**
 * Markdown 渲染工具
 * 使用 marked + highlight.js 做完整渲染，DOMPurify 做 XSS 过滤
 */
import { marked, type Renderer } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'

// ── 配置 marked ──────────────────────────────────────────────

function unescapeHtml(str: string): string {
  return str
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
}

const renderer: Partial<Renderer> = {
  // marked v12+ uses positional args: code(code: string, infostring: string, escaped: boolean)
  code(code, infostring, escaped) {
    const rawText = (escaped ? unescapeHtml(code) : code) ?? ''
    const lang = infostring?.trim() || ''
    const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
    const highlighted = hljs.highlight(rawText, { language }).value

    console.log('[code renderer] lang:', lang, '| rawText length:', rawText.length)
    console.log('[code renderer] rawText[:100]:', rawText.slice(0, 100))
    console.log('[code renderer] highlighted[:100]:', highlighted.slice(0, 100))

    return `
<div class="code-block" data-lang="${language}">
  <div class="code-block__header">
    <span class="code-block__lang">${language}</span>
    <button class="code-block__copy" data-code="${encodeURIComponent(rawText)}">复制</button>
  </div>
  <pre><code class="hljs language-${language}">${highlighted}</code></pre>
</div>`
  },

  codespan(text) {
    return `<code class="inline-code">${text ?? ''}</code>`
  },

  image(href, title, text) {
    if (!href) return text ?? ''
    const titleAttr = title ? ` title="${title}"` : ''
    return `<img src="${href}" alt="${text ?? ''}"${titleAttr} class="chat-image" loading="lazy" data-zoomable />`
  },

  link(href, title, text) {
    if (!href) return text ?? ''
    const titleAttr = title ? ` title="${title}"` : ''
    return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer">${text ?? ''}</a>`
  },
}

marked.use({
  renderer: renderer as Renderer,
  gfm: true,
  breaks: true,
})

// ── 思考过程解析 ─────────────────────────────────────────────

export interface ParsedMessage {
  thinking: string
  body: string
}

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

export function renderMarkdown(md: string): string {
  const html = marked.parse(md) as string

  console.log('[renderMarkdown] marked output (code block section):',
    html.slice(html.indexOf('<div class="code-block"'), html.indexOf('<div class="code-block"') + 300))

  const sanitized = DOMPurify.sanitize(html, {
    ADD_TAGS: ['button', 'span', 'pre', 'code'],
    ADD_ATTR: ['data-lang', 'data-code', 'data-zoomable', 'loading', 'target', 'rel', 'class'],
  })

  console.log('[renderMarkdown] after DOMPurify (code block section):',
    sanitized.slice(sanitized.indexOf('<div class="code-block"'), sanitized.indexOf('<div class="code-block"') + 300))

  return sanitized
}
