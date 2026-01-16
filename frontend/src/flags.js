import config from '@/config'

export function isUsingJsonServer() {
  return config.flags.isUsingJsonServer
}

export function disableCaching() {
  return config.flags.disableCaching
}
