const app = getApp()
const STORAGE_KEY = 'admin_password'

Page({
  data: {
    statusBarHeight: 44,
    navHeight: 44,
    isLoggedIn: true,
    userInfo: {
      nickname: '系统管理员',
      avatar_url: '',
      id: '8888'
    },
    defaultAvatar: '/assets/default_avatar.png',
    stats: {
      loginCount: 16,
      viewCount: 128,
      likeCount: 9
    },
    unreadCount: 3
  },

  onLoad() {
    const sysInfo = wx.getWindowInfo()
    this.setData({ 
      statusBarHeight: sysInfo.statusBarHeight || 44,
      navHeight: 44
    })
  },
  
  onShow() {
    this.setData({ theme: wx.getStorageSync('app_theme') || 'theme-dark' })
    if (this.data.theme === 'theme-light') {
       wx.setNavigationBarColor({ frontColor: '#000000', backgroundColor: '#F0F4F8' })
    } else {
       wx.setNavigationBarColor({ frontColor: '#ffffff', backgroundColor: '#0B0B1A' })
    }
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2, theme: this.data.theme })
    }
  },

  onSettings() {
    wx.showToast({ title: '系统设置', icon: 'none' })
  },

  chooseAvatar() {
    if (!this.data.isLoggedIn) return;
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      success: (res) => {
        const file = res.tempFiles[0]
        this.setData({
          'userInfo.avatar_url': file.tempFilePath
        })
      }
    })
  },

  goLogin() {
    this.setData({ isLoggedIn: true })
    wx.showToast({ title: '登录成功', icon: 'success' })
  },

  editProfile() {
    wx.showToast({ title: '编辑资料功能', icon: 'none' })
  },

  handleMenuTap(e) {
    const type = e.currentTarget.dataset.type
    if (type === 'key_manage') {
       wx.navigateTo({ url: '/pages/key_manage/key_manage' })
    } else if (type === 'sys_logs') {
       wx.navigateTo({ url: '/pages/sys_logs/sys_logs' })
    } else if (type === 'theme') {
       wx.navigateTo({ url: '/pages/theme/theme' })
    } else {
       wx.showToast({ title: '正在建设中', icon: 'none' })
    }
  },
  
  handleLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync(STORAGE_KEY)
          this.setData({ 
             isLoggedIn: false,
             unreadCount: 0,
             stats: { loginCount: 0, viewCount: 0, likeCount: 0 },
             userInfo: { nickname: '', avatar_url: '', id: '' }
          })
          wx.showToast({ title: '已安全退出', icon: 'success' })
        }
      }
    })
  }
})
