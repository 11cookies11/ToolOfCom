<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { basicSetup } from 'codemirror'
import { EditorState, RangeSetBuilder } from '@codemirror/state'
import { Decoration, EditorView, ViewPlugin } from '@codemirror/view'
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags } from '@lezer/highlight'
import DropdownSelect from './components/DropdownSelect.vue'
import { yaml as yamlLanguage } from '@codemirror/lang-yaml'

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
const scriptFileName = ref('production_test_suite_v2.yaml')
const scriptFilePath = ref('/usr/local/scripts/auto/prod/...')
const scriptRunning = ref(false)
const scriptStartMs = ref(0)
const scriptElapsedMs = ref(0)
const scriptVarRefreshKey = ref(0)
const yamlFileInputRef = ref(null)
const scriptLogRef = ref(null)
const scriptAutoScroll = ref(true)
const yamlCollapsed = ref(true)
const yamlEditorRef = ref(null)
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
const portPlaceholder = 'COM3 - USB Serial (115200)'
const channelDialogOpen = ref(false)
const channelType = ref('serial')
const channelName = ref('')
const channelPort = ref('')
const channelBaud = ref(115200)
const channelDataBits = ref('8')
const channelParity = ref('none')
const channelStopBits = ref('1')
const channelHost = ref('127.0.0.1')
const channelTcpPort = ref(502)
const channelAutoConnect = ref(true)
const uiLanguage = ref('????')
const uiTheme = ref('娴呰壊')
const defaultBaud = ref(115200)
const defaultParity = ref('none')
const defaultStopBits = ref('1')
const tcpTimeoutMs = ref(5000)
const tcpHeartbeatSec = ref(60)
const tcpRetryCount = ref(3)
const dslWorkspacePath = ref('/usr/local/protoflow/workflows')
const autoConnectOnStart = ref(true)
const settingsSaving = ref(false)
const settingsSnapshot = ref(null)
const channelTab = ref('all')
const protocolTab = ref('all')
const settingsTab = ref('general')
const settingsGeneralRef = ref(null)
const settingsNetworkRef = ref(null)
const settingsPluginsRef = ref(null)
const settingsRuntimeRef = ref(null)
const settingsLogsRef = ref(null)

const noPorts = computed(() => ports.value.length === 0)
const portOptionsList = computed(() => ports.value.map((item) => ({ label: item, value: item, icon: 'usb' })))

const quickCommands = ref([
  'AT+GMR',
  'RESET_DEVICE_01',
  'GET_WIFI_STATUS',
  'PING_SERVER',
])

const channels = ref([])
const channelCards = computed(() => {
  return channels.value.map((channel) => {
    const type = channel.type || 'unknown'
    const status = channel.status || 'disconnected'
    const statusMap = {
      connected: { text: '已连接', className: 'status-ok' },
      connecting: { text: '连接中', className: 'status-warn' },
      error: { text: '错误', className: 'status-error' },
      disconnected: { text: '未连接', className: 'status-idle' },
      idle: { text: '空闲', className: 'status-idle' },
    }
    const statusInfo = statusMap[status] || statusMap.disconnected
    const isSerial = type === 'serial'
    const isTcpClient = type === 'tcp-client'
    const name = isSerial ? '串口通道' : isTcpClient ? 'TCP 客户端' : 'TCP 服务端'
    const details = isSerial
      ? [channel.port || '--', channel.baud ? `${channel.baud} bps` : '--']
      : [channel.host || channel.address || '--', channel.port ? `端口: ${channel.port}` : '--']
    const traffic = `TX: ${formatBytes(channel.tx_bytes || 0)} / RX: ${formatBytes(channel.rx_bytes || 0)}`
    return {
      id: channel.id || `${type}:${details[0]}`,
      name,
      type: isSerial ? 'Serial' : isTcpClient ? 'TCP Client' : 'TCP Server',
      category: type,
      statusText: statusInfo.text,
      statusClass: statusInfo.className,
      details,
      traffic,
      error: channel.error || '',
    }
  })
})

const protocolCards = ref([])

const isConnected = computed(() => connectionInfo.value.state === 'connected')

const consoleLogs = computed(() => filterLogs(commLogs.value))
const uartLogs = computed(() => filterLogs(commLogs.value))
const tcpLogs = computed(() => filterLogs([]))
const scriptViewLogs = computed(() => filterLogs(scriptLogs.value))
const scriptVariables = computed(() => {
  scriptVarRefreshKey.value
  return parseScriptVariables(yamlText.value)
})
const scriptErrorCount = computed(
  () => scriptLogs.value.filter((line) => String(line || '').toLowerCase().includes('[error]')).length
)
const scriptStepTotal = computed(() => countScriptSteps(yamlText.value))
const scriptStepIndex = computed(() => {
  if (!scriptStepTotal.value) return 0
  return Math.max(
    0,
    Math.min(scriptStepTotal.value, Math.round((scriptProgress.value / 100) * scriptStepTotal.value))
  )
})
const scriptElapsedLabel = computed(() => formatElapsed(scriptElapsedMs.value))
const scriptCanRun = computed(() => !scriptRunning.value && yamlText.value.trim().length > 0)
const scriptCanStop = computed(() => scriptRunning.value)
const scriptStatusLabel = computed(() => {
  if (scriptRunning.value) {
    return scriptState.value ? '运行中 ' + scriptState.value : '运行中'
  }
  return '空闲'
})
const scriptStatusClass = computed(() => (scriptRunning.value ? 'running' : 'idle'))

const filteredChannelCards = computed(() => {
  if (channelTab.value === 'all') return channelCards.value
  return channelCards.value.filter((card) => card.category === channelTab.value)
})
const filteredProtocolCards = computed(() => {
  if (protocolTab.value === 'all') return protocolCards.value
  return protocolCards.value.filter((card) => card.category === protocolTab.value)
})

let scriptTimer = null
let yamlEditor = null
let yamlEditorUpdating = false

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

function formatElapsed(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  const tenths = Math.floor((ms % 1000) / 100)
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${tenths}`
}

function formatBytes(value) {
  const bytes = Number(value) || 0
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  const gb = mb / 1024
  return `${gb.toFixed(1)} GB`
}

function countScriptSteps(text) {
  if (!text) return 0
  const matches = text.match(/^\s*-\s*step\s*:/gm)
  return matches ? matches.length : 0
}

function parseScriptVariables(text) {
  if (!text) return []
  const lines = text.split(/\r?\n/)
  const vars = []
  let inVars = false
  for (const line of lines) {
    if (!inVars) {
      if (/^\s*variables\s*:\s*$/.test(line)) {
        inVars = true
      }
      continue
    }
    if (!line.trim()) continue
    if (!/^\s+/.test(line)) break
    const match = line.match(/^\s+([A-Za-z0-9_-]+)\s*:\s*(.*)$/)
    if (!match) continue
    let value = match[2].trim()
    value = value.replace(/^['"]|['"]$/g, '')
    vars.push({ name: match[1], value })
  }
  return vars
}

function initYamlEditor() {
  if (!yamlEditorRef.value || yamlEditor) return
  if (yamlEditorRef.value) {
    yamlEditorRef.value.style.height = yamlCollapsed.value ? '360px' : '640px'
  }
  const theme = EditorView.theme(
    {
      '&': {
        height: '100%',
        backgroundColor: '#fafafa',
        fontFamily:
          'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
        fontSize: '13px',
      },
      '.cm-scroller': {
        overflow: 'auto',
      },
      '.cm-content': {
        padding: '16px',
      },
      '.cm-gutters': {
        backgroundColor: '#f8fafc',
        borderRight: '1px solid #e2e8f0',
      },
      '.cm-lineNumbers': {
        color: '#94a3b8',
      },
      '.cm-activeLine': {
        backgroundColor: '#eef2ff',
      },
      '.cm-activeLineGutter': {
        backgroundColor: '#e0e7ff',
      },
    },
    { dark: false }
  )
  const indentPlugin = ViewPlugin.fromClass(
    class {
      constructor(view) {
        this.decorations = this.build(view)
      }
      update(update) {
        if (update.docChanged || update.viewportChanged) {
          this.decorations = this.build(update.view)
        }
      }
      build(view) {
        const builder = new RangeSetBuilder()
        for (const { from, to } of view.visibleRanges) {
          let pos = from
          while (pos <= to) {
            const line = view.state.doc.lineAt(pos)
            const indentMatch = line.text.match(/^\s+/)
            const indent = indentMatch ? indentMatch[0].length : 0
            const level = Math.min(5, Math.floor(indent / 2) + 1)
            builder.add(line.from, line.from, Decoration.line({ class: `yaml-indent-${level}` }))
            pos = line.to + 1
          }
        }
        return builder.finish()
      }
    },
    {
      decorations: (value) => value.decorations,
    }
  )
  const state = EditorState.create({
    doc: yamlText.value,
    extensions: [
      basicSetup,
      yamlLanguage(),
      syntaxHighlighting(
        HighlightStyle.define([
          { tag: tags.keyword, color: '#1d4ed8' },
          { tag: tags.atom, color: '#1d4ed8' },
          { tag: tags.string, color: '#16a34a' },
          { tag: tags.number, color: '#f97316' },
          { tag: tags.bool, color: '#1d4ed8' },
          { tag: tags.comment, color: '#94a3b8', fontStyle: 'italic' },
          { tag: tags.punctuation, color: '#64748b' },
        ])
      ),
      theme,
      EditorView.lineWrapping,
      indentPlugin,
      EditorView.updateListener.of((update) => {
        if (!update.docChanged) return
        yamlEditorUpdating = true
        yamlText.value = update.state.doc.toString()
        yamlEditorUpdating = false
      }),
    ],
  })
  yamlEditor = new EditorView({
    state,
    parent: yamlEditorRef.value,
  })
}

function destroyYamlEditor() {
  if (!yamlEditor) return
  yamlEditor.destroy()
  yamlEditor = null
}

function toggleYamlCollapsed() {
  yamlCollapsed.value = !yamlCollapsed.value
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
  const text = String(line || '')
  scriptLogs.value.push(text)
  if (scriptLogs.value.length > 200) scriptLogs.value.shift()
  if (
    text.includes('Script finished') ||
    text.includes('Script stopped') ||
    text.toLowerCase().includes('[error]')
  ) {
    scriptRunning.value = false
    scriptState.value = 'idle'
  }
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

function setChannels(items) {
  channels.value = Array.isArray(items) ? items : []
}

function refreshChannels() {
  if (!bridge.value || !bridge.value.list_channels) return
  withResult(bridge.value.list_channels(), (items) => {
    setChannels(items)
  })
}

function protocolCategory(key) {
  const name = String(key || "").toLowerCase()
  if (name.startsWith("modbus_")) return "modbus"
  if (name.includes("tcp")) return "tcp"
  return "custom"
}

function prettyProtocolName(key, fallback) {
  const value = String(key || "").trim()
  if (!value) return fallback || "协议"
  const parts = value.split("_").map((part) => {
    const upper = part.toUpperCase()
    if (["RTU", "TCP", "SCPI", "AT", "XMODEM", "YMODEM"].includes(upper)) return upper
    if (upper.length <= 2) return upper
    return part.charAt(0).toUpperCase() + part.slice(1)
  })
  return parts.join(" ")
}

function setProtocols(items) {
  const list = Array.isArray(items) ? items : []
  protocolCards.value = list.map((item) => {
    const key = String(item.key || item.id || "")
    const driver = String(item.driver || item.name || "")
    const category = String(item.category || protocolCategory(key))
    const status = String(item.status || "available")
    const desc = String(item.desc || "暂无描述")
    return {
      id: key || driver || Math.random().toString(36).slice(2),
      name: prettyProtocolName(key, driver),
      category,
      desc,
      statusText: status === "available" ? "可用" : status,
      statusClass: status === "available" ? "badge-green" : "badge-gray",
      rows: [
        { label: "键名", value: key || "--" },
        { label: "驱动", value: driver || "--" },
        { label: "分类", value: category || "--" },
      ],
    }
  })
}

function refreshProtocols() {
  if (!bridge.value || !bridge.value.list_protocols) return
  withResult(bridge.value.list_protocols(), (items) => {
    setProtocols(items)
  })
}


function handleChannelRefresh() {
  refreshChannels()
  refreshPorts()
}

function handleNewChannel() {
  channelType.value = 'serial'
  channelName.value = ''
  channelPort.value = selectedPort.value || ports.value[0] || ''
  channelBaud.value = Number(defaultBaud.value || 115200)
  channelDataBits.value = '8'
  channelParity.value = defaultParity.value || 'none'
  channelStopBits.value = defaultStopBits.value || '1'
  channelHost.value = tcpHost.value || '127.0.0.1'
  channelTcpPort.value = Number(tcpPort.value || 502)
  channelAutoConnect.value = !!autoConnectOnStart.value
  channelDialogOpen.value = true
}

function closeChannelDialog() {
  channelDialogOpen.value = false
}

function submitChannelDialog() {
  if (!bridge.value) return
  if (channelType.value === 'serial') {
    if (channelAutoConnect.value) {
      bridge.value.connect_serial(channelPort.value, Number(channelBaud.value || 115200))
    }
  } else if (channelType.value === 'tcp') {
    if (channelAutoConnect.value) {
      bridge.value.connect_tcp(channelHost.value, Number(channelTcpPort.value || 502))
    }
  }
  channelDialogOpen.value = false
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
  if (!bridge.value) return
  const payload = yamlText.value.trim()
  if (!payload) {
    addScriptLog('[WARN] YAML is empty, abort run.')
    return
  }
  scriptRunning.value = true
  scriptState.value = 'starting'
  scriptStartMs.value = Date.now()
  scriptElapsedMs.value = 0
  scriptProgress.value = 0
  bridge.value.run_script(payload)
}

function stopScript() {
  if (!bridge.value) return
  scriptState.value = 'stopping'
  bridge.value.stop_script()
  addScriptLog('[INFO] Stop requested.')
}

function loadYaml() {
  if (bridge.value && bridge.value.load_yaml) {
    withResult(bridge.value.load_yaml(), (payload) => {
      if (!payload || !payload.text) return
      yamlText.value = payload.text
      scriptFileName.value = payload.name || scriptFileName.value
      scriptFilePath.value = payload.path || scriptFilePath.value
      refreshScriptVariables()
      addScriptLog(`[INFO] Loaded: ${scriptFileName.value}`)
    })
    return
  }
  if (!yamlFileInputRef.value) return
  yamlFileInputRef.value.value = ''
  yamlFileInputRef.value.click()
}

function saveYaml() {
  const payload = yamlText.value.trim()
  if (!payload) {
    addScriptLog('[WARN] YAML is empty, not saved.')
    return
  }
  if (bridge.value && bridge.value.save_yaml) {
    withResult(bridge.value.save_yaml(payload, scriptFileName.value || 'workflow.yaml'), (info) => {
      if (!info) return
      if (info.name) scriptFileName.value = info.name
      if (info.path) scriptFilePath.value = info.path
      addScriptLog(`[INFO] Saved: ${scriptFileName.value}`)
    })
    return
  }
  const name = scriptFileName.value || 'script.yaml'
  const blob = new Blob([payload], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  addScriptLog(`[INFO] Saved: ${name}`)
}

function handleYamlFile(event) {
  const file = event && event.target && event.target.files ? event.target.files[0] : null
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    const text = typeof reader.result === 'string' ? reader.result : ''
    yamlText.value = text
    scriptFileName.value = file.name
    scriptFilePath.value = file.name
    refreshScriptVariables()
    addScriptLog(`[INFO] Loaded: ${file.name}`)
  }
  reader.readAsText(file)
}

async function copyYaml() {
  const payload = yamlText.value.trim()
  if (!payload) {
    addScriptLog('[WARN] YAML is empty, nothing to copy.')
    return
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(payload)
      addScriptLog('[INFO] YAML copied to clipboard.')
      return
    } catch (err) {
      addScriptLog('[WARN] Clipboard API failed, falling back.')
    }
  }
  const temp = document.createElement('textarea')
  temp.value = payload
  document.body.appendChild(temp)
  temp.select()
  document.execCommand('copy')
  temp.remove()
  addScriptLog('[INFO] YAML copied to clipboard.')
}

function searchYaml() {
  const keyword = window.prompt('搜索关键词')
  if (!keyword) return
  if (yamlEditor) {
    const doc = yamlEditor.state.doc.toString()
    const lower = doc.toLowerCase()
    const idx = lower.indexOf(keyword.toLowerCase())
    if (idx === -1) {
      addScriptLog(`[INFO] Not found: ${keyword}`)
      return
    }
    yamlEditor.dispatch({
      selection: { anchor: idx, head: idx + keyword.length },
      scrollIntoView: true,
    })
    return
  }
  const found = window.find(keyword)
  if (!found) {
    addScriptLog(`[INFO] Not found: ${keyword}`)
  }
}

function clearScriptLogs() {
  scriptLogs.value = []
}

function scrollScriptLogsToBottom() {
  if (!scriptLogRef.value) return
  scriptLogRef.value.scrollTop = scriptLogRef.value.scrollHeight
}

function refreshScriptVariables() {
  scriptVarRefreshKey.value += 1
}

function attachBridge(obj) {
  bridge.value = obj
  obj.comm_batch.connect((batch) => addCommBatch(batch))
  obj.comm_status.connect((payload) => {
    const detail = payload && payload.payload !== undefined ? payload.payload : payload
    if (!detail) {
      connectionInfo.value = { state: 'disconnected', detail: '' }
      refreshChannels()
      return
    }
    if (typeof detail === 'string') {
      connectionInfo.value = { state: 'error', detail }
      refreshChannels()
      return
    }
    connectionInfo.value = {
      state: 'connected',
      detail: detail.address || detail.port || detail.type || '',
    }
    refreshChannels()
  })
  obj.script_log.connect((line) => addScriptLog(line))
  obj.script_state.connect((state) => {
    scriptState.value = state
    if (state) {
      scriptRunning.value = true
    }
  })
  obj.script_progress.connect((value) => {
    scriptProgress.value = value
  })
  if (obj.channel_update) {
    obj.channel_update.connect((items) => setChannels(items))
  }
  refreshPorts()
  refreshChannels()
  refreshProtocols()
  loadSettings()
}

onMounted(() => {
  const timer = setInterval(() => {
    if (window.bridge) {
      attachBridge(window.bridge)
      clearInterval(timer)
    }
  }, 200)
  scriptTimer = window.setInterval(() => {
    if (scriptRunning.value && scriptStartMs.value) {
      scriptElapsedMs.value = Date.now() - scriptStartMs.value
    }
  }, 200)
  if (currentView.value === 'scripts') {
    nextTick(() => initYamlEditor())
  }
  window.addEventListener('keydown', handleGlobalKeydown)
  loadSettings()
})

onBeforeUnmount(() => {
  if (scriptTimer) {
    window.clearInterval(scriptTimer)
    scriptTimer = null
  }
  destroyYamlEditor()
  window.removeEventListener('keydown', handleGlobalKeydown)
})

watch(
  () => scriptLogs.value.length,
  async () => {
    if (!scriptAutoScroll.value) return
    await nextTick()
    scrollScriptLogsToBottom()
  }
)

watch(
  () => currentView.value,
  (value) => {
    if (value === 'scripts') {
      nextTick(() => initYamlEditor())
    } else {
      destroyYamlEditor()
    }
    if (value === 'protocols') {
      refreshProtocols()
    }
  }
)

watch(
  () => yamlCollapsed.value,
  (collapsed) => {
    if (yamlEditorRef.value) {
      yamlEditorRef.value.style.height = collapsed ? '360px' : '640px'
    }
  }
)

watch(
  () => channelDialogOpen.value,
  (open) => {
    document.body.classList.toggle('modal-open', open)
  }
)

watch(
  () => yamlText.value,
  (value) => {
    if (!yamlEditor || yamlEditorUpdating) return
    const current = yamlEditor.state.doc.toString()
    if (value === current) return
    yamlEditor.dispatch({
      changes: { from: 0, to: current.length, insert: value },
    })
  }
)

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

function selectPort(item) {
  if (!item || noPorts.value) return
  selectedPort.value = item
  channelMode.value = 'serial'
}
function handleGlobalKeydown(event) {
  if (!event) return
  if (event.key === 'Escape') {
    if (channelDialogOpen.value) {
      closeChannelDialog()
    }
  }
}

function setChannelTab(tab) {
  channelTab.value = tab
}

function setProtocolTab(tab) {
  protocolTab.value = tab
}

function setSettingsTab(tab) {
  settingsTab.value = tab
  const targets = {
    general: settingsGeneralRef,
    network: settingsNetworkRef,
    plugins: settingsPluginsRef,
    runtime: settingsRuntimeRef,
    logs: settingsLogsRef,
  }
  const target = targets[tab]
  if (target && target.value && typeof target.value.scrollIntoView === 'function') {
    target.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}


const settingsDirty = computed(() => {
  if (!settingsSnapshot.value) return false
  return JSON.stringify(buildSettingsPayload()) !== JSON.stringify(settingsSnapshot.value)
})

function buildSettingsPayload() {
  return {
    uiLanguage: uiLanguage.value,
    uiTheme: uiTheme.value,
    autoConnectOnStart: !!autoConnectOnStart.value,
    dslWorkspacePath: dslWorkspacePath.value,
    serial: {
      defaultBaud: Number(defaultBaud.value || 115200),
      defaultParity: defaultParity.value,
      defaultStopBits: defaultStopBits.value,
    },
    network: {
      tcpTimeoutMs: Number(tcpTimeoutMs.value || 0),
      tcpHeartbeatSec: Number(tcpHeartbeatSec.value || 0),
      tcpRetryCount: Number(tcpRetryCount.value || 0),
    },
  }
}

function normalizeSettings(payload) {
  const defaults = {
    uiLanguage: '????',
    uiTheme: '????',
    autoConnectOnStart: true,
    dslWorkspacePath: '/usr/local/protoflow/workflows',
    serial: {
      defaultBaud: 115200,
      defaultParity: 'none',
      defaultStopBits: '1',
    },
    network: {
      tcpTimeoutMs: 5000,
      tcpHeartbeatSec: 60,
      tcpRetryCount: 3,
    },
  }
  if (!payload || typeof payload !== 'object') return defaults
  return {
    ...defaults,
    ...payload,
    serial: {
      ...defaults.serial,
      ...(payload.serial || {}),
    },
    network: {
      ...defaults.network,
      ...(payload.network || {}),
    },
  }
}

function applySettings(payload) {
  const normalized = normalizeSettings(payload)
  uiLanguage.value = normalized.uiLanguage
  uiTheme.value = normalized.uiTheme
  autoConnectOnStart.value = !!normalized.autoConnectOnStart
  dslWorkspacePath.value = normalized.dslWorkspacePath
  defaultBaud.value = Number(normalized.serial.defaultBaud || 115200)
  defaultParity.value = normalized.serial.defaultParity || 'none'
  defaultStopBits.value = normalized.serial.defaultStopBits || '1'
  tcpTimeoutMs.value = Number(normalized.network.tcpTimeoutMs || 0)
  tcpHeartbeatSec.value = Number(normalized.network.tcpHeartbeatSec || 0)
  tcpRetryCount.value = Number(normalized.network.tcpRetryCount || 0)
  baud.value = Number(defaultBaud.value || 115200)
}

function loadSettings() {
  if (bridge.value && bridge.value.load_settings) {
    withResult(bridge.value.load_settings(), (payload) => {
      const normalized = normalizeSettings(payload)
      applySettings(normalized)
      settingsSnapshot.value = normalized
    })
    return
  }
  const normalized = normalizeSettings(null)
  applySettings(normalized)
  settingsSnapshot.value = normalized
}

function saveSettings() {
  const payload = buildSettingsPayload()
  settingsSaving.value = true
  const finalize = () => {
    settingsSnapshot.value = normalizeSettings(payload)
    settingsSaving.value = false
  }
  if (bridge.value && bridge.value.save_settings) {
    withResult(bridge.value.save_settings(payload), () => finalize())
  } else {
    finalize()
  }
}

function discardSettings() {
  if (!settingsSnapshot.value) return
  applySettings(settingsSnapshot.value)
}

function chooseDslWorkspace() {
  if (!bridge.value || !bridge.value.select_directory) return
  withResult(
    bridge.value.select_directory('????', dslWorkspacePath.value || ''),
    (value) => {
      if (value) {
        dslWorkspacePath.value = value
      }
    }
  )
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
              <DropdownSelect
                v-model="selectedPort"
                :options="portOptionsList"
                :placeholder="portPlaceholder"
                :disabled="noPorts"
                leading-icon="usb"
                @change="selectPort"
              />
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
                    <button :class="{ active: sendMode === 'text' }" @click="sendMode = 'text'">文本</button>
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
                  发送数据
                </button>
              </div>

              <div class="panel stack manual-quick">
                <div class="panel-title simple">
                  发送
                  <button class="icon-btn">
                    <span class="material-symbols-outlined">add</span>
                  </button>
                </div>
                <div class="quick-list">
                  <button
                    快捷指令
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
                    <button class="icon-btn" title="娓呴櫎">
                      <span class="material-symbols-outlined">delete</span>
                    </button>
                    <button class="icon-btn" title="鏆傚仠">
                      <span class="material-symbols-outlined">pause_circle</span>
                    </button>
                    <button class="icon-btn" title="瀵煎嚭">
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
                  <div class="search">
                    <span class="material-symbols-outlined">search</span>
                    <input v-model="logKeyword" type="text" placeholder="过滤日志..." />
                  </div>
                </div>
                <div class="log-stream compact">
                  <div
                    v-for="(line, index) in (logTab === 'uart' ? uartLogs : logTab === 'tcp' ? tcpLogs : consoleLogs)"
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
                {{ scriptFileName }}
                <span class="badge">只读</span>
              </div>
              <div class="file-path">{{ scriptFilePath }}</div>
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
            <input
              ref="yamlFileInputRef"
              type="file"
              accept=".yaml,.yml,text/yaml"
              style="display: none"
              @change="handleYamlFile"
            />
          </header>

          <div class="scripts-grid">
            <div class="panel editor">
              <div class="panel-title bar">
                <span class="material-symbols-outlined">code</span>
                DSL 编辑器
                <div class="panel-actions">
                  <button class="icon-btn" :title="yamlCollapsed ? '灞曞紑' : '鏀惰捣'" @click="toggleYamlCollapsed">
                    <span class="material-symbols-outlined">
                      {{ yamlCollapsed ? 'unfold_more' : 'unfold_less' }}
                    </span>
                  </button>
                  <button class="icon-btn" title="复制" @click="copyYaml">
                    <span class="material-symbols-outlined">content_copy</span>
                  </button>
                  <button class="icon-btn" title="搜索" @click="searchYaml">
                    <span class="material-symbols-outlined">search</span>
                  </button>
                </div>
              </div>
              <div ref="yamlEditorRef" class="code-area" :class="{ collapsed: yamlCollapsed }"></div>
            </div>

            <div class="scripts-side">
              <div class="panel stack">
                <div class="panel-title simple">执行控制</div>
                <div class="status-pill" :class="scriptStatusClass">
                  <span v-if="scriptRunning" class="pulse"></span>
                  {{ scriptStatusLabel }}
                </div>
                <div class="button-grid">
                  <button
                    class="btn btn-primary"
                    :class="{ 'btn-muted': !scriptCanRun }"
                    :disabled="!scriptCanRun"
                    @click="runScript"
                  >
                    <span class="material-symbols-outlined">play_arrow</span>
                    运行
                  </button>
                  <button
                    class="btn btn-danger"
                    :class="{ 'btn-muted': !scriptCanStop }"
                    :disabled="!scriptCanStop"
                    @click="stopScript"
                  >
                    <span class="material-symbols-outlined">stop</span>
                    停止
                  </button>
                </div>
                <div class="progress-block">
                  <div class="progress-row">
                    <span>当前步骤: <strong>{{ scriptState }}</strong></span>
                    <span class="mono">{{ scriptStepIndex }}/{{ scriptStepTotal }}</span>
                  </div>
                  <div class="progress-bar">
                    <div class="progress" :style="{ width: `${Math.min(100, scriptProgress)}%` }"></div>
                  </div>
                  <div class="progress-stats">
                    <div>
                      <span>已用时间</span>
                      <strong class="mono">{{ scriptElapsedLabel }}</strong>
                    </div>
                    <div>
                      <span>错误数</span>
                      <strong class="mono">{{ scriptErrorCount }}</strong>
                    </div>
                  </div>
                </div>
              </div>

              <div class="panel stack">
                <div class="panel-title simple">
                  变量监控
                  <button class="link-btn" type="button" @click="refreshScriptVariables">刷新</button>
                </div>
                <table class="mini-table">
                  <thead>
                    <tr>
                      <th>变量名</th>
                      <th class="right">当前值</th>
                    </tr>
                  </thead>
                  <tbody v-if="scriptVariables.length">
                    <tr v-for="item in scriptVariables" :key="item.name">
                      <td>{{ item.name }}</td>
                      <td class="right">{{ item.value || '--' }}</td>
                    </tr>
                  </tbody>
                  <tbody v-else>
                    <tr>
                      <td colspan="2" class="right">--</td>
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
                <button class="icon-btn" title="清空日志" @click="clearScriptLogs">
                  <span class="material-symbols-outlined">block</span>
                </button>
                <button class="icon-btn" title="滚动到底部" @click="scrollScriptLogsToBottom">
                  <span class="material-symbols-outlined">vertical_align_bottom</span>
                </button>
              </div>
            </div>
            <div class="log-stream compact" ref="scriptLogRef">
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
      <p>管理通信连接通道，监控实时状态与配置参数。</p>
    </div>
    <div class="header-actions">
      <button class="btn btn-outline" @click="handleChannelRefresh">
        <span class="material-symbols-outlined">refresh</span>
        刷新状态
      </button>
      <button class="btn btn-primary" @click="handleNewChannel">
        <span class="material-symbols-outlined">add</span>
        新建通道
      </button>
    </div>
  </header>
  <div class="tab-strip secondary">
    <button :class="{ active: channelTab === 'all' }" @click="setChannelTab('all')">全部通道</button>
    <button :class="{ active: channelTab === 'serial' }" @click="setChannelTab('serial')">串口 (Serial)</button>
    <button :class="{ active: channelTab === 'tcp-client' }" @click="setChannelTab('tcp-client')">TCP 客户端</button>
    <button :class="{ active: channelTab === 'tcp-server' }" @click="setChannelTab('tcp-server')">TCP 服务端</button>
  </div>
  <div class="card-list">
            <div v-for="card in filteredChannelCards" :key="card.id" class="card">
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
                  <span>流量</span>
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
            <div v-if="filteredChannelCards.length === 0" class="card empty-card">
              <div class="card-main">
                <div class="card-icon">
                  <span class="material-symbols-outlined">link_off</span>
                </div>
                <div>
                  <div class="card-title">暂无通道</div>
                  <div class="card-meta">
                    <span>未检测到活动连接</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="channelDialogOpen" class="modal-backdrop">
            <div class="channel-modal">
              <div class="modal-header">
                <div>
                  <h3>新建通道</h3>
                  <p>配置新的通信连接参数</p>
                </div>
                <button class="icon-btn" type="button" @click="closeChannelDialog">
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
              <div class="modal-body">
                <div class="channel-type-grid">
                  <button
                    class="channel-type-card"
                    :class="{ active: channelType === 'serial' }"
                    type="button"
                    @click="channelType = 'serial'"
                  >
                    <span class="material-symbols-outlined">settings_input_hdmi</span>
                    <span>串口 (Serial)</span>
                  </button>
                  <button
                    class="channel-type-card"
                    :class="{ active: channelType === 'tcp' }"
                    type="button"
                    @click="channelType = 'tcp'"
                  >
                    <span class="material-symbols-outlined">lan</span>
                    <span>TCP / 网络</span>
                  </button>
                </div>

                <div class="modal-section">
                  <div class="form-grid">
                    <label>
                      通道名称
                      <input v-model="channelName" type="text" placeholder="例如：传感器A接口" />
                    </label>
                    <label v-if="channelType === 'serial'">
                      串口端口
                      <DropdownSelect
                        v-model="channelPort"
                        :options="portOptionsList"
                        :placeholder="ports.length ? '选择串口' : '无可用串口'"
                        :disabled="noPorts"
                        leading-icon="usb"
                      />
                    </label>
                    <label v-else>
                      目标地址
                      <input v-model="channelHost" type="text" placeholder="例如：192.168.1.10" />
                    </label>
                  </div>
                </div>

                <div class="modal-section" v-if="channelType === 'serial'">
                  <div class="form-grid triple">
                    <label>
                      波特率                      <DropdownSelect v-model="channelBaud" :options="[9600, 19200, 38400, 57600, 115200]" />
                    </label>
                    <label>
                      数据位                      <DropdownSelect v-model="channelDataBits" :options="['7', '8']" />
                    </label>
                    <label>
                      停止位                      <DropdownSelect v-model="channelStopBits" :options="['1', '1.5', '2']" />
                    </label>
                  </div>
                  <div class="form-grid triple">
                    <label>
                      校验位                      <DropdownSelect
                        v-model="channelParity"
                        :options="[
                          { label: '无校验', value: 'none' },
                          { label: '奇校验', value: 'odd' },
                          { label: '偶校验', value: 'even' },
                        ]"
                      />
                    </label>
                  </div>
                </div>

                <div class="modal-section" v-else>
                  <div class="form-grid">
                    <label>
                      TCP 端口
                      <input v-model.number="channelTcpPort" type="number" />
                    </label>
                  </div>
                </div>

                <label class="channel-toggle">
                  <input v-model="channelAutoConnect" type="checkbox" />
                  <span>创建后立即启动连接</span>
                </label>
              </div>
              <div class="modal-footer">
                <button class="btn btn-outline" type="button" @click="closeChannelDialog">取消</button>
                <button class="btn btn-primary" type="button" @click="submitChannelDialog">创建通道</button>
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="currentView === 'protocols'" class="page">
          <header class="page-header spaced">
            <div>
              <h2>协议管理</h2>
              <p>配置通信协议定义，绑定通道并设置解析规则。</p>
            </div>
            <div class="header-actions">
              <button class="btn btn-outline" @click="refreshProtocols">
                <span class="material-symbols-outlined">refresh</span>
                刷新
              </button>
              <button class="btn btn-primary">
                <span class="material-symbols-outlined">add</span>
                新建协议
              </button>
            </div>
          </header>
          <div class="tab-strip secondary">
            <button :class="{ active: protocolTab === 'all' }" @click="setProtocolTab('all')">全部协议</button>
            <button :class="{ active: protocolTab === 'modbus' }" @click="setProtocolTab('modbus')">Modbus</button>
            <button :class="{ active: protocolTab === 'tcp' }" @click="setProtocolTab('tcp')">TCP/IP</button>
            <button :class="{ active: protocolTab === 'custom' }" @click="setProtocolTab('custom')">自定义</button>
          </div>
          <div class="protocol-grid">
            <div v-for="card in filteredProtocolCards" :key="card.id" class="protocol-card">
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
            <div v-if="filteredProtocolCards.length === 0" class="protocol-card empty">
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
              <button class="btn btn-outline" :disabled="!settingsDirty" @click="discardSettings">放弃更改</button>
              <button class="btn btn-primary" :disabled="!settingsDirty || settingsSaving" @click="saveSettings">
                <span class="material-symbols-outlined">save</span>
                保存更改
              </button>
            </div>
          </header>
          <div class="tab-strip secondary">
            <button :class="{ active: settingsTab === 'general' }" @click="setSettingsTab('general')">通用</button>
            <button :class="{ active: settingsTab === 'network' }" @click="setSettingsTab('network')">网络与端口</button>
            <button :class="{ active: settingsTab === 'plugins' }" @click="setSettingsTab('plugins')">插件</button>
            <button :class="{ active: settingsTab === 'runtime' }" @click="setSettingsTab('runtime')">运行时</button>
            <button :class="{ active: settingsTab === 'logs' }" @click="setSettingsTab('logs')">日志</button>
          </div>

          <div class="settings-stack">
            <div class="panel" ref="settingsGeneralRef">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">tune</span>
                通用偏好
              </div>
              <div class="form-grid">
                <label>
                  界面语言
                  <DropdownSelect
                    v-model="uiLanguage"
                    :options="['简体中文', 'English (US)', 'Deutsch', '日本語']"
                  />
                </label>
                <label>
                  主题偏好
                  <DropdownSelect
                    v-model="uiTheme"
                    :options="['系统默认', '深色 (工程模式)', '浅色']"
                  />
                </label>
              </div>
              <div class="toggle-row spaced">
                <div>
                  <strong>启动时自动连接</strong>
                  <p>自动尝试重连上次活动的通道。</p>
                </div>
                <label class="switch">
                  <input v-model="autoConnectOnStart" type="checkbox" />
                  <span></span>
                </label>
              </div>
            </div>

            <div class="panel" ref="settingsNetworkRef">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">router</span>
                网络连接设置
              </div>
              <div class="section-title">TCP / IP 配置</div>
              <div class="form-grid triple">
                <label>
                  发送超时 (ms)
                  <input v-model.number="tcpTimeoutMs" type="number" />
                </label>
                <label>
                  心跳间隔 (s)
                  <input v-model.number="tcpHeartbeatSec" type="number" />
                </label>
                <label>
                  重试次数
                  <input v-model.number="tcpRetryCount" type="number" />
                </label>
              </div>
              <div class="divider"></div>
              <div class="section-title">串口配置</div>
              <div class="form-grid triple">
                <label>
                  波特率                  <DropdownSelect v-model="defaultBaud" :options="[9600, 19200, 38400, 57600, 115200]" />
                </label>
                <label>
                  校验位                  <DropdownSelect
                    v-model="defaultParity"
                  :options="['无校验', '偶校验', '奇校验', '标记校验', '空格校验']"
                  />
                </label>
                <label>
                  停止位                  <DropdownSelect v-model="defaultStopBits" :options="['1', '1.5', '2']" />
                </label>
              </div>
            </div>

            <div class="panel" ref="settingsPluginsRef">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">extension</span>
                DSL 脚本目录
              </div>
              <label class="file-row">
                工作目录
                <div class="file-input">
                  <span class="material-symbols-outlined">folder_open</span>
                  <input v-model="dslWorkspacePath" type="text" readonly />
                </div>
                <button class="btn btn-outline" type="button" @click="chooseDslWorkspace">选择目录</button>
              </label>
              <div class="divider"></div>
              <div class="panel-title simple inline">
                插件管理
                <button class="link-btn">
                  <span class="material-symbols-outlined">refresh</span>
                  刷新列表
                </button>
              </div>
              <div class="plugin-list">
                <div class="plugin-item">
                  <div>
                    <div class="plugin-title">Modbus TCP/RTU</div>
                    <div class="plugin-meta">v1.2.4 - 已启用</div>
                  </div>
                  <span class="badge badge-green">已启用</span>
                </div>
                <div class="plugin-item muted">
                  <div>
                    <div class="plugin-title">MQTT 适配器</div>
                    <div class="plugin-meta">v0.9.8 - 未安装</div>
                  </div>
                  <span class="badge badge-gray">未安装</span>
                </div>
              </div>
              <div class="toggle-row spaced">
                <div>
                  <strong>启动时自动连接</strong>
                  <p>自动尝试重连上次活动的通道。</p>
                </div>
                <label class="switch">
                  <input v-model="autoConnectOnStart" type="checkbox" />
                  <span></span>
                </label>
              </div>
            </div>

            <div class="panel" ref="settingsRuntimeRef">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">tune</span>
                运行时
              </div>
              <div class="empty-state muted">
                暂无可配置项，运行时设置将随着模块扩展开放。
              </div>
            </div>

            <div class="panel" ref="settingsLogsRef">
              <div class="panel-title simple">
                <span class="material-symbols-outlined">folder_open</span>
                日志
              </div>
              <div class="empty-state muted">
                日志采集与归档策略将在后续版本中提供。
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>

    <div v-if="snapPreview" class="snap-overlay" :class="`snap-${snapPreview}`"></div>
  </div>
</template>
