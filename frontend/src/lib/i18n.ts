export type UiLang = 'en' | 'fa'

const STORAGE_KEY = 'lang'

export function detectDefaultLang(): UiLang {
  if (typeof navigator === 'undefined') return 'en'
  const raw = (navigator.language || '').toLowerCase()
  return raw.startsWith('fa') ? 'fa' : 'en'
}

export function loadLang(): UiLang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'fa' || saved === 'en') return saved
  } catch {
    // ignore
  }
  return detectDefaultLang()
}

export function saveLang(lang: UiLang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // ignore
  }
}

export function applyDocumentLang(lang: UiLang): void {
  const root = document.documentElement
  root.lang = lang
  root.dir = lang === 'fa' ? 'rtl' : 'ltr'
  // Persian needs slightly more line-height than Latin at the same size.
  root.style.lineHeight = lang === 'fa' ? '1.7' : ''
}

export type Copy = {
  brand: string
  brandSub: string
  system: string
  overview: string
  gateway: string
  loop: string
  memory: string
  tools: string
  database: string
  ops: string
  compare: string
  settings: string
  live: string
  updated: string
  ago: string
  newChat: string
  history: string
  stats: string
  allMessages: string
  send: string
  messagePlaceholder: string
  dockEmpty: string
  langToggle: string
  comingSoon: string
  spent: string
  avgTurn: string
  turns: string
  toolCalls: string
  facts: string
  events: string
  gateHero: string
  gateEmpty: string
  gateCaption: (pct: number) => string
  latestTurn: string
  noTurns: string
  thinking: string
  architecture: string
  architectureSoon: string
  gateSkipped: string
  gateRetrieved: string
  chat: string
}

export const copy: Record<UiLang, Copy> = {
  en: {
    brand: 'Yar',
    brandSub: 'companion',
    system: 'System',
    overview: 'Overview',
    gateway: 'Gateway',
    loop: 'Loop',
    memory: 'Memory',
    tools: 'Tools',
    database: 'Database',
    ops: 'LLM Ops',
    compare: 'Compare',
    settings: 'Settings',
    live: 'live',
    updated: 'updated',
    ago: 'ago',
    newChat: 'New chat',
    history: 'History',
    stats: 'stats',
    allMessages: 'All messages',
    send: 'Send',
    messagePlaceholder: 'Message Yar…',
    dockEmpty:
      "Message Yar here from any tab. Open Overview to watch it flow through the harness, or the Gateway tab to see every channel's messages together.",
    langToggle: 'فارسی',
    comingSoon: 'Coming in a later slice.',
    spent: 'spent · all-time',
    avgTurn: 'avg turn',
    turns: 'turns',
    toolCalls: 'tool calls',
    facts: 'facts',
    events: 'events',
    gateHero: 'Retrieval gate — the hero decision',
    gateEmpty: 'no turns yet — send a message and the gate starts deciding',
    gateCaption: (pct: number) =>
      `the retrieval gate skipped memory on ${pct}% of turns — that's latency and bias saved`,
    latestTurn: 'Latest turn',
    noTurns: 'no turns yet',
    thinking: 'thinking…',
    architecture: 'Architecture',
    architectureSoon: 'Architecture diagram arrives with the next frontend issue.',
    gateSkipped: 'skipped',
    gateRetrieved: 'retrieved',
    chat: 'Chat',
  },
  fa: {
    brand: 'یار',
    brandSub: 'همراه',
    system: 'سامانه',
    overview: 'نمای کلی',
    gateway: 'درگاه',
    loop: 'حلقه',
    memory: 'حافظه',
    tools: 'ابزارها',
    database: 'پایگاه داده',
    ops: 'عملیات LLM',
    compare: 'مقایسه',
    settings: 'تنظیمات',
    live: 'زنده',
    updated: 'به‌روز',
    ago: 'پیش',
    newChat: 'گفتگوی تازه',
    history: 'تاریخچه',
    stats: 'آمار',
    allMessages: 'همه پیام‌ها',
    send: 'ارسال',
    messagePlaceholder: 'پیام به یار…',
    dockEmpty:
      'از هر برگه‌ای اینجا به یار پیام بدهید. نمای کلی جریان هارنس را نشان می‌دهد؛ درگاه همه کانال‌ها را یک‌جا.',
    langToggle: 'English',
    comingSoon: 'در برش بعدی می‌آید.',
    spent: 'هزینه · کل',
    avgTurn: 'میانگین نوبت',
    turns: 'نوبت‌ها',
    toolCalls: 'فراخوان ابزار',
    facts: 'حقایق',
    events: 'رویدادها',
    gateHero: 'دروازه بازیابی — تصمیم اصلی',
    gateEmpty: 'هنوز نوبتی نیست — پیام بفرستید تا دروازه شروع کند',
    gateCaption: (pct: number) =>
      `دروازه بازیابی حافظه را در ${pct}٪ نوبت‌ها رد کرد — یعنی تأخیر و سوگیری کمتر`,
    latestTurn: 'آخرین نوبت',
    noTurns: 'هنوز نوبتی نیست',
    thinking: 'در حال فکر…',
    architecture: 'معماری',
    architectureSoon: 'نمودار معماری با شماره بعدی فرانت‌اند می‌آید.',
    gateSkipped: 'رد شده',
    gateRetrieved: 'بازیابی',
    chat: 'گفتگو',
  },
}
