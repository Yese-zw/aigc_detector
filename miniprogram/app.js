/**
 * AIGC Detector 小程序 - 全局逻辑
 */
const { getApiKey } = require('./utils/api')

App({
  globalData: {
    apiKey: '',
    quotaInfo: null,
    statusBarHeight: 0,
    navBarHeight: 0,
    systemInfo: null,
  },

  onLaunch() {
    const systemInfo = wx.getWindowInfo()
    const menuButton = wx.getMenuButtonBoundingClientRect()
    this.globalData.systemInfo = systemInfo
    this.globalData.statusBarHeight = systemInfo.statusBarHeight || 44
    this.globalData.navBarHeight =
      (menuButton.top - systemInfo.statusBarHeight) * 2 +
      menuButton.height +
      systemInfo.statusBarHeight

    // 读取保存的 API Key
    this.globalData.apiKey = getApiKey()

    // 动态加载全量图标库 (WOFF2 Base64)
    wx.loadFontFace({
      family: 'iconfont',
      source: 'url("data:font/woff2;charset=utf-8;base64,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")',
      global: true,
      success: res => console.log('Iconfont loaded via API'),
      fail: err => console.error('Iconfont API failed', err)
    })
  },

  /**
   * 获取时间段问候语
   */
  getGreeting() {
    const hour = new Date().getHours()
    if (hour < 6)  return { text: '夜深了', emoji: '🌙' }
    if (hour < 9)  return { text: '早上好', emoji: '🌅' }
    if (hour < 12) return { text: '上午好', emoji: '☀️' }
    if (hour < 14) return { text: '中午好', emoji: '🌤️' }
    if (hour < 18) return { text: '下午好', emoji: '🌇' }
    if (hour < 22) return { text: '晚上好', emoji: '🌆' }
    return { text: '夜深了', emoji: '🌙' }
  }
})
