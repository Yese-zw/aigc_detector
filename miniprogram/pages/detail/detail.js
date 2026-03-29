/**
 * DETAIL PAGE - 内容详情逻辑
 */
const app = getApp()
const { request } = require('../../utils/api')
const { formatDate } = require('../../utils/util')

Page({
  data: {
    statusBarHeight: 44,
    navHeight: 44,
    detail: {},
    isLiked: false,
    isCollected: false,
  },

  onLoad(options) {
    const statusBarHeight = app.globalData.statusBarHeight || 44
    const menuButton = wx.getMenuButtonBoundingClientRect()
    const navHeight = (menuButton.top - statusBarHeight) * 2 + menuButton.height
    this.setData({ statusBarHeight, navHeight })

    if (options.id) {
      this.loadDetail(options.id)
    }
  },

  async loadDetail(id) {
    try {
      const res = await request({ url: `/contents/${id}` })
      const detail = res.data || res
      detail.created_at_formatted = formatDate(detail.created_at, 'YYYY-MM-DD')
      this.setData({ detail })
    } catch (err) {
      console.error('加载详情失败:', err)
      this.setData({
        detail: {
          title: '液态玻璃设计趋势',
          subtitle: '2026年最前沿的UI设计语言',
          cover_image: 'https://picsum.photos/750/500?random=30',
          category: '设计',
          author: 'Design Team',
          view_count: 1280,
          like_count: 356,
          content: '<p>液态玻璃设计是玻璃拟态（Glassmorphism）的进阶版本，它不再只是简单的毛玻璃模糊效果，而是融合了动态渐变、折射光泽与流体质感。</p><p>这种设计语言的核心理念是让数字界面具备物理世界中液体和玻璃的视觉特征——透明、流动、折射，从而创造出既科技又优雅的用户体验。</p><p>在实际应用中，液态玻璃效果通常通过以下技术实现：backdrop-filter 模糊、多层渐变叠加、动态阴影变化、以及 CSS 动画驱动的光泽流动。</p>',
          created_at_formatted: '2026-03-28',
        }
      })
    }
  },

  goBack() {
    wx.navigateBack({ delta: 1 })
  },

  handleLike() {
    wx.vibrateShort({ type: 'medium' })
    const isLiked = !this.data.isLiked
    const detail = { ...this.data.detail }
    detail.like_count = (detail.like_count || 0) + (isLiked ? 1 : -1)
    this.setData({ isLiked, detail })
    wx.showToast({ title: isLiked ? '已喜欢 ❤️' : '取消喜欢', icon: 'none', duration: 1000 })
  },

  handleCollect() {
    wx.vibrateShort({ type: 'medium' })
    const isCollected = !this.data.isCollected
    this.setData({ isCollected })
    wx.showToast({ title: isCollected ? '已收藏 ⭐' : '取消收藏', icon: 'none', duration: 1000 })
  },

  handleShare() {
    wx.showToast({ title: '分享功能开发中', icon: 'none' })
  },

  onShare() {
    this.handleShare()
  },

  onShareAppMessage() {
    return {
      title: this.data.detail.title || 'Modern App',
      path: `/pages/detail/detail?id=${this.data.detail.id}`,
      imageUrl: this.data.detail.cover_image,
    }
  }
})
