Page({
  data: {
    theme: 'theme-dark'
  },
  onShow() {
    this.setData({
      theme: wx.getStorageSync('app_theme') || 'theme-dark'
    })
  },
  setDark() {
    wx.setStorageSync('app_theme', 'theme-dark')
    this.setData({ theme: 'theme-dark' })
    wx.setNavigationBarColor({ frontColor: '#ffffff', backgroundColor: '#0B0B1A' })
    wx.showToast({ title: '切换 液态玻璃', icon: 'success' })
  },
  setLight() {
    wx.setStorageSync('app_theme', 'theme-light')
    this.setData({ theme: 'theme-light' })
    wx.setNavigationBarColor({ frontColor: '#000000', backgroundColor: '#F0F4F8' })
    wx.showToast({ title: '切换 极地简白', icon: 'success' })
  }
})