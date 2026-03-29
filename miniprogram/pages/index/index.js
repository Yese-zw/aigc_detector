const app = getApp()

const BASE_URL = "https://lingsi.chat/api/v1"
const API_KEY = "lingsi-analytics-secure-key-2026"
const ENDPOINT = "/analytics/dashboard-overview"

// 千分位格式化 (强制取整)
function formatNum(num) {
  if (num === null || num === undefined) return '0'
  return Math.round(parseFloat(num)).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

// 递归将对象中的所有数字都取整
function roundAllNumbers(obj) {
  if (typeof obj === 'number') {
    return Math.round(obj);
  } else if (Array.isArray(obj)) {
    return obj.map(roundAllNumbers);
  } else if (obj !== null && typeof obj === 'object') {
    const newObj = {};
    for (let key in obj) {
      newObj[key] = roundAllNumbers(obj[key]);
    }
    return newObj;
  }
  return obj;
}

Page({
  data: {
    statusBarHeight: 44,
    navHeight: 44,
    timeRange: '30d',
    isLoading: true,
    isRefreshing: false,
    lastUpdate: '',
    
    // 仪表盘数据
    users: {},
    revenue: {},
    orders: {},
    points: {},
    conversion: {},
    agents: {},
    realtime: {},

    // 格式化后的展示数据
    f_revenue: '0.00',
    f_today_rev: '0.00',
    f_total_users: '0',
    f_today_users: '0',
    f_total_orders: '0',
    f_today_orders: '0'
  },

  onLoad() {
    this.setData({
      statusBarHeight: app.globalData.statusBarHeight || 44,
      navHeight: app.globalData.navHeight || 44,
    })
    this.fetchDashboardData()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 })
    }
  },

  onPullDownRefresh() {
    this.onRefresh()
  },

  onRefresh() {
    this.setData({ isRefreshing: true })
    this.fetchDashboardData().then(() => {
      this.setData({ isRefreshing: false })
      wx.stopPullDownRefresh()
      wx.vibrateShort({ type: 'light' })
    })
  },

  switchTimeRange(e) {
    const range = e.currentTarget.dataset.range
    if (range === this.data.timeRange) return
    wx.vibrateShort({ type: 'light' })
    this.setData({ timeRange: range })
    this.fetchDashboardData()
  },

  fetchDashboardData() {
    this.setData({ isLoading: true })

    return new Promise((resolve) => {
      // 由于后端路由中并未包含 /api/v1 这个前缀，应直接使用 /admin/lingsi-dashboard
      const LOCAL_API_BASE = 'https://api.lingsi.chat/admin'

      wx.request({
        url: `${LOCAL_API_BASE}/lingsi-dashboard`,
        method: 'GET',
        data: { time_range: this.data.timeRange },
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data) {
            // 将返回结果中的所有浮点数一律强制取整
            const d = roundAllNumbers(res.data)
            
            const now = new Date()
            const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`

            this.setData({
              users: d.users || {},
              revenue: d.revenue || {},
              orders: d.orders || {},
              points: d.points || {},
              conversion: d.conversion || {},
              agents: d.agents || {},
              realtime: d.realtime || {},
              lastUpdate: timeStr,
              
              f_revenue: formatNum(d.revenue?.total),
              f_today_rev: formatNum(d.revenue?.today),
              f_total_users: formatNum(d.users?.total),
              f_today_users: formatNum(d.users?.today),
              f_total_orders: formatNum(d.orders?.total),
              f_today_orders: formatNum(d.orders?.today),
            })
          } else {
            wx.showToast({ title: '数据获取失败', icon: 'none' })
          }
        },
        fail: (err) => {
          console.error('Fetch error:', err)
          wx.showToast({ title: '网络请求失败', icon: 'none' })
        },
        complete: () => {
          this.setData({ isLoading: false })
          resolve()
        }
      })
    })
  }
})
