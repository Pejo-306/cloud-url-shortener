import { ref } from 'vue'

import config from '@/config'
import { BackendError } from '@/errors'
import { isUsingJsonServer, disableCaching } from '@/flags'
import { getSession } from '@/helpers/auth'

const configureOptions = (targetUrl, idToken) => {
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
        Authorization: idToken ? `Bearer ${idToken}` : null,
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
    const session = getSession()
    const idToken = session.idToken
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), config.backend.timeout)

    try {
      const { method, headers, body } = configureOptions(targetUrl, idToken)
      const url = `${host}${endpoint}`
      const response = await fetch(url, { method, headers, body, signal: controller.signal })
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
      if (error.name === 'AbortError') {
        errorCode.value = 'TIMEOUT'
        message.value = 'Request timed out'
      } else if (error instanceof BackendError) {
        errorCode.value = error.errorCode
        message.value = error.message
      } else {
        errorCode.value = 'UNKNOWN_ERROR'
        message.value = 'Unknown error occurred'
      }
      throw error
    } finally {
      clearTimeout(timeoutId)
    }
  }

  return { shortUrl, message, errorCode, details, load }
}

export default shorten
