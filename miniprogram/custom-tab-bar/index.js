/**
 * CUSTOM TAB BAR - 液态玻璃底部导航组件
 */
Component({
  data: {
    selected: 0,
    indicatorLeft: 0,
    list: [
      {
        pagePath: '/pages/index/index',
        text: '数据大屏',
        icon: 'icon-chart',
        selectedIcon: 'icon-chart',
      },
      {
        pagePath: '/pages/admin/admin',
        text: 'Token管理',
        icon: 'icon-lock',
        selectedIcon: 'icon-lock',
      },
      {
        pagePath: '/pages/profile/profile',
        text: '我的',
        icon: 'icon-user',
        selectedIcon: 'icon-user',
      }
    ]
  },

  attached() {
    this.updateIndicator(this.data.selected)
  },

  observers: {
    'selected': function(index) {
      this.updateIndicator(index)
    }
  },

  methods: {
    switchTab(e) {
      const data = e.currentTarget.dataset
      const index = data.index
      const url = data.path

      if (this.data.selected === index) return

      wx.vibrateShort({ type: 'light' })

      this.setData({ selected: index })
      this.updateIndicator(index)

      wx.switchTab({ url })
    },

    updateIndicator(index) {
      // 计算指示器位置
      const query = this.createSelectorQuery()
      query.select('.tab-bar-inner').boundingClientRect()
      query.exec((res) => {
        if (res[0]) {
          const barWidth = res[0].width
          const tabWidth = barWidth / this.data.list.length
          const indicatorWidth = 40 // 指示器宽度 px（约80rpx）
          const left = tabWidth * index + (tabWidth - indicatorWidth) / 2
          this.setData({ indicatorLeft: left })
        }
      })
    }
  }
})
