/**
 * 工具函数
 */

/**
 * 格式化日期
 */
function formatDate(date, fmt = 'YYYY-MM-DD HH:mm') {
  if (!date) return ''
  if (typeof date === 'string') date = new Date(date)

  const map = {
    'YYYY': date.getFullYear(),
    'MM': String(date.getMonth() + 1).padStart(2, '0'),
    'DD': String(date.getDate()).padStart(2, '0'),
    'HH': String(date.getHours()).padStart(2, '0'),
    'mm': String(date.getMinutes()).padStart(2, '0'),
    'ss': String(date.getSeconds()).padStart(2, '0')
  }

  let result = fmt
  for (const key in map) {
    result = result.replace(key, map[key])
  }
  return result
}

/**
 * 相对时间 (多久前)
 */
function timeAgo(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now - date) / 1000) // seconds

  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`
  return formatDate(date, 'MM-DD')
}

/**
 * 数字格式化 (如 12345 -> 1.2万)
 */
function formatNumber(num) {
  if (!num) return '0'
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
  return String(num)
}

/**
 * 节流
 */
function throttle(fn, delay = 300) {
  let timer = null
  let lastTime = 0
  return function (...args) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      lastTime = now
      fn.apply(this, args)
    }
  }
}

/**
 * 防抖
 */
function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

module.exports = {
  formatDate,
  timeAgo,
  formatNumber,
  throttle,
  debounce
}
