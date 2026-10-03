/**
 * dsh-task-notifier — DSHA builtin server plugin.
 *
 * 精准任务完成通知：监听 session/event 的 turn/end（整轮对话结束 =
 * agent 任务完成），通过 DSHA 设备桥发 App 通知栏提醒。
 * 取代 App 端 TaskNotifier 的「轮询会话文件」方案（不准）。
 *
 * 链路：turn/end → 调设备桥的 /app/notify?title=&text=&token=（端口见 /root/.dsh/.bridge_port）
 * App 收到后在后台发通知（App 前台时 TaskNotifier 抑制，这里插件无感知——
 * 由 App 端 /app/notify 处理前台判断）。
 */

/** 无额外依赖（监听 session/event 是 cordis 核心事件，任何插件可用） */
export const inject = []
export const name = 'dsh-task-notifier'

/** 通知节流：同一 agent 30s 内只发一次（防连续 turn/end 轰炸） */
const THROTTLE_MS = 30_000
export function completionNotice(reason) {
  if (reason === 'completed') return ['DSHA · 任务完成', 'Agent 已完成一轮对话，点击查看结果']
  if (reason === 'max-tokens') return ['DSHA · 已达到输出上限', '请查看结果，按需继续对话']
  if (reason === 'aborted' || reason === 'interrupted') return ['DSHA · 任务已停止', '本轮任务未完成，点击查看状态']
  return ['DSHA · 任务需要处理', '本轮任务因错误或阻塞结束，请查看对话详情']
}

/** 通过设备桥发 App 通知（token 鉴权） */
async function notifyApp(title, text) {
  try {
    const fs = await import('node:fs/promises')
    let token = ''
    try {
      token = (await fs.readFile('/root/.dsh/.bridge_token', 'utf-8')).trim()
    } catch {}
    if (!token) return
    // 端口不写死：App 会把生效的设备桥端口写进 /root/.dsh/.bridge_port
    // （每个 App 自己的端口，写死会在多个 DSHA 版本同时运行时连错桥）。
    let port = 3190
    try {
      const raw = (await fs.readFile('/root/.dsh/.bridge_port', 'utf-8')).trim()
      if (/^\d+$/.test(raw)) port = Number(raw)
    } catch {}
    // 用 fetch（node 18+ 内置）调设备桥 /app/notify
    const url = 'http://127.0.0.1:' + port + '/app/notify'
      + '?title=' + encodeURIComponent(title)
      + '&text=' + encodeURIComponent(text)
      + '&token=' + encodeURIComponent(token)
    const resp = await fetch(url, { signal: AbortSignal.timeout(5000) })
    await resp.text()
  } catch {}
}

/**
 * Plugin entry.
 * @param {import('@deepseek-ai/cordis').Context} ctx
 */
export function apply(ctx) {
  const lastNotified = new Map()
  ctx.on('dispose', () => lastNotified.clear())
  ctx.on('session/event', (session, event) => {
    try {
      if (event.type !== 'turn/end') return
      // 整轮结束 = 任务完成（turnEnds.reason.kind: completed / blocked / max-tokens 等）
      const reason = event.data?.reason?.kind ?? 'unknown'
      // 正常完成
      const sessionId = session?.id ?? 'session'
      const now = Date.now()
      const last = lastNotified.get(sessionId) ?? 0
      if (now - last < THROTTLE_MS) return
      lastNotified.set(sessionId, now)
      if (lastNotified.size > 256) lastNotified.delete(lastNotified.keys().next().value)
      const [title, text] = completionNotice(reason)
      void notifyApp(title, text)
    } catch {}
  })
}
