const ADMIN_API_BASE = 'https://api.lingsi.chat/admin'

Page({
  data: {
    keys: [],
    isLoading: true
  },

  onLoad() {
    this.fetchKeys()
  },

  getAuthHeader() {
    const pwd = wx.getStorageSync('admin_password') || 'zw123'
    return {
      'Authorization': `Bearer ${pwd}`
    }
  },

  fetchKeys() {
    this.setData({ isLoading: true })
    wx.showNavigationBarLoading()
    wx.request({
      url: `${ADMIN_API_BASE}/keys`,
      method: 'GET',
      header: this.getAuthHeader(),
      success: (res) => {
        if (res.data && res.data.status === 'success') {
          this.setData({ keys: res.data.data })
        } else {
          wx.showToast({ title: '加载失败', icon: 'none' })
        }
      },
      complete: () => {
        this.setData({ isLoading: false })
        wx.hideNavigationBarLoading()
      }
    })
  },

  copyKey(e) {
    const key = e.currentTarget.dataset.key
    wx.setClipboardData({
      data: key,
      success: () => {
        wx.showToast({ title: '已复制密钥', icon: 'success' })
      }
    })
  },

  modifyQuota(e) {
    const key = e.currentTarget.dataset.key
    wx.showModal({
      title: '调整可用额度',
      content: '',
      editable: true,
      placeholderText: '输入要增加的额度',
      success: (res) => {
        if (res.confirm && res.content) {
          const addQuota = parseInt(res.content)
          if (isNaN(addQuota)) {
             return wx.showToast({ title: '请输入正确的数字', icon: 'error' })
          }
          wx.showLoading({ title: '调整中' })
          wx.request({
            url: `${ADMIN_API_BASE}/keys/${key}?add_quota=${addQuota}`,
            method: 'PUT',
            header: this.getAuthHeader(),
            success: (fetchRes) => {
              wx.hideLoading()
              wx.showToast({ title: '额度已更新', icon: 'success' })
              this.fetchKeys()
            },
            fail: () => {
              wx.hideLoading()
              wx.showToast({ title: '网络请求失败', icon: 'none' })
            }
          })
        }
      }
    })
  },

  deleteKey(e) {
    const key = e.currentTarget.dataset.key
    wx.showModal({
      title: '吊销确认',
      content: '严重警告：确定要永久销毁该分发密钥吗？关联终端将立即断连。',
      confirmColor: '#FF6B6B',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '销毁中' })
          wx.request({
            url: `${ADMIN_API_BASE}/keys/${key}`,
            method: 'DELETE',
            header: this.getAuthHeader(),
            success: () => {
              wx.hideLoading()
              wx.showToast({ title: '密钥已灰飞烟灭', icon: 'success' })
              this.fetchKeys()
            }
          })
        }
      }
    })
  },

  toggleActive(e) {
    const key = e.currentTarget.dataset.key
    const isActive = e.detail.value
    wx.request({
      url: `${ADMIN_API_BASE}/keys/${key}?is_active=${isActive}`,
      method: 'PUT',
      header: this.getAuthHeader(),
      success: (res) => {
        wx.showToast({ title: isActive ? '网关通道已放行' : '网关通道已阻断', icon: 'success' })
        this.fetchKeys()
      }
    })
  },

  openAddModal() {
    wx.showToast({ title: '请在桌面端云管控中心添加新品', icon: 'none' })
  }
})
