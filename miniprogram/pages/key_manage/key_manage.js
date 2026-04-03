const ADMIN_API_BASE = 'https://api.lingsiai.cn/admin'

Page({
  data: {
    keys: [],
    totalQuota: 0,
    activeKeys: 0,
    isLoading: true,
    showAddModal: false,
    showQuotaModal: false,
    newKey: { name: '', quota: 100000, description: '' },
    currentKey: '',
    quotaToAdd: 0
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
          const keys = res.data.data || []
          let totalQ = 0
          let activeK = 0
          keys.forEach(k => {
            totalQ += (k.total_quota || 0)
            if (k.is_active) activeK++
          })
          this.setData({ 
            keys,
            totalQuota: totalQ,
            activeKeys: activeK
          })
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
    this.setData({
      currentKey: e.currentTarget.dataset.key,
      showQuotaModal: true,
      quotaToAdd: 0
    })
  },

  onQuotaInput(e) {
    this.setData({ quotaToAdd: parseInt(e.detail.value) || 0 })
  },

  confirmQuota() {
    const { currentKey, quotaToAdd } = this.data
    if (!quotaToAdd) return wx.showToast({ title: '请输入额度', icon: 'none' })
    
    wx.showLoading({ title: '调整中' })
    wx.request({
      url: `${ADMIN_API_BASE}/keys/${currentKey}?add_quota=${quotaToAdd}`,
      method: 'PUT',
      header: this.getAuthHeader(),
      success: () => {
        wx.showToast({ title: '额度已更新', icon: 'success' })
        this.closeModals()
        this.fetchKeys()
      },
      complete: () => wx.hideLoading()
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
              wx.showToast({ title: '密钥已灰飞烟灭', icon: 'success' })
              this.fetchKeys()
            },
            complete: () => wx.hideLoading()
          })
        }
      }
    })
  },

  openAddModal() {
    this.setData({ showAddModal: true })
  },

  onNewKeyInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`newKey.${field}`]: e.detail.value })
  },

  confirmAddKey() {
    const { name, quota, description } = this.data.newKey
    if (!name) return wx.showToast({ title: '请输入名称', icon: 'none' })
    
    wx.showLoading({ title: '创建中' })
    wx.request({
      url: `${ADMIN_API_BASE}/keys`,
      method: 'POST',
      header: {
        ...this.getAuthHeader(),
        'content-type': 'application/x-www-form-urlencoded'
      },
      data: `name=${encodeURIComponent(name)}&quota=${quota}&description=${encodeURIComponent(description)}`,
      success: (res) => {
        if (res.data.status === 'success') {
          wx.showToast({ title: '创建成功', icon: 'success' })
          this.closeModals()
          this.fetchKeys()
        } else {
          wx.showToast({ title: res.data.error || '创建失败', icon: 'none' })
        }
      },
      complete: () => wx.hideLoading()
    })
  },

  closeModals() {
    this.setData({ 
      showAddModal: false, 
      showQuotaModal: false,
      newKey: { name: '', quota: 100000, description: '' }
    })
  }
})
