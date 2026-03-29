/**
 * API 请求工具 - AIGC Detector
 * 使用 X-API-Key 认证
 */
const BASE_URL = 'https://api.lingsi.chat/api/v1/ai'
const STORAGE_KEY = 'user_api_key'

/** 获取 API Key */
function getApiKey() {
  return wx.getStorageSync(STORAGE_KEY) || ''
}

/** 保存 API Key */
function setApiKey(key) {
  wx.setStorageSync(STORAGE_KEY, key)
}

/** 移除 API Key */
function removeApiKey() {
  wx.removeStorageSync(STORAGE_KEY)
}

/**
 * 统一请求封装
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const apiKey = getApiKey()
    const header = {
      'Content-Type': 'application/json',
      ...options.header
    }
    if (apiKey) {
      header['X-API-Key'] = apiKey
    }

    wx.request({
      url: `${BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data || {},
      header,
      timeout: options.timeout || 30000,
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          wx.showToast({ title: 'API Key 无效或未设置', icon: 'none' })
          reject(new Error('Unauthorized'))
        } else if (res.statusCode === 402) {
          const msg = res.data?.detail || '额度不足'
          wx.showToast({ title: msg.slice(0, 30), icon: 'none' })
          reject(new Error(msg))
        } else {
          const errorMsg = res.data?.detail || res.data?.message || '请求失败'
          reject(new Error(errorMsg))
        }
      },
      fail: (err) => {
        wx.showToast({ title: '网络连接失败', icon: 'none' })
        reject(err)
      }
    })
  })
}

/**
 * 上传文件 - 使用 wx.uploadFile
 */
function uploadFile(filePath, formData) {
  return new Promise((resolve, reject) => {
    const apiKey = getApiKey()
    const header = {}
    if (apiKey) header['X-API-Key'] = apiKey

    wx.uploadFile({
      url: `${BASE_URL}/upload`,
      filePath,
      name: 'file',
      formData,
      header,
      timeout: 60000,
      success: (res) => {
        if (res.statusCode === 200) {
          try {
            const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
            resolve(data)
          } catch (e) {
            resolve(res.data)
          }
        } else if (res.statusCode === 402) {
          wx.showToast({ title: '额度不足', icon: 'none' })
          reject(new Error('额度不足'))
        } else {
          reject(new Error('上传失败'))
        }
      },
      fail: (err) => {
        wx.showToast({ title: '上传失败', icon: 'none' })
        reject(err)
      }
    })
  })
}

module.exports = {
  request,
  uploadFile,
  getApiKey,
  setApiKey,
  removeApiKey,
  BASE_URL
}
