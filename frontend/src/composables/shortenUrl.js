import { ref } from 'vue'

import { BackendError } from '@/errors'
import { isUsingJsonServer, disableCaching } from '@/flags'

const configureOptions = (targetUrl) => {
  let method = null
  let headers = null
  let body = null

  switch (isUsingJsonServer()) {
    case true:
      method = 'GET'
      // prettier-ignore
      headers = disableCaching() ? {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
      } : {}
      break
    case false:
      method = 'POST'
      headers = {
        'Content-Type': 'application/json',
      }
      body = JSON.stringify({ targetUrl })
      break
    default:
      throw new Error('Invalid configuration (isUsingJsonServer() returned non-boolean value)')
  }
  return { method, headers, body }
}

const shorten = (host, endpoint = '/v1/shorten') => {
  const shortUrl = ref(null)
  const message = ref(null)
  const errorCode = ref(null)
  const details = ref(null)

  const load = async (targetUrl) => {
    try {
      const { method, headers, body } = configureOptions(targetUrl)
      const url = `${host}${endpoint}`
      const response = await fetch(url, { method, headers, body })
      const data = await response.json()

      if (!response.ok) {
        throw new BackendError(
          response.status,
          data.message || 'Unknown error occurred',
          data.errorCode || 'UNKNOWN_ERROR',
        )
      }
      message.value = data.message
      shortUrl.value = data.shortUrl
      details.value = {
        targetUrl: data.targetUrl,
        shortcode: data.shortcode,
        remainingQuota: data.remainingQuota,
      }
    } catch (error) {
      if (error instanceof BackendError) {
        errorCode.value = error.errorCode
        message.value = error.message
      }
      throw error
    }
  }

  return { shortUrl, message, errorCode, details, load }
}

export default shorten
