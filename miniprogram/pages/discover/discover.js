const app = getApp()
const { request } = require('../../utils/api')

Page({
  data: {
    statusBarHeight: 44,
    navHeight: 44,
    text: '',
    comboId: '100', // default rewrite
    wordCount: 0,
    isLoading: false,
    result: null,
    resultText: '',
    resultStr: '',
    quotaInfo: null
  },

  onLoad() {
    this.setData({
      statusBarHeight: app.globalData.statusBarHeight,
      navHeight: app.globalData.navHeight,
    })
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }
  },

  setCombo(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ comboId: String(id) })
  },

  onInput(e) {
    const val = e.detail.value
    this.setData({
      text: val,
      wordCount: val.replace(/\s+/g, '').length
    })
  },

  clearText() {
    this.setData({ text: '', wordCount: 0, result: null, resultText: '', resultStr: '', quotaInfo: null })
  },

  pasteText() {
    wx.getClipboardData({
      success: (res) => {
        const val = this.data.text + res.data
        this.setData({
          text: val,
          wordCount: val.replace(/\s+/g, '').length
        })
      }
    })
  },

  copyResult() {
    if (!this.data.resultText) return
    wx.setClipboardData({
      data: this.data.resultText,
      success: () => {
        wx.showToast({ title: '复制成功', icon: 'success' })
      }
    })
  },

  async doRewrite() {
    if (!this.data.text.trim()) {
      wx.showToast({ title: '请输入文本', icon: 'none' })
      return
    }

    this.setData({ isLoading: true, result: null, resultText: '', resultStr: '', quotaInfo: null })

    try {
      const res = await request({
        url: '/AIRewrite',
        method: 'POST',
        data: {
          text: this.data.text,
          combination_id: this.data.comboId
        }
      })

      if (res.status === 'success') {
        const resultData = res.result
        let displayStr = JSON.stringify(resultData, null, 2)
        let extractedText = ''
        let parsedJSON = resultData
        
        if (typeof resultData === 'string') {
          try {
            parsedJSON = JSON.parse(resultData)
            displayStr = JSON.stringify(parsedJSON, null, 2)
          } catch (e) {
            extractedText = resultData
          }
        }

        // Try to identify the rewritten text field
        if (typeof parsedJSON === 'object') {
          // Assume common field names for rewritten text
          if (parsedJSON.rewrite_text) extractedText = parsedJSON.rewrite_text;
          else if (parsedJSON.text) extractedText = parsedJSON.text;
          else if (parsedJSON.result) extractedText = parsedJSON.result;
        }

        this.setData({
          result: parsedJSON,
          resultText: extractedText || '',
          resultStr: displayStr,
          quotaInfo: res.quota_info,
          isLoading: false
        })

        // 更新全局额度，以便 profile 页使用
        if (res.quota_info) {
          app.globalData.quotaInfo = res.quota_info
        }
      }
    } catch (err) {
      this.setData({ isLoading: false })
      console.error(err)
    }
  }
})
