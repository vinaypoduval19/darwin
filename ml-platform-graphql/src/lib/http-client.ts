import axios from 'axios'
import * as R from 'ramda'
import {curlLogger, replaceUndefinedHeadersValue} from './utils'
import {config} from './config'
import { logger } from '../../logger/winstonLogger'

const queryString = require('query-string')

// Hardcoded user for phase 1
export const HARDCODED_USER = {
  id: 1,
  name: 'ML Platform User',
  email: 'mlplatform@example.com',
  role: 'admin',
}

const getServiceHost = (service: string): string => {
  let resolvedHost: string
  let source: string
  
  // First, try to get from config.serviceHosts
  if (config.serviceHosts[service]) {
    resolvedHost = config.serviceHosts[service]
    source = 'config.serviceHosts'
  }
  // Try with environment variables (legacy support)
  else if (process.env[`${service}_SERVICE_HOST`]) {
    resolvedHost = process.env[`${service}_SERVICE_HOST`]!
    source = 'env (with _SERVICE_HOST)'
  }
  // Try directly from environment
  else if (process.env[service]) {
    resolvedHost = process.env[service]!
    source = 'env (direct)'
  }
  // Fall back to default service host
  else {
    resolvedHost = config.DEFAULT_SERVICE_HOST
    source = 'default'
  }
  
  logger.info(`🔍 Service Resolution: "${service}" -> "${resolvedHost}" (from: ${source})`)
  
  return resolvedHost
}

const cleanHeaders = (headers: any) => {
  const cleaned = {...headers}
  
  // Headers that should NOT be forwarded to backend services
  const headersToRemove = [
    'content-length',  // Should be auto-calculated by axios
    'host',            // Should be set by axios based on URL
    'connection',      // Connection management header
    'transfer-encoding', // Transfer encoding header
    'accept-encoding',   // Let axios handle encoding
  ]
  
  Object.keys(cleaned).forEach((key) => {
    const lowerKey = key.toLowerCase()
    // Remove undefined values
    if (cleaned[key] === undefined) {
      delete cleaned[key]
    }
    // Remove problematic headers
    if (headersToRemove.includes(lowerKey)) {
      logger.info(`🗑️  Removing header: ${key} = ${cleaned[key]}`)
      delete cleaned[key]
    }
  })
  
  return cleaned
}

const post = R.curry(
  (request, response, url: string, headers: any, body) => {
    const newBody = JSON.stringify(body)
    const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')
    
    // Add hardcoded user info to headers
    const finalHeaders = {
      ...headers,
      'content-type': 'application/json',
      'msd-user': JSON.stringify(HARDCODED_USER),
      'msd-user-id': HARDCODED_USER.id,
      'msd-user-email': HARDCODED_USER.email,
      'msd-role-id': HARDCODED_USER.role,
    }

    // Clean undefined headers
    const cleanedHeaders = cleanHeaders(finalHeaders)

    logger.info('**** POST Request ****', serviceDomain + url)
    
    curlLogger({
      url: `${serviceDomain}${url}`,
      body: JSON.parse(newBody),
      headers: cleanedHeaders,
      method: 'POST',
    })

    return axios
      .post(`${serviceDomain}${url}`, newBody, {
        headers: replaceUndefinedHeadersValue(cleanedHeaders),
        method: 'POST',
      })
      .then((res: any) => {
        logger.info('✅ POST Response Success', url, 'Status:', res?.status)
        return R.prop('data')(res)
      })
      .catch((error) => {
        // Log full error details for debugging
        logger.error('❌ POST Error Details:', {
          url: `${serviceDomain}${url}`,
          errorMessage: error?.message,
          errorCode: error?.code,
          hasResponse: !!error?.response,
          responseStatus: error?.response?.status,
          responseData: error?.response?.data,
          isAxiosError: error?.isAxiosError,
        })
        
        // Handle different error scenarios
        if (error?.response) {
          // Server responded with error status
          const errorMsg = error.response.data?.error?.message || error.response.data?.message || error.response.data?.error || error.message
          logger.error('POST Error (Response):', url, `Status ${error.response.status}:`, errorMsg)
          throw new Error(`${errorMsg} (Status: ${error.response.status})`)
        } else if (error?.request) {
          // Request was made but no response received
          const errorMsg = error?.message || 'No response from server'
          logger.error('POST Error (No Response):', url, errorMsg)
          throw new Error(errorMsg)
        } else {
          // Something else happened
          const errorMsg = error?.message || 'Unknown error'
          logger.error('POST Error (Setup):', url, errorMsg)
          throw new Error(errorMsg)
        }
      })
  }
)

const get = R.curry(
  (request, response, url: string, headers: any, queryParams: Object) => {
    const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')
    
    const finalHeaders = {
      ...headers,
      'msd-user': JSON.stringify(HARDCODED_USER),
      'msd-user-id': HARDCODED_USER.id,
      'msd-user-email': HARDCODED_USER.email,
      'msd-role-id': HARDCODED_USER.role,
    }

    const cleanedHeaders = cleanHeaders(finalHeaders)

    logger.info('**** GET Request ****', serviceDomain + url)

    curlLogger({
      url: `${serviceDomain}${url}?${queryString.stringify(queryParams)}`,
      headers: cleanedHeaders,
      method: 'GET',
    })

    return axios
      .get(`${serviceDomain}${url}`, {
        headers: replaceUndefinedHeadersValue(cleanedHeaders),
        params: queryParams,
        method: 'GET',
      })
      .then((res: any) => {
        logger.info('✅ GET Response Success', url, 'Status:', res?.status)
        return R.prop('data')(res)
      })
      .catch((error) => {
        // Log full error details for debugging
        logger.error('❌ GET Error Details:', {
          url: `${serviceDomain}${url}`,
          queryParams: queryParams,
          errorMessage: error?.message,
          errorCode: error?.code,
          hasResponse: !!error?.response,
          responseStatus: error?.response?.status,
          responseData: error?.response?.data,
          responseHeaders: error?.response?.headers,
          requestHeaders: cleanedHeaders,
          isAxiosError: error?.isAxiosError,
        })
        
        // Handle different error scenarios
        if (error?.response) {
          // Server responded with error status
          const errorData = error.response.data
          const errorMsg = typeof errorData === 'string' 
            ? errorData 
            : errorData?.message || errorData?.error || JSON.stringify(errorData) || error.message
          logger.error('GET Error (Response):', url, `Status ${error.response.status}:`, errorMsg)
          throw new Error(`${errorMsg} (Status: ${error.response.status})`)
        } else if (error?.request) {
          // Request was made but no response
          logger.error('GET Error (No Response):', url, 'Full error:', error)
          throw new Error(`No response from ${serviceDomain}${url}: ${error.message}`)
        } else {
          // Something else happened
          const errorMsg = error?.message || 'Unknown error'
          logger.error('GET Error (Setup):', url, errorMsg)
          throw new Error(errorMsg)
        }
      })
  }
)

const put = R.curry(
  (request, response, url: string, headers: any, body) => {
    const newBody = JSON.stringify(body)
    const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')

    const finalHeaders = {
      ...headers,
      'content-type': 'application/json',
      'msd-user': JSON.stringify(HARDCODED_USER),
      'msd-user-id': HARDCODED_USER.id,
      'msd-user-email': HARDCODED_USER.email,
      'msd-role-id': HARDCODED_USER.role,
    }

    const cleanedHeaders = cleanHeaders(finalHeaders)

    logger.info('**** PUT Request ****', serviceDomain + url)
    
    curlLogger({
      url: `${serviceDomain}${url}`,
      headers: cleanedHeaders,
      method: 'PUT',
      body: body,
    })

    return axios
      .put(`${serviceDomain}${url}`, newBody, {
        headers: replaceUndefinedHeadersValue(cleanedHeaders),
      })
      .then((res: any) => {
        logger.info('✅ PUT Response Success', url, 'Status:', res?.status)
        return R.prop('data')(res)
      })
      .catch((error) => {
        // Log full error details for debugging
        logger.error('❌ PUT Error Details:', {
          url: `${serviceDomain}${url}`,
          errorMessage: error?.message,
          errorCode: error?.code,
          hasResponse: !!error?.response,
          responseStatus: error?.response?.status,
          responseData: error?.response?.data,
          isAxiosError: error?.isAxiosError,
        })
        
        // Handle different error scenarios
        if (error?.response) {
          // Server responded with error status
          const errorMsg = error.response.data?.message || error.response.data?.error || error.message
          logger.error('PUT Error (Response):', url, `Status ${error.response.status}:`, errorMsg)
          throw new Error(`${errorMsg} (Status: ${error.response.status})`)
        } else if (error?.request) {
          // Request was made but no response
          const errorMsg = error?.message || 'No response from server'
          logger.error('PUT Error (No Response):', url, errorMsg)
          throw new Error(errorMsg)
        } else {
          // Something else happened
          const errorMsg = error?.message || 'Unknown error'
          logger.error('PUT Error (Setup):', url, errorMsg)
          throw new Error(errorMsg)
        }
      })
  }
)

const patch = R.curry(
  (request, response, url: string, headers: any, body) => {
    const newBody = JSON.stringify(body)
    const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')

    const finalHeaders = {
      ...headers,
      'content-type': 'application/json',
      'msd-user': JSON.stringify(HARDCODED_USER),
      'msd-user-id': HARDCODED_USER.id,
      'msd-user-email': HARDCODED_USER.email,
      'msd-role-id': HARDCODED_USER.role,
    }

    const cleanedHeaders = cleanHeaders(finalHeaders)

    curlLogger({
      url: `${serviceDomain}${url}`,
      headers: cleanedHeaders,
      method: 'PATCH',
      body: body,
    })

    logger.info('**** PATCH Request ****', serviceDomain + url)

    return axios
      .patch(`${serviceDomain}${url}`, newBody, {
        headers: replaceUndefinedHeadersValue(cleanedHeaders),
      })
      .then((res: any) => {
        logger.info('✅ PATCH Response Success', url, 'Status:', res?.status)
        return R.prop('data')(res)
      })
      .catch((error) => {
        // Log full error details for debugging
        logger.error('❌ PATCH Error Details:', {
          url: `${serviceDomain}${url}`,
          errorMessage: error?.message,
          errorCode: error?.code,
          hasResponse: !!error?.response,
          responseStatus: error?.response?.status,
          responseData: error?.response?.data,
          isAxiosError: error?.isAxiosError,
        })
        
        // Handle different error scenarios
        if (error?.response) {
          // Server responded with error status
          const errorMsg = error.response.data?.message || error.response.data?.error || error.message
          logger.error('PATCH Error (Response):', url, `Status ${error.response.status}:`, errorMsg)
          throw new Error(`${errorMsg} (Status: ${error.response.status})`)
        } else if (error?.request) {
          // Request was made but no response
          const errorMsg = error?.message || 'No response from server'
          logger.error('PATCH Error (No Response):', url, errorMsg)
          throw new Error(errorMsg)
        } else {
          // Something else happened
          const errorMsg = error?.message || 'Unknown error'
          logger.error('PATCH Error (Setup):', url, errorMsg)
          throw new Error(errorMsg)
        }
      })
  }
)

const deleteReq = R.curry(
  (request, response, url: string, headers: any, queryParams: Object) => {
    const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')

    const finalHeaders = {
      ...headers,
      'msd-user': JSON.stringify(HARDCODED_USER),
      'msd-user-id': HARDCODED_USER.id,
      'msd-user-email': HARDCODED_USER.email,
      'msd-role-id': HARDCODED_USER.role,
    }

    const cleanedHeaders = cleanHeaders(finalHeaders)

    curlLogger({
      url: `${serviceDomain}${url}?${queryString.stringify(queryParams)}`,
      headers: cleanedHeaders,
      method: 'DELETE',
    })

    return axios
      .delete(`${serviceDomain}${url}`, {
        headers: replaceUndefinedHeadersValue(cleanedHeaders),
        params: queryParams,
      })
      .then((res: any) => {
        logger.info('✅ DELETE Response Success', url, 'Status:', res?.status)
        return R.prop('data')(res)
      })
      .catch((error) => {
        // Log full error details for debugging
        logger.error('❌ DELETE Error Details:', {
          url: `${serviceDomain}${url}`,
          errorMessage: error?.message,
          errorCode: error?.code,
          hasResponse: !!error?.response,
          responseStatus: error?.response?.status,
          responseData: error?.response?.data,
          isAxiosError: error?.isAxiosError,
        })
        
        // Handle different error scenarios
        if (error?.response) {
          // Server responded with error status
          const errorMsg = error.response.data?.message || error.response.data?.error || error.message
          logger.error('DELETE Error (Response):', url, `Status ${error.response.status}:`, errorMsg)
          throw new Error(`${errorMsg} (Status: ${error.response.status})`)
        } else if (error?.request) {
          // Request was made but no response
          const errorMsg = error?.message || 'No response from server'
          logger.error('DELETE Error (No Response):', url, errorMsg)
          throw new Error(errorMsg)
        } else {
          // Something else happened
          const errorMsg = error?.message || 'Unknown error'
          logger.error('DELETE Error (Setup):', url, errorMsg)
          throw new Error(errorMsg)
        }
      })
  }
)

const deleteWithBodyReq = R.curry(
  (request, response, url: string, headers: any, body) => {
    const newBody = JSON.stringify(body)
    const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')

    const finalHeaders = {
      ...headers,
      'content-type': 'application/json',
      'msd-user': JSON.stringify(HARDCODED_USER),
      'msd-user-id': HARDCODED_USER.id,
      'msd-user-email': HARDCODED_USER.email,
      'msd-role-id': HARDCODED_USER.role,
    }

    const cleanedHeaders = cleanHeaders(finalHeaders)

    logger.info('**** Delete Request ****', serviceDomain + url)

    curlLogger({
      url: `${serviceDomain}${url}`,
      headers: cleanedHeaders,
      method: 'DELETE',
      body: JSON.parse(newBody),
    })

    return axios
      .delete(`${serviceDomain}${url}`, {
        headers: replaceUndefinedHeadersValue(cleanedHeaders),
        data: newBody,
      })
      .then((res: any) => {
        logger.info('✅ DELETE (with body) Response Success', url, 'Status:', res?.status)
        return R.prop('data')(res)
      })
      .catch((error) => {
        // Log full error details for debugging
        logger.error('❌ DELETE (with body) Error Details:', {
          url: `${serviceDomain}${url}`,
          errorMessage: error?.message,
          errorCode: error?.code,
          hasResponse: !!error?.response,
          responseStatus: error?.response?.status,
          responseData: error?.response?.data,
          isAxiosError: error?.isAxiosError,
        })
        
        // Handle different error scenarios
        if (error?.response) {
          // Server responded with error status
          const errorMsg = error.response.data?.message || error.response.data?.error || error.message
          logger.error('DELETE (with body) Error (Response):', url, `Status ${error.response.status}:`, errorMsg)
          throw new Error(`${errorMsg} (Status: ${error.response.status})`)
        } else if (error?.request) {
          // Request was made but no response
          const errorMsg = error?.message || 'No response from server'
          logger.error('DELETE (with body) Error (No Response):', url, errorMsg)
          throw new Error(errorMsg)
        } else {
          // Something else happened
          const errorMsg = error?.message || 'Unknown error'
          logger.error('DELETE (with body) Error (Setup):', url, errorMsg)
          throw new Error(errorMsg)
        }
      })
  }
)

const getWithoutDecode = R.curry(
  (request, response, url: string, headers: any, queryParams: Object) => {
    const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')
    
    const cleanedHeaders = cleanHeaders(headers)

    logger.info('**** GET W/O Decode Request ****', serviceDomain + url)
    
    curlLogger({
      url: `${serviceDomain}${url}?${queryString.stringify(queryParams)}`,
      headers: cleanedHeaders,
      method: 'GET',
    })

    return axios
      .get(`${serviceDomain}${url}`, {
        headers: cleanedHeaders,
        params: queryParams,
      })
      .then((res: any) => R.prop('data')(res))
      .catch((error) => {
        logger.error('GET W/O Decode Error:', url, error?.message)
        throw error
      })
  }
)

const postWithoutDecode = (url: string, headers: any, body) => {
  const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')

  curlLogger({
    url: `${serviceDomain}${url}`,
    body: body,
    headers: {
      ...headers,
      'content-type': 'application/json',
    },
    method: 'POST',
  })

  return axios(`${serviceDomain}${url}`, {
    method: 'post',
    data: body,
    responseType: 'json',
    headers: headers,
  })
    .then((res: any) => R.prop('data')(res))
    .catch((error) => {
      logger.error('POST W/O Decode Error:', url, error?.message)
      throw error
    })
}

const getWithoutPermissionCheck = (
  url: string,
  headers: any,
  queryParams: Object
) => {
  const serviceDomain = getServiceHost(headers?.service || 'DEFAULT')

  curlLogger({
    url: `${serviceDomain}${url}?${queryString.stringify(queryParams)}`,
    headers: {
      ...headers,
      'content-type': 'application/json',
    },
    method: 'GET',
  })

  return axios(`${serviceDomain}${url}`, {
    method: 'get',
    params: queryParams,
    responseType: 'json',
    headers: headers,
  })
    .then((res: any) => R.prop('data')(res))
    .catch((error) => {
      logger.error('GET W/O Permission Check Error:', url, error?.message)
      throw error
    })
}

export const http = {
  get: get,
  post: post,
  put: put,
  getWithoutDecode: getWithoutDecode,
  postWithoutDecode: postWithoutDecode,
  patch: patch,
  delete: deleteReq,
  deleteWithBody: deleteWithBodyReq,
  getWithoutPermissionCheck: getWithoutPermissionCheck,
}

type HTTPReq = {
  get?: any
  post?: any
  getWithoutDecode?: any
  put?: any
  patch?: any
  delete?: any
  deleteWithBody?: any
  getWithoutPermissionCheck?: any
}

export type HttpIO = HTTPReq

