const ADMIN_API_BASE = 'https://api.lingsiai.cn/admin'

Page({
  data: {
    logs: '',
    scrollTop: 0
  },
  
  onLoad() {
    this.fetchLogs()
  },

  getAuthHeader() {
    const pwd = wx.getStorageSync('admin_password') || 'zw123'
    return {
      'Authorization': `Bearer ${pwd}`
    }
  },

  fetchLogs() {
    wx.showNavigationBarLoading()
    wx.request({
      url: `${ADMIN_API_BASE}/logs`,
      method: 'GET',
      header: this.getAuthHeader(),
      success: (res) => {
        wx.hideNavigationBarLoading()
        if (res.data && res.data.content) {
          this.setData({ 
            logs: res.data.content,
            scrollTop: 999999 
          })
          wx.showToast({ title: '已同步', icon: 'success' })
        } else {
          this.setData({ logs: '>>> 暂无底层日志数据返回' })
        }
      },
      fail: () => {
        wx.hideNavigationBarLoading()
        this.setData({ logs: '>>> Node 控制台通信阻断，网络请求失败...' })
      }
    })
  }
})
