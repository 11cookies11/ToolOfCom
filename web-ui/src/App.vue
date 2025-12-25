<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const bridge = ref(null)
const connectionInfo = ref({ state: 'disconnected', detail: '' })
const ports = ref([])
const selectedPort = ref('')
const baud = ref(115200)
const tcpHost = ref('127.0.0.1')
const tcpPort = ref(502)
const channelMode = ref('serial')
const sendMode = ref('text')
const displayMode = ref('ascii')
const sendText = ref('')
const sendHex = ref('')
const commLogs = ref([])
const scriptLogs = ref([])
const scriptState = ref('idle')
const scriptProgress = ref(0)
const yamlText = ref('# paste DSL YAML here')
const currentView = ref('manual')
const logKeyword = ref('')
const logTab = ref('all')
const appendCR = ref(true)
const appendLF = ref(true)
const loopSend = ref(false)
const draggingWindow = ref(false)
const dragArmed = ref(false)
const dragStarted = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const snapPreview = ref('')
const enableSnapPreview = ref(false)
const portDropdownOpen = ref(false)
const portDropdownRef = ref(null)
const portPlaceholder = 'COM3 - USB Serial (115200)'

const portOptions = computed(() => (ports.value.length ? ports.value : [portPlaceholder]))
const noPorts = computed(() => ports.value.length === 0)
const selectedPortLabel = computed(() => selectedPort.value || portOptions.value[0] || '')

const quickCommands = ref([
  'AT+GMR',
  'RESET_DEVICE_01',
  'GET_WIFI_STATUS',
  'PING_SERVER',
])

const channelCards = ref([
  {
    id: 'serial-main',
    name: '主控板通信链路',
    type: 'Serial',
    status: 'connected',
    statusText: '已连接',
    statusClass: 'status-ok',
    details: ['COM3', '115200, 8, N, 1'],
    traffic: 'TX: 12.5 MB / RX: 48.2 MB',
  },
  {
    id: 'tcp-client',
    name: '远程遥测服务',
    type: 'TCP Client',
    status: 'connecting',
    statusText: '连接中...',
    statusClass: 'status-warn',
    details: ['192.168.1.200', 'Port: 502 (Modbus)'],
    traffic: 'TX: 0 B / RX: 0 B',
  },
  {
    id: 'tcp-server',
    name: '本地调试接口',
    type: 'TCP Server',
    status: 'idle',
    statusText: '已停止',
    statusClass: 'status-idle',
    details: ['0.0.0.0', 'Port: 8080'],
    traffic: '--',
  },
  {
    id: 'serial-error',
    name: '遗留设备端口',
    type: 'Serial',
    status: 'error',
    statusText: '无法打开',
    statusClass: 'status-error',
    details: ['COM1', '9600, 8, N, 1'],
    traffic: '--',
  },
])

const protocolCards = ref([
  {
    id: 'modbus-rtu',
    name: 'Modbus_RTU_Core',
    desc: '主生产线传感器',
    statusText: '运行中',
    statusClass: 'badge-green',
    rows: [
      { label: '协议类型', value: 'Modbus RTU' },
      { label: '绑定通道', value: 'COM3 (/dev/ttyUSB0)' },
      { label: '轮询间隔', value: '500ms' },
    ],
  },
  {
    id: 'tcp-client',
    name: 'Lab_TCP_Client',
    desc: '实验室数据采集',
    statusText: '离线',
    statusClass: 'badge-gray',
    rows: [
      { label: '协议类型', value: 'TCP Client' },
      { label: '目标地址', value: '192.168.1.105:8080' },
      { label: '重连策略', value: '指数退避' },
    ],
  },
  {
    id: 'custom-binary',
    name: 'Custom_Binary_V2',
    desc: '私有二进制协议',
    statusText: '草稿',
    statusClass: 'badge-yellow',
    rows: [
      { label: 'DSL 版本', value: 'v2.1 (YAML)' },
      { label: '绑定通道', value: '未绑定' },
      { label: '最后编辑', value: '2小时前' },
    ],
  },
])

const isConnected = computed(() => connectionInfo.value.state === 'connected')

const consoleLogs = computed(() => filterLogs(commLogs.value))
const uartLogs = computed(() => filterLogs(commLogs.value))
const tcpLogs = computed(() => filterLogs([]))
const scriptViewLogs = computed(() => filterLogs(scriptLogs.value))

function filterLogs(lines) {
  const keyword = logKeyword.value.trim().toLowerCase()
  if (!keyword) return lines
  return lines.filter((line) => {
    if (typeof line === 'string') {
      return line.toLowerCase().includes(keyword)
    }
    const text = String(line.text || '').toLowerCase()
    const hex = String(line.hex || '').toLowerCase()
    return text.includes(keyword) || hex.includes(keyword)
  })
}

function formatTime(ts) {
  const date = new Date((ts || 0) * 1000)
  const pad = (value, len = 2) => String(value).padStart(len, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${pad(
    date.getMilliseconds(),
    3
  )}`
}

function formatPayload(item) {
  if (!item) return ''
  if (displayMode.value === 'hex' && item.hex) return item.hex
  return item.text || ''
}

function addCommLog(kind, payload) {
  commLogs.value.unshift({
    kind,
    text: payload.text || '',
    hex: payload.hex || '',
    ts: payload.ts || Date.now() / 1000,
  })
  if (commLogs.value.length > 200) commLogs.value.pop()
}

function addScriptLog(line) {
  scriptLogs.value.unshift(line)
  if (scriptLogs.value.length > 200) scriptLogs.value.pop()
}

function addCommBatch(batch) {
  if (!Array.isArray(batch)) return
  for (const item of batch) {
    if (!item) continue
    const kind = item.kind || 'RX'
    if (kind === 'FRAME') {
      addCommLog('FRAME', { text: JSON.stringify(item.payload), ts: item.ts })
    } else {
      addCommLog(kind, item.payload || {})
    }
  }
}

function withResult(value, handler) {
  if (value && typeof value.then === 'function') {
    value.then(handler)
  } else {
    handler(value)
  }
}

function refreshPorts() {
  if (!bridge.value) return
  withResult(bridge.value.list_ports(), (items) => {
    ports.value = items || []
    if (!selectedPort.value && ports.value.length) {
      selectedPort.value = ports.value[0]
    }
  })
}

function connectSerial() {
  if (!bridge.value) return
  bridge.value.connect_serial(selectedPort.value, Number(baud.value))
}

function connectTcp() {
  if (!bridge.value) return
  bridge.value.connect_tcp(tcpHost.value, Number(tcpPort.value))
}

function connectPrimary() {
  if (channelMode.value === 'tcp') {
    connectTcp()
  } else {
    connectSerial()
  }
}

function disconnect() {
  if (!bridge.value) return
  bridge.value.disconnect()
}

function applyLineEndings(text) {
  let payload = text
  if (appendCR.value) payload += '\r'
  if (appendLF.value) payload += '\n'
  return payload
}

function applyHexLineEndings(text) {
  const parts = text.trim().split(/\\s+/).filter(Boolean)
  if (appendCR.value) parts.push('0D')
  if (appendLF.value) parts.push('0A')
  return parts.join(' ')
}

function sendAscii() {
  if (!bridge.value || !sendText.value) return
  const payload = applyLineEndings(sendText.value)
  bridge.value.send_text(payload)
}

function sendHexData() {
  if (!bridge.value || !sendHex.value) return
  const payload = applyHexLineEndings(sendHex.value)
  bridge.value.send_hex(payload)
}

function sendPayload() {
  if (sendMode.value === 'hex') {
    sendHexData()
  } else {
    sendAscii()
  }
}

function sendQuickCommand(cmd) {
  if (!cmd) return
  sendText.value = cmd
  sendMode.value = 'text'
  sendAscii()
}

function runScript() {
  if (!bridge.value || !yamlText.value) return
  bridge.value.run_script(yamlText.value)
}

function stopScript() {
  if (!bridge.value) return
  bridge.value.stop_script()
}

function loadYaml() {
  addScriptLog('[INFO] Load YAML not wired yet')
}

function saveYaml() {
  addScriptLog('[INFO] Save YAML not wired yet')
}

function attachBridge(obj) {
  bridge.value = obj
  obj.comm_batch.connect((batch) => addCommBatch(batch))
  obj.comm_status.connect((payload) => {
    const detail = payload && payload.payload !== undefined ? payload.payload : payload
    if (!detail) {
      connectionInfo.value = { state: 'disconnected', detail: '' }
      return
    }
    if (typeof detail === 'string') {
      connectionInfo.value = { state: 'error', detail }
      return
    }
    connectionInfo.value = {
      state: 'connected',
      detail: detail.address || detail.port || detail.type || '',
    }
  })
  obj.script_log.connect((line) => addScriptLog(line))
  obj.script_state.connect((state) => {
    scriptState.value = state
  })
  obj.script_progress.connect((value) => {
    scriptProgress.value = value
  })
  refreshPorts()
}

onMounted(() => {
  const timer = setInterval(() => {
    if (window.bridge) {
      attachBridge(window.bridge)
      clearInterval(timer)
    }
  }, 200)
  window.addEventListener('click', handlePortDropdownClick)
  window.addEventListener('keydown', handlePortDropdownKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handlePortDropdownClick)
  window.removeEventListener('keydown', handlePortDropdownKeydown)
})

function armWindowMove(event) {
  if (!event) return
  dragArmed.value = true
  dragStarted.value = false
  dragStart.value = { x: event.screenX, y: event.screenY }
}

function maybeStartWindowMove(event) {
  if (!dragArmed.value || dragStarted.value || !event) return
  const dx = Math.abs(event.screenX - dragStart.value.x)
  const dy = Math.abs(event.screenY - dragStart.value.y)
  if (dx < 10 && dy < 10) return
  if (bridge.value) {
    if (bridge.value.window_start_move_at) {
      bridge.value.window_start_move_at(Math.round(event.screenX), Math.round(event.screenY))
    } else {
      bridge.value.window_start_move()
    }
  }
  dragStarted.value = true
  draggingWindow.value = true
  document.body.classList.add('resizing')
  snapPreview.value = ''
  attachDragListeners()
}

function minimizeWindow() {
  if (bridge.value) {
    bridge.value.window_minimize()
  }
}

function toggleMaximize() {
  if (bridge.value) {
    bridge.value.window_toggle_maximize()
  }
}

function closeWindow() {
  if (bridge.value) {
    bridge.value.window_close()
  }
}

function applyWindowSnap(event) {
  if (bridge.value && event && dragStarted.value) {
    bridge.value.window_apply_snap(Math.round(event.screenX), Math.round(event.screenY))
  }
  clearDragState()
}

function showSystemMenu(event) {
  if (bridge.value && event) {
    bridge.value.window_show_system_menu(Math.round(event.screenX), Math.round(event.screenY))
  }
}

function startResize(edge, event) {
  if (!bridge.value || !edge || !event) return
  document.body.classList.add('resizing')
  bridge.value.window_start_resize(edge)
}

function togglePortDropdown() {
  portDropdownOpen.value = !portDropdownOpen.value
}

function closePortDropdown() {
  portDropdownOpen.value = false
}

function selectPort(item) {
  if (!item || noPorts.value) return
  selectedPort.value = item
  channelMode.value = 'serial'
  closePortDropdown()
}

function handlePortDropdownClick(event) {
  if (!portDropdownRef.value || !event) return
  if (!portDropdownRef.value.contains(event.target)) {
    closePortDropdown()
  }
}

function handlePortDropdownKeydown(event) {
  if (!event) return
  if (event.key === 'Escape') {
    closePortDropdown()
  }
}

function updateSnapPreview(event) {
  if (!draggingWindow.value || !event) return
  if (event.buttons !== 1) {
    snapPreview.value = ''
    return
  }
  if (!enableSnapPreview.value) {
    snapPreview.value = ''
    return
  }
  const margin = 24
  const x = event.clientX
  const y = event.clientY
  const width = window.innerWidth
  if (y <= margin) {
    snapPreview.value = 'max'
  } else if (x <= margin) {
    snapPreview.value = 'left'
  } else if (x >= width - margin) {
    snapPreview.value = 'right'
  } else {
    snapPreview.value = ''
  }
}

function handleDragEnd(event) {
  if (!draggingWindow.value) return
  applyWindowSnap(event)
}

function attachDragListeners() {
  window.addEventListener('mousemove', updateSnapPreview)
  window.addEventListener('mouseup', handleDragEnd)
  window.addEventListener('blur', handleDragCancel)
  document.addEventListener('visibilitychange', handleDragCancel)
}

function detachDragListeners() {
  window.removeEventListener('mousemove', updateSnapPreview)
  window.removeEventListener('mouseup', handleDragEnd)
  window.removeEventListener('blur', handleDragCancel)
  document.removeEventListener('visibilitychange', handleDragCancel)
}

function handleDragCancel() {
  clearDragState()
}

function clearDragState() {
  draggingWindow.value = false
  dragArmed.value = false
  dragStarted.value = false
  snapPreview.value = ''
  document.body.classList.remove('resizing')
  detachDragListeners()
}

</script>

<template>
  <div class="app">
    <div class="resize-handle top" @mousedown.stop="startResize('top', $event)"></div>
    <div class="resize-handle bottom" @mousedown.stop="startResize('bottom', $event)"></div>
    <div class="resize-handle left" @mousedown.stop="startResize('left', $event)"></div>
    <div class="resize-handle right" @mousedown.stop="startResize('right', $event)"></div>
    <div class="resize-handle top-left" @mousedown.stop="startResize('top-left', $event)"></div>
    <div class="resize-handle top-right" @mousedown.stop="startResize('top-right', $event)"></div>
    <div class="resize-handle bottom-left" @mousedown.stop="startResize('bottom-left', $event)"></div>
    <div class="resize-handle bottom-right" @mousedown.stop="startResize('bottom-right', $event)"></div>

    <header
      class="app-titlebar"
      @dblclick="toggleMaximize"
      @mousedown.left="armWindowMove"
      @mousemove="maybeStartWindowMove"
      @mouseup.left="applyWindowSnap"
      @contextmenu.prevent="showSystemMenu"
    >
      <button
        class="app-icon"
        type="button"
        @mousedown.stop
        @dblclick.stop
        @click.stop="showSystemMenu"
      >
        <span class="app-icon-dot"></span>
      </button>
      <div class="app-title">ProtoFlow</div>
      <div class="title-actions">
        <button
          class="title-btn"
          type="button"
          @mousedown.stop
          @dblclick.stop
          @click.stop="minimizeWindow"
        >
          <span class="material-symbols-outlined">minimize</span>
        </button>
        <button
          class="title-btn"
          type="button"
          @mousedown.stop
          @dblclick.stop
          @click.stop="toggleMaximize"
        >
          <span class="material-symbols-outlined">crop_square</span>
        </button>
        <button
          class="title-btn close"
          type="button"
          @mousedown.stop
          @dblclick.stop
          @click.stop="closeWindow"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </header>

    <div class="app-shell">
      <aside class="sidebar">
        <div class="sidebar-header">
          <div class="brand-mark">
            <span class="material-symbols-outlined">hub</span>
          </div>
          <div>
            <div class="brand-name">ProtoFlow</div>
            <div class="brand-meta">v2.4.0-stable</div>
          </div>
        </div>
        <nav class="sidebar-nav">
          <button class="nav-item" :class="{ active: currentView === 'manual' }" @click="currentView = 'manual'">
            <span class="material-symbols-outlined">terminal</span>
            <span>手动脚本</span>
          </button>
          <button class="nav-item" :class="{ active: currentView === 'scripts' }" @click="currentView = 'scripts'">
            <span class="material-symbols-outlined">smart_toy</span>
            <span>自动脚本</span>
          </button>
          <button class="nav-item" :class="{ active: currentView === 'channels' }" @click="currentView = 'channels'">
            <span class="material-symbols-outlined">cloud_queue</span>
            <span>通道</span>
          </button>
          <button class="nav-item" :class="{ active: currentView === 'protocols' }" @click="currentView = 'protocols'">
            <span class="material-symbols-outlined">cable</span>
            <span>协议</span>
          </button>
          <div class="nav-divider"></div>
          <button class="nav-item" :class="{ active: currentView === 'settings' }" @click="currentView = 'settings'">
            <span class="material-symbols-outlined">settings</span>
            <span>设置</span>
          </button>
        </nav>
        <div class="sidebar-footer">
          <div class="user-avatar"></div>
          <div>
            <div class="user-name">DevUser_01</div>
            <div class="user-meta">管理员工作区</div>
          </div>
        </div>
      </aside>

      <main class="main">
        <section v-if="currentView === 'manual'" class="page">
          <header class="page-header">
            <div>
              <h2>手动脚本</h2>
              <p>单步调试指令发送与 I/O 数据流实时监控。</p>
            </div>
            <div class="header-actions">
              <div class="status-indicator" :class="connectionInfo.state">
                <span class="dot"></span>
                {{ isConnected ? '已连接' : connectionInfo.state === 'error' ? '错误' : '未连接' }}
              </div>
              <div class="select-wrap" ref="portDropdownRef">
                <button class="select-trigger" type="button" @click.stop="togglePortDropdown">
                  <span class="material-symbols-outlined">usb</span>
                  <span class="select-value">{{ selectedPortLabel }}</span>
                  <span class="material-symbols-outlined expand">expand_more</span>
                </button>
                <div v-if="portDropdownOpen" class="select-menu" @click.stop>
                  <button
                    v-for="item in portOptions"
                    :key="item"
                    class="select-option"
                    :class="{ selected: item === selectedPort }"
                    type="button"
                    :disabled="noPorts"
                    @click="selectPort(item)"
                  >
                    <span class="material-symbols-outlined">usb</span>
                    <span>{{ item }}</span>
                  </button>
                </div>
              </div>
              <button class="icon-btn" type="button" title="刷新串口" @click="refreshPorts">
                <span class="material-symbols-outlined">refresh</span>
              </button>
              <button class="btn btn-success" @click="isConnected ? disconnect() : connectSerial()">
                <span class="material-symbols-outlined">link</span>
                {{ isConnected ? '断开' : '连接' }}
              </button>
            </div>
          </header>

          <div class="manual-grid">
            <div class="manual-left">
              <div class="panel stack manual-send">
                <div class="panel-title">
                  <span class="material-symbols-outlined">send</span>
                  发送数据
                  <div class="segmented">
                    <button :class="{ active: sendMode === 'text' }" @click="sendMode = 'text'">Text</button>
                    <button :class="{ active: sendMode === 'hex' }" @click="sendMode = 'hex'">HEX</button>
                  </div>
                </div>
                <textarea
                  v-if="sendMode === 'text'"
                  v-model="sendText"
                  class="text-area"
                  placeholder="输入要发送的数据..."
                ></textarea>
                <textarea
                  v-else
                  v-model="sendHex"
                  class="text-area"
                  placeholder="55 AA 01"
                ></textarea>
                <div class="toggle-row">
                  <label class="check">
                    <input v-model="appendCR" type="checkbox" />
                    <span>+CR</span>
                  </label>
                  <label class="check">
                    <input v-model="appendLF" type="checkbox" />
                    <span>+LF</span>
                  </label>
                  <label class="check">
                    <input v-model="loopSend" type="checkbox" />
                    <span>循环发送</span>
                  </label>
                </div>
                <button class="btn btn-primary" @click="sendPayload">
                  <span class="material-symbols-outlined">send</span>
                  发送
                </button>
              </div>

              <div class="panel stack manual-quick">
                <div class="panel-title simple">
                  快捷指令
                  <button class="icon-btn">
                    <span class="material-symbols-outlined">add</span>
                  </button>
                </div>
                <div class="quick-list">
                  <button
                    v-for="cmd in quickCommands"
                    :key="cmd"
                    class="quick-item"
                    @click="sendQuickCommand(cmd)"
                  >
                    <span>{{ cmd }}</span>
                    <span class="material-symbols-outlined">play_arrow</span>
                  </button>
                </div>
              </div>
            </div>

            <div class="manual-right">
              <div class="panel monitor manual-monitor">
                <div class="panel-title bar">
                  <div class="panel-title-left">
                    <span class="material-symbols-outlined">swap_horiz</span>
                    IO 监控
                    <span class="pill live">LIVE</span>
                  </div>
                  <div class="panel-actions">
                    <div class="segmented small">
                      <button :class="{ active: displayMode === 'ascii' }" @click="displayMode = 'ascii'">ASCII</button>
                      <button :class="{ active: displayMode === 'hex' }" @click="displayMode = 'hex'">HEX</button>
                    </div>
                    <span class="divider"></span>
                    <button class="icon-btn" title="清除">
                      <span class="material-symbols-outlined">delete</span>
                    </button>
                    <button class="icon-btn" title="暂停">
                      <span class="material-symbols-outlined">pause_circle</span>
                    </button>
                    <button class="icon-btn" title="导出">
                      <span class="material-symbols-outlined">download</span>
                    </button>
                  </div>
                </div>
                <div class="log-stream">
                  <div class="log-line" v-for="(item, index) in commLogs" :key="`io-${index}`">
                    <span class="log-time">{{ formatTime(item.ts) }}</span>
                    <span class="log-kind" :class="`kind-${item.kind?.toLowerCase()}`">{{ item.kind }}</span>
                    <span class="log-text">{{ formatPayload(item) }}</span>
                  </div>
                </div>
              </div>

              <div class="panel console manual-console">
                <div class="tab-strip">
                  <button :class="{ active: logTab === 'all' }" @click="logTab = 'all'">全部日志</button>
                  <button :class="{ active: logTab === 'uart' }" @click="logTab = 'uart'">串口 (UART)</button>
                  <button :class="{ active: logTab === 'tcp' }" @click="logTab = 'tcp'">网络 (TCP)</button>
                  <button :class="{ active: logTab === 'script' }" @click="logTab = 'script'">脚本引擎</button>
                  <div class="search">
                    <span class="material-symbols-outlined">search</span>
                    <input v-model="logKeyword" type="text" placeholder="过滤日志..." />
                  </div>
                </div>
                <div class="log-stream compact">
                  <div
                    v-for="(line, index) in (logTab === 'uart' ? uartLogs : logTab === 'tcp' ? tcpLogs : logTab === 'script' ? scriptViewLogs : consoleLogs)"
                    :key="`console-${index}`"
                    class="log-line"
                  >
                    <template v-if="typeof line === 'string'">
                      {{ line }}
                    </template>
                    <template v-else>
                      <span class="log-time">{{ formatTime(line.ts) }}</span>
                      <span class="log-kind" :class="`kind-${line.kind?.toLowerCase()}`">{{ line.kind }}</span>
                      <span class="log-text">{{ formatPayload(line) }}</span>
                    </template>
                  </div>
                </div>
                <div class="panel-footer">
                  <span>{{ consoleLogs.length }} 条日志记录</span>
                  <button class="link-btn">清除日志</button>
                </div>
              </div>
            </div>
          </div>
        </section>

<section v-else-if="currentView === 'scripts'" class="page">
          <header class="page-header compact">
            <div class="file-info">
              <div class="file-title">
                production_test_suite_v2.yaml
                <span class="badge">READ-ONLY</span>
              </div>
              <div class="file-path">/usr/local/scripts/auto/prod/...</div>
            </div>
            <div class="header-actions">
              <button class="btn btn-outline" @click="loadYaml">
                <span class="material-symbols-outlined">folder_open</span>
                加载脚本
              </button>
              <button class="btn btn-outline" @click="saveYaml">
                <span class="material-symbols-outlined">save</span>
                保存
              </button>
            </div>
          </header>

          <div class="scripts-grid">
            <div class="panel editor">
              <div class="panel-title bar">
                <span class="material-symbols-outlined">code</span>
                DSL Editor
                <div class="panel-actions">
                  <button class="icon-btn"><span class="material-symbols-outlined">content_copy</span></button>
                  <button class="icon-btn"><span class="material-symbols-outlined">search</span></button>
                </div>
              </div>
              <textarea v-model="yamlText" class="code-area"></textarea>
            </div>

            <div class="scripts-side">
              <div class="panel stack">
                <div class="panel-title simple">执行控制</div>
                <div class="status-pill">
                  <span class="pulse"></span>
                  运行中
                </div>
                <div class="button-grid">
                  <button class="btn btn-primary" @click="runScript">
                    <span class="material-symbols-outlined">play_arrow</span>
                    运行
                  </button>
                  <button class="btn btn-danger" @click="stopScript">
                    <span class="material-symbols-outlined">stop</span>
                    停止
                  </button>
                </div>
                <div class="progress-block">
                  <div class="progress-row">
                    <span>当前步骤: <strong>{{ scriptState }}</strong></span>
                    <span class="mono">{{ Math.round(scriptProgress / 25) }}/4</span>
                  </div>
                  <div class="progress-bar">
                    <div class="progress" :style="{ width: `${Math.min(100, scriptProgress)}%` }"></div>
                  </div>
                  <div class="progress-stats">
                    <div>
                      <span>已用时间</span>
                      <strong class="mono">00:04.2</strong>
                    </div>
                    <div>
                      <span>错误数</span>
                      <strong class="mono">0</strong>
                    </div>
                  </div>
                </div>
              </div>

              <div class="panel stack">
                <div class="panel-title simple">
                  变量监控
                  <button class="link-btn" type="button">刷新</button>
                </div>
                <table class="mini-table">
                  <thead>
                    <tr>
                      <th>变量名</th>
                      <th class="right">当前值</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>target_host</td>
                      <td class="right primary">192.168.1.50</td>
                    </tr>
                    <tr>
                      <td>port</td>
                      <td class="right">5020</td>
                    </tr>
                    <tr>
                      <td>_last_recv</td>
                      <td class="right green">"ACK_0x01"</td>
                    </tr>
                    <tr>
                      <td>status</td>
                      <td class="right">"WAITING"</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div class="panel log-panel">
            <div class="panel-title bar">
              <span class="material-symbols-outlined">terminal</span>
              运行日志
              <div class="panel-actions">
                <button class="icon-btn" title="Clear Logs">
                  <span class="material-symbols-outlined">block</span>
                </button>
                <button class="icon-btn" title="Scroll to Bottom">
                  <span class="material-symbols-outlined">vertical_align_bottom</span>
                </button>
              </div>
            </div>
            <div class="log-stream compact">
              <div class="log-line" v-for="(line, index) in scriptLogs" :key="`${line}-${index}`">
                {{ line }}
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="currentView === 'channels'" class="page">
          <header class="page-header spaced">
            <div>
              <h2>通道管理</h2>
              <p>管理通信连接通道，监控实时状态及配置参数。</p>
            </div>
            <div class="header-actions">
              <button class="btn btn-outline">
                <span class="material-symbols-outlined">refresh</span>
                刷新状态
              </button>
              <button class="btn btn-primary">
                <span class="material-symbols-outlined">add</span>
                新建通道
              </button>
            </div>
          </header>
          <div class="tab-strip secondary">
            <button class="active">全部通道</button>
            <button>串口 (Serial)</button>
            <button>TCP 客户端</button>
            <button>TCP 服务端</button>
          </div>
          <div class="card-list">
            <div v-for="card in channelCards" :key="card.id" class="card">
              <div class="card-main">
                <div class="card-icon">
                  <span class="material-symbols-outlined">settings_input_hdmi</span>
                </div>
                <div>
                  <div class="card-title">
                    {{ card.name }}
                    <span class="chip">{{ card.type }}</span>
                  </div>
                  <div class="card-meta">
                    <span>{{ card.details[0] }}</span>
                    <span class="dot"></span>
                    <span>{{ card.details[1] }}</span>
                  </div>
                </div>
              </div>
              <div class="card-side">
                <div class="traffic">
                  <span>Traffic</span>
                  <strong>{{ card.traffic }}</strong>
                </div>
                <div class="status" :class="card.statusClass">
                  <span class="dot"></span>
                  {{ card.statusText }}
                </div>
                <button class="icon-btn">
                  <span class="material-symbols-outlined">more_vert</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="currentView === 'protocols'" class="page">
          <header class="page-header spaced">
            <div>
              <h2>协议管理</h2>
              <p>配置通信协议定义，绑定通道并设定解析规则。</p>
            </div>
            <div class="header-actions">
              <button class="btn btn-primary">
                <span class="material-symbols-outlined">add</span>
                新建协议
              </button>
            </div>
          </header>
          <div class="tab-strip secondary">
            <button class="active">全部协议</button>
            <button>Modbus</button>
            <button>TCP/IP</button>
            <button>自定义</button>
          </div>
          <div class="protocol-grid">
            <div v-for="card in protocolCards" :key="card.id" class="protocol-card">
              <div class="protocol-header">
                <div>
                  <div class="protocol-title">{{ card.name }}</div>
                  <div class="protocol-sub">{{ card.desc }}</div>
                </div>
                <span class="badge" :class="card.statusClass">{{ card.statusText }}</span>
              </div>
              <div class="protocol-rows">
                <div v-for="row in card.rows" :key="row.label" class="protocol-row">
                  <span>{{ row.label }}</span>
                  <strong>{{ row.value }}</strong>
                </div>
              </div>
              <div class="protocol-actions">
                <button class="btn btn-ghost">配置</button>
                <button class="btn btn-ghost">监控</button>
                <button class="icon-btn">
                  <span class="material-symbols-outlined">more_horiz</span>
                </button>
              </div>
            </div>
            <div class="protocol-card empty">
              <div class="empty-icon">
                <span class="material-symbols-outlined">add</span>
              </div>
              <h3>从模板创建</h3>
              <p>使用预设的 Modbus、MQTT 或 TCP 模板快速开始。</p>
            </div>
          </div>
        </section>

        <section v-else class="page">
          <header class="page-header spaced">
            <div>
              <h2>应用设置</h2>
              <p>管理全局偏好、协议默认值和运行时环境配置。</p>
            </div>
            <div class="header-actions">
              <button class="btn btn-outline">放弃更改</button>
              <button class="btn btn-primary">
                <span class="material-symbols-outlined">save</span>
                保存更改
              </button>
            </div>
          </header>
          <div class="tab-strip secondary">
            <button class="active">通用</button>
            <button>网络与端口</button>
            <button>插件</button>
            <button>运行时</button>
            <button>日志</button>
          </div>

          <div class="settings-stack">
            <div class="panel">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">tune</span>
                通用偏好
              </div>
              <div class="form-grid">
                <label>
                  界面语言
                  <select>
                    <option>英语 (美国)</option>
                    <option>德语</option>
                    <option>日语</option>
                    <option selected>简体中文</option>
                  </select>
                </label>
                <label>
                  主题偏好
                  <select>
                    <option>系统默认</option>
                    <option>深色 (工程模式)</option>
                    <option selected>浅色</option>
                  </select>
                </label>
              </div>
              <div class="toggle-row spaced">
                <div>
                  <strong>启动时自动连接</strong>
                  <p>自动尝试重新连接上次活动的通道。</p>
                </div>
                <label class="switch">
                  <input type="checkbox" />
                  <span></span>
                </label>
              </div>
            </div>

            <div class="panel">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">router</span>
                通信默认设置
              </div>
              <div class="section-title">TCP / IP 配置</div>
              <div class="form-grid triple">
                <label>
                  默认超时 (ms)
                  <input type="number" value="5000" />
                </label>
                <label>
                  保活间隔 (s)
                  <input type="number" value="60" />
                </label>
                <label>
                  重试次数
                  <input type="number" value="3" />
                </label>
              </div>
              <div class="divider"></div>
              <div class="section-title">串口配置</div>
              <div class="form-grid triple">
                <label>
                  默认波特率
                  <select>
                    <option>9600</option>
                    <option>19200</option>
                    <option>38400</option>
                    <option>57600</option>
                    <option selected>115200</option>
                  </select>
                </label>
                <label>
                  校验位
                  <select>
                    <option selected>无</option>
                    <option>偶校验</option>
                    <option>奇校验</option>
                    <option>标记校验</option>
                    <option>空格校验</option>
                  </select>
                </label>
                <label>
                  停止位
                  <select>
                    <option selected>1</option>
                    <option>1.5</option>
                    <option>2</option>
                  </select>
                </label>
              </div>
            </div>

            <div class="panel">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">extension</span>
                DSL 与插件
              </div>
              <label class="file-row">
                工作流定义目录
                <div class="file-input">
                  <span class="material-symbols-outlined">folder_open</span>
                  <input type="text" readonly value="/usr/local/protoflow/workflows" />
                </div>
                <button class="btn btn-outline">浏览</button>
              </label>
              <div class="divider"></div>
              <div class="panel-title simple inline">
                已安装插件
                <button class="link-btn">
                  <span class="material-symbols-outlined">refresh</span>
                  检查更新
                </button>
              </div>
              <div class="plugin-list">
                <div class="plugin-item">
                  <div>
                    <div class="plugin-title">Modbus TCP/RTU</div>
                    <div class="plugin-meta">v1.2.4 - 核心</div>
                  </div>
                  <span class="badge badge-green">已激活</span>
                </div>
                <div class="plugin-item muted">
                  <div>
                    <div class="plugin-title">MQTT 桥接</div>
                    <div class="plugin-meta">v0.9.8 - 社区版</div>
                  </div>
                  <span class="badge badge-gray">未激活</span>
                </div>
              </div>
              <div class="toggle-row spaced">
                <div>
                  <strong>严格 Lint 模式</strong>
                  <p>拒绝包含已弃用语法警告的工作流。</p>
                </div>
                <label class="switch">
                  <input type="checkbox" checked />
                  <span></span>
                </label>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>

    <div v-if="snapPreview" class="snap-overlay" :class="`snap-${snapPreview}`"></div>
  </div>
</template>
