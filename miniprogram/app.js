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
