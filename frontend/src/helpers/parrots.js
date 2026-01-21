import loadingMessagesRaw from '@/assets/loadingmessages.txt?raw'

const parrotModules = import.meta.glob('@/assets/gifs/parrots/**/*.{gif,webp,png}', {
  eager: true,
  import: 'default',
})

const parrotList = Object.values(parrotModules)

export const pickParrot = () => {
  if (!parrotList.length) {
    return ''
  }
  const index = Math.floor(Math.random() * parrotList.length)
  return parrotList[index]
}

export const pickLoadingMessage = () => {
  const messages = loadingMessagesRaw
    .split('\n')
    .map((message) => message.trim())
    .filter(Boolean)
  if (!messages.length) {
    return 'Partying'
  }
  const index = Math.floor(Math.random() * messages.length)
  return messages[index]
}
