import * as R from 'ramda'
import { logger } from '../../logger/winstonLogger'

const colors = require('colors')
const cookie = require('cookie')

export const replaceUndefinedHeadersValue = (headers: Object) =>
  JSON.parse(JSON.stringify(headers))

// Configuration stubs - these functions are simplified for standalone use
export const getSiteIdFromSite = (site: string): number => 1 // Simplified

export const getCookieCSRF = (reqCookie: string) => {
  try {
    return cookie.parse(reqCookie).__csrf
  } catch (e) {
    return ''
  }
}

export const getCSRF = R.curry((skipCSRF: boolean, headers: any) =>
  skipCSRF
    ? R.compose(getCookieCSRF, R.propOr('', 'cookie'))(headers)
    : R.prop('x-csrf', headers)
)

export const getServiceHost = (service: string, headers?: any) => {
  // Get service host from environment variables
  const serviceKey = `${service}_SERVICE_HOST`
  return process.env[serviceKey] || process.env.DEFAULT_SERVICE_HOST || ''
}

export const overrideRequestHeaders = R.useWith(R.merge, [
  R.applySpec({
    Authorization: R.propOr('', 'authorization'),
    'x-cloudfront-viewer-country': R.prop('cloudfront-viewer-country'),
    device: R.propOr('pwa', 'device'),
    'x-csrf': getCSRF(false), // skipCSRF = false
  }),
  R.applySpec({
    siteId: R.compose(getSiteIdFromSite, R.prop('site')),
  }),
])

export const getFinalHeaders = R.compose(
  R.omit([
    'content-length',
    'accept-encoding',
    'host',
    'connection',
    'cloudfront-is-desktop-viewer',
    'cloudfront-is-mobile-viewer',
    'cloudfront-is-smarttv-viewer',
    'cloudfront-is-tablet-viewer',
    'cloudfront-viewer-country',
    'pragma',
    'via',
    'permissiontoken',
  ]),
  R.merge
) as any

type CurlRequest = {
  url: string
  method:
    | 'GET'
    | 'get'
    | 'POST'
    | 'post'
    | 'PUT'
    | 'put'
    | 'PATCH'
    | 'patch'
    | 'DELETE'
    | 'delete'
  headers?: any
  body?: any
}

type StringMap = {[key: string]: string}

const slash = ' \\'
const newLine = '\n'

const getCurlMethod = function(method?: string): string {
  let result: string = ''
  if (method) {
    const types: StringMap = {
      GET: '-X GET',
      POST: '-X POST',
      PUT: '-X PUT',
      PATCH: '-X PATCH',
      DELETE: '-X DELETE',
    }
    result = ` ${types[method.toUpperCase()]}`
  }
  return slash + newLine + result
}

const getCurlHeaders = function(headers?: StringMap): string {
  let result = ''
  if (headers) {
    Object.keys(headers).map((val) => {
      result += `${slash}${newLine}-H "${val}: ${String(headers[val]).replace(
        /(\\|")/g,
        '\\$1'
      )}"`
    })
  }
  return result
}

const getCurlBody = function(body?: Object): string {
  let result = ''
  if (body) {
    result += `${slash}${newLine}-d "${JSON.stringify(body).replace(
      /(\\|")/g,
      '\\$1'
    )}"`
  }
  return result
}

const CurlGenerator = function(params: CurlRequest): string {
  let curlSnippet = 'curl '
  curlSnippet += colors.blue(`"${params.url}"`)
  curlSnippet += getCurlMethod(params.method)
  curlSnippet += getCurlHeaders(params.headers)
  curlSnippet += getCurlBody(params.body)
  return curlSnippet.trim()
}

export const curlLogger = (curlParams: CurlRequest) => {
  if (
    process.env.NODE_ENV !== 'dev-local' ||
    process.env.CURL_LOGGING !== 'true'
  ) {
    return
  }

  const finalHeaders = curlParams.headers
  for (let key in replaceUndefinedHeadersValue(finalHeaders)) {
    finalHeaders[key] = finalHeaders[key].toString()
  }

  logger.info(
    '\n\n' +
      CurlGenerator({
        url: curlParams.url,
        body: curlParams.body,
        headers: replaceUndefinedHeadersValue(finalHeaders),
        method: curlParams.method,
      }) +
      '\n\n'
  )
}

// Additional utility functions that might be used
export const getConvertedDate = (datestring: string) => {
  if (!datestring || datestring === '0000-00-00') return null
  return new Date(datestring)
}

export const parseNumberOrUndefined = (a: any) => {
  const parsed = +a
  return isNaN(parsed) || a === null ? undefined : parsed
}

