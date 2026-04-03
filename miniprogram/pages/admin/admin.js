const ADMIN_API_BASE = 'https://api.lingsiai.cn'
const DEFAULT_ADMIN_PWD = 'zw123' // 默认管理员密码

Page({
  data: {
    statusBarHeight: 44,
    isLoading: false,
    isRefreshing: false,
    isSubmitting: false,
    
    // Auth - 默认验证通过
    isAuthed: true,
    inputPassword: DEFAULT_ADMIN_PWD,
    
    // Token status info
    tokenStatusText: '检测中...',
    tokenStatusBadge: '...',
    tokenStatusClass: '',
    tokenInfo: null,
    
    // Input for updating token
    inputToken: '',
    
    // WX Login
    isWxLoading: false,
    wxQrUrl: '',
    wxRequestId: '',
    pollTimer: null
  },

  onLoad() {
    const sysInfo = wx.getWindowInfo()
    this.setData({ statusBarHeight: sysInfo.statusBarHeight || 44 })
    this.loadData()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }
  },

  onUnload() {
    this.stopPolling()
  },

  onPullDownRefresh() {
    this.onRefresh()
  },

  onRefresh() {
    this.setData({ isRefreshing: true })
    this.loadData().then(() => {
      this.setData({ isRefreshing: false })
      wx.stopPullDownRefresh()
      wx.vibrateShort({ type: 'light' })
    })
  },

  loadData() {
    this.setData({ isLoading: true })
    const pwd = this.data.inputPassword
    return new Promise((resolve) => {
      wx.request({
        url: `${ADMIN_API_BASE}/admin/token/info`,
        method: 'GET',
        header: {
          'Authorization': `Bearer ${pwd}`
        },
        success: (res) => {
          this.setData({ isLoading: false })
          if (res.statusCode === 200 && res.data && !res.data.error) {
            const d = res.data
            
            // 将秒转换为 'X小时 Y分钟'
            if (d.remaining_seconds != null) {
              const hrs = Math.floor(d.remaining_seconds / 3600)
              const mins = Math.floor((d.remaining_seconds % 3600) / 60)
              d.remaining_time_fmt = `${hrs}小时 ${mins}分钟`
            }
            
            const tokenMap = {
              active: { text: '正常运行，上游直连成功', badge: '● 在线', cls: 'status-active' },
              expired: { text: 'Token 已过期，请尽早更新', badge: '⚠ 过期', cls: 'status-warning' },
              empty: { text: '服务器暂无配置 Token', badge: '✗ 缺失', cls: 'status-error' },
              error: { text: '服务端解析失败', badge: '! 异常', cls: 'status-error' },
              unknown: { text: '状态未知', badge: '? 未知', cls: '' },
            }
            const ts = tokenMap[d.status] || tokenMap.unknown
            
            this.setData({
              tokenInfo: { ...d },
              tokenStatusText: ts.text,
              tokenStatusBadge: ts.badge,
              tokenStatusClass: ts.cls,
            })
          } else {
            wx.showToast({ title: '无法获取 Token 状态', icon: 'none' })
          }
          resolve()
        },
        fail: (err) => {
          this.setData({ isLoading: false })
          console.error(err)
          wx.showToast({ title: '网络连接失败', icon: 'none' })
          resolve()
        }
      })
    })
  },

  startWxLogin() {
    this.setData({ isWxLoading: true, wxQrUrl: '' })
    this.stopPolling()
    
    wx.request({
      url: `${ADMIN_API_BASE}/admin/wxlogin/start`,
      method: 'POST',
      header: { 'Authorization': `Bearer ${this.data.inputPassword}` },
      success: (res) => {
        this.setData({ isWxLoading: false })
        if (res.statusCode === 200 && res.data && res.data.code === 200 && res.data.data) {
           const d = res.data.data
           this.setData({
             wxQrUrl: d.qr_code || d.qr_url || d.qrcode_url,
             wxRequestId: d.request_id
           })
           // Start polling
           this.startPolling()
        } else {
           wx.showToast({ title: '获取二维码失败', icon: 'none' })
        }
      },
      fail: (err) => {
        this.setData({ isWxLoading: false })
        wx.showToast({ title: '请求失败', icon: 'none' })
      }
    })
  },

  startPolling() {
    this.stopPolling()
    // Poll every 2 seconds
    const timer = setInterval(() => {
      this.checkLoginStatus()
    }, 2000)
    this.setData({ pollTimer: timer })
  },

  stopPolling() {
    if (this.data.pollTimer) {
      clearInterval(this.data.pollTimer)
      this.setData({ pollTimer: null })
    }
  },

  checkLoginStatus() {
    const id = this.data.wxRequestId
    if (!id) return
    
    wx.request({
      url: `${ADMIN_API_BASE}/admin/wxlogin/status?request_id=${id}`,
      method: 'GET',
      header: { 'Authorization': `Bearer ${this.data.inputPassword}` },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.code === 200) {
          const d = res.data.data
          if (d && d.token) {
            this.stopPolling()
            wx.showToast({ title: '扫码成功！拦截 Token', icon: 'success' })
            this.setData({ 
              inputToken: d.token,
              wxQrUrl: ''
            })
            // Auto update
            this.doUpdate()
          } else if (res.data.msg === '授权成功') {
            // Wait for next poll or it may be in root
            if (res.data.token) {
              this.stopPolling()
              this.setData({ inputToken: res.data.token, wxQrUrl: '' })
              this.doUpdate()
            }
          }
        }
      }
    })
  },

  onTokenInput(e) {
    this.setData({ inputToken: e.detail.value })
  },
  
  clearInput() {
    this.setData({ inputToken: '' })
  },

  doUpdate() {
    const token = this.data.inputToken.trim()
    if (!token) return

    const pwd = this.data.inputPassword
    this.setData({ isSubmitting: true })
    
    wx.request({
      url: `${ADMIN_API_BASE}/admin/token`,
      method: 'POST',
      header: {
        'content-type': 'application/x-www-form-urlencoded',
        'Authorization': `Bearer ${pwd}`
      },
      data: {
        token: token
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.status === 'success') {
          wx.showToast({ title: 'Token 更新成功', icon: 'success' })
          this.clearInput()
          this.loadData()
        } else {
          wx.showToast({ title: res.data.message || '更新失败', icon: 'none' })
        }
      },
      fail: (err) => {
        console.error(err)
        wx.showToast({ title: '请求失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ isSubmitting: false })
      }
    })
  }
})
