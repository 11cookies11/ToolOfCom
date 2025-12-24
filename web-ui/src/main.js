import { createApp } from 'vue'
import ElementPlus, { FixedSizeList } from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/es/components/virtual-list/style/css'
import './style.css'
import App from './App.vue'

function initWebChannel() {
  if (!window.qt || !window.qt.webChannelTransport) {
    return Promise.resolve(null)
  }
  return new Promise((resolve) => {
    // eslint-disable-next-line no-undef
    new QWebChannel(window.qt.webChannelTransport, (channel) => {
      const bridge = channel.objects.bridge
      window.bridge = bridge
      resolve(bridge)
    })
  })
}

async function bootstrap() {
  const bridge = await initWebChannel()
  if (bridge) {
    bridge.log.connect((msg) => {
      console.log('[bridge]', msg)
    })
    bridge.notify_ready()
    bridge.ping('web-ui').then((resp) => console.log(resp))
  }
  const app = createApp(App)
  app.use(ElementPlus)
  app.component('ElFixedSizeList', FixedSizeList)
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }
  app.mount('#app')
}

bootstrap()
