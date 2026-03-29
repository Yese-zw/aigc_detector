/**
 * LOGIN PAGE - 微信登录逻辑
 */
const app = getApp()

Page({
  data: {
    isLoading: false,
    agreed: true,
  },

  onLoad() {
    // 如果已经登录，跳转首页
    if (app.globalData.isLoggedIn) {
      wx.switchTab({ url: '/pages/index/index' })
    }
  },

  /**
   * 微信登录
   */
  async handleWxLogin() {
    if (this.data.isLoading) return

    if (!this.data.agreed) {
      wx.showToast({
        title: '请先同意用户协议',
        icon: 'none'
      })
      return
    }

    this.setData({ isLoading: true })

    // 触发触感反馈
    wx.vibrateShort({ type: 'medium' })

    try {
      await app.wxLogin()

      wx.showToast({
        title: '登录成功',
        icon: 'success',
        duration: 1500
      })

      // 延时跳转，让用户看到成功提示
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' })
      }, 1000)
    } catch (err) {
      console.error('登录失败:', err)
      wx.showToast({
        title: err.message || '登录失败，请重试',
        icon: 'none'
      })
    } finally {
      this.setData({ isLoading: false })
    }
  },

  /**
   * 切换协议同意状态
   */
  toggleAgreement() {
    wx.vibrateShort({ type: 'light' })
    this.setData({ agreed: !this.data.agreed })
  },

  /**
   * 查看用户协议
   */
  showUserAgreement() {
    wx.showModal({
      title: '用户协议',
      content: '本应用尊重并保护所有使用服务用户的个人隐私权。为了给您提供更准确、更有个性化的服务，本应用会按照本隐私权政策的规定使用和披露您的个人信息。',
      showCancel: false,
      confirmText: '我知道了'
    })
  },

  /**
   * 查看隐私政策
   */
  showPrivacyPolicy() {
    wx.showModal({
      title: '隐私政策',
      content: '我们深知个人信息对您的重要性，并会尽全力保护您的个人信息安全可靠。我们致力于维持您对我们的信任，恪守权责一致、目的明确、选择同意、最少够用、确保安全、主体参与、公开透明的原则。',
      showCancel: false,
      confirmText: '我知道了'
    })
  }
})
