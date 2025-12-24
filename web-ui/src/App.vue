<script setup>
import { onMounted, ref } from 'vue'

const bridge = ref(null)
const status = ref('disconnected')
const ports = ref([])
const selectedPort = ref('')
const baud = ref(115200)
const tcpHost = ref('127.0.0.1')
const tcpPort = ref(502)
const sendText = ref('')
const sendHex = ref('')
const commLogs = ref([])
const scriptLogs = ref([])
const scriptState = ref('idle')
const scriptProgress = ref(0)
const yamlText = ref('# paste DSL YAML here')

function addCommLog(kind, payload) {
  const line = `[${kind}] ${payload.text || ''} ${payload.hex ? `(0x${payload.hex})` : ''}`
  commLogs.value.unshift(line.trim())
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
      addCommLog('FRAME', { text: JSON.stringify(item.payload) })
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

function disconnect() {
  if (!bridge.value) return
  bridge.value.disconnect()
}

function sendAscii() {
  if (!bridge.value || !sendText.value) return
  bridge.value.send_text(sendText.value)
}

function sendHexData() {
  if (!bridge.value || !sendHex.value) return
  bridge.value.send_hex(sendHex.value)
}

function runScript() {
  if (!bridge.value || !yamlText.value) return
  bridge.value.run_script(yamlText.value)
}

function stopScript() {
  if (!bridge.value) return
  bridge.value.stop_script()
}

function attachBridge(obj) {
  bridge.value = obj
  obj.comm_batch.connect((batch) => addCommBatch(batch))
  obj.comm_status.connect((payload) => {
    const text = typeof payload === 'string' ? payload : JSON.stringify(payload)
    status.value = text
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
})
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">ProtoFlow Web UI</div>
      <div class="status">Status: {{ status }}</div>
    </header>

    <main class="grid">
      <section class="panel">
        <h2>Connection</h2>
        <div class="field">
          <label>Serial Port</label>
          <el-select v-model="selectedPort" placeholder="Select port" filterable>
            <el-option v-for="item in ports" :key="item" :label="item" :value="item" />
          </el-select>
          <el-button type="primary" plain size="small" @click="refreshPorts">Refresh</el-button>
        </div>
        <div class="field">
          <label>Baud</label>
          <el-input-number v-model="baud" :min="300" :max="2000000" controls-position="right" />
        </div>
        <div class="row">
          <el-button type="primary" @click="connectSerial">Connect Serial</el-button>
          <el-button plain @click="disconnect">Disconnect</el-button>
        </div>

        <div class="divider"></div>

        <div class="field">
          <label>TCP Host</label>
          <el-input v-model="tcpHost" placeholder="127.0.0.1" />
        </div>
        <div class="field">
          <label>TCP Port</label>
          <el-input-number v-model="tcpPort" :min="1" :max="65535" controls-position="right" />
        </div>
        <div class="row">
          <el-button type="primary" @click="connectTcp">Connect TCP</el-button>
        </div>
      </section>

      <section class="panel">
        <h2>Console</h2>
        <div class="field">
          <label>Send Text</label>
          <el-input v-model="sendText" placeholder="ASCII payload" />
          <el-button type="primary" @click="sendAscii">Send</el-button>
        </div>
        <div class="field">
          <label>Send Hex</label>
          <el-input v-model="sendHex" placeholder="AA 55 0D" />
          <el-button type="primary" @click="sendHexData">Send</el-button>
        </div>
        <div class="log">
          <el-fixed-size-list
            :data="commLogs"
            :total="commLogs.length"
            :height="200"
            :item-size="18"
          >
            <template #default="{ data, index, style }">
              <div class="log-line" :style="style">{{ data[index] }}</div>
            </template>
          </el-fixed-size-list>
        </div>
      </section>

      <section class="panel">
        <h2>Script Runner</h2>
        <div class="field">
          <label>State</label>
          <el-tag type="info">{{ scriptState }}</el-tag>
        </div>
        <div class="field">
          <label>Progress</label>
          <el-progress :percentage="scriptProgress" :stroke-width="8" />
        </div>
        <el-input v-model="yamlText" type="textarea" :rows="10" />
        <div class="row">
          <el-button type="primary" @click="runScript">Run</el-button>
          <el-button plain @click="stopScript">Stop</el-button>
        </div>
        <div class="log">
          <el-fixed-size-list
            :data="scriptLogs"
            :total="scriptLogs.length"
            :height="200"
            :item-size="18"
          >
            <template #default="{ data, index, style }">
              <div class="log-line" :style="style">{{ data[index] }}</div>
            </template>
          </el-fixed-size-list>
        </div>
      </section>
    </main>
  </div>
</template>
