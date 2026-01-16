export const escapeHtml = (text = '') =>
  text.replace(/[&<>"']/g, (char) => {
    const escapeMap = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }
    return escapeMap[char] || char
  })

export const formatMessage = (text = '') => {
  const urlRegex = /(https?:\/\/[^\s]+)/g
  return escapeHtml(text).replace(
    urlRegex,
    '<a class="message-url" href="$1" target="_blank" rel="noopener noreferrer">$1</a>',
  )
}
