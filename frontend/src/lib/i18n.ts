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
  save: string
  apiKey: string
  baseUrl: string
  baseUrlHint: string
  yourModels: string
  yourModelsSub: string
  currentModels: string
  loopModel: string
  smallModel: string
  addModel: string
  add: string
  makeDefault: string
  remove: string
  switching: string
  switchedTo: (model: string) => string
  gateNow: (model: string) => string
  modelNow: (model: string) => string
  searchKey: string
  searchKeyHint: string
  catalog: string
  catalogFilter: string
  useModel: string
  useAsGate: string
  current: string
  gateLabel: string
  noPins: string
  modelListUnavailable: (msg: string) => string
  modelsOn: (n: number, endpoint: string) => string
  pinTitle: string
  unpinTitle: string
  keySet: (last4: string) => string
  keyUnset: string
  edit: string
  delete: string
  cancel: string
  run: string
  error: string
  savedLive: string
  confirmDeleteMemory: string
  saveSkill: string
  saveSoul: string
  gatewayIntro: string
  noConversations: string
  subOverview: string
  subSemantic: string
  subEpisodic: string
  subSkills: string
  subSoul: string
  subConsolidation: string
  subAvailable: string
  subResults: string
  subMcp: string
  subQuery: string
  semanticIntro: string
  noFacts: string
  noEpisodes: string
  noSkills: string
  soulIntro: string
  episodicWhyTitle: string
  episodicWhyBody: string
  skillsIntro: string
  consolidationHowTitle: string
  consolidationHowBody: (n: number) => string
  messagesQueued: string
  triggerThreshold: string
  factsFromConsolidation: string
  episodesTotal: string
  distilledFacts: string
  memoryVsDbTitle: string
  memoryVsDbBody: string
  memoryVsDbBody2: string
  threePillars: string
  pillarSemanticDesc: string
  pillarEpisodicDesc: string
  pillarSkillsDesc: string
  memoryGateNote: string
  filesLabel: string
  toolsAvailableIntro: string
  toolsFlagship: string
  toolsWeb: string
  toolsSelfMgmt: string
  toolsMcpGroup: string
  toolsExperimental: string
  toolsOther: string
  toolsComingSoon: string
  toolsResultsIntro: string
  calendarEvents: string
  noEvents: string
  alsoWrittenTo: string
  outboxTitle: string
  openOutbox: string
  noOutbox: string
  mcpTitle: string
  mcpConnected: string
  mcpConfigured: string
  mcpNotSetup: string
  mcpIntro: string
  mcpServers: string
  mcpStartChat: string
  mcpConnectTitle: string
  mcpStep1: string
  mcpStep2: string
  mcpStep3: string
  queryIntro: string
  tryExamples: string
  running: string
  dbVsMemoryTitle: string
  dbVsMemoryBody: string
  dbVsMemoryBody2: string
  tablesTitle: string
  ftsTitle: string
  ftsBody: string
  tokensInAll: string
  tokensOutAll: string
  llmCalls: string
  toolErrors: string
  spendTitle: string
  spendBody: string
  spendByProvider: string
  spendPerDay: string
  gateOpsTitle: string
  gateDecisionsNote: string
  releaseGateTitle: string
  releaseGateBody: string
  evalHistory: string
  slowestTurns: string
  tracingTitle: string
  openTraces: string
  traceTailNote: string
  noTraceLines: string
  traceOtelHint: string
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
    save: 'Save',
    apiKey: 'OpenAI API key',
    baseUrl: 'Base URL',
    baseUrlHint: 'Optional OpenAI-compatible endpoint (e.g. AvalAI)',
    yourModels: 'Your models',
    yourModelsSub: 'shown in the chat switcher',
    currentModels: 'Current',
    loopModel: 'Loop model',
    smallModel: 'Small model (gate / summarizer)',
    addModel: 'Model id',
    add: 'Add',
    makeDefault: 'make default',
    remove: 'remove',
    switching: 'switching…',
    switchedTo: (model: string) => `Switched to ${model} — live now.`,
    gateNow: (model: string) => `Gate model is now ${model}. Applies from your next message.`,
    modelNow: (model: string) => `Model is now ${model}. Applies from your next message.`,
    searchKey: 'Tavily search key',
    searchKeyHint: 'Optional — web search tool',
    catalog: 'Model catalog',
    catalogFilter: 'Filter models…',
    useModel: 'use',
    useAsGate: 'gate',
    current: 'CURRENT',
    gateLabel: 'GATE',
    noPins: 'No models pinned yet — add one below.',
    modelListUnavailable: (msg: string) => `Model list unavailable: ${msg}`,
    modelsOn: (n: number, endpoint: string) =>
      `${n} models on ${endpoint} · click to switch`,
    pinTitle: 'Pin to your models',
    unpinTitle: 'Remove from your models',
    keySet: (last4: string) => `set ····${last4}`,
    keyUnset: 'not set',
    edit: 'Edit',
    delete: 'Delete',
    cancel: 'Cancel',
    run: 'Run',
    error: 'Error',
    savedLive: 'Saved — live next turn.',
    confirmDeleteMemory: 'Delete this from memory?',
    saveSkill: 'Save SKILL.md',
    saveSoul: 'Save SOUL.md',
    gatewayIntro:
      'Every conversation across dashboard and CLI — answered by the same brain. Click one to open it in the chat dock. This is the inbox; the dock is the open thread.',
    noConversations: 'No conversations yet — say something in the chat dock.',
    subOverview: 'Overview',
    subSemantic: 'Semantic',
    subEpisodic: 'Episodic',
    subSkills: 'Skills',
    subSoul: 'SOUL',
    subConsolidation: 'Consolidation',
    subAvailable: 'Available',
    subResults: 'Results',
    subMcp: 'MCP',
    subQuery: 'SQL console',
    semanticIntro:
      'Durable facts distilled from what you tell Yar — edit or forget any of them; changes are live next turn.',
    noFacts: 'No facts yet',
    noEpisodes: 'No episodes yet',
    noSkills: 'No skills loaded',
    soulIntro:
      'SOUL.md is Yar\'s persona — the system prompt it loads every turn. Editing it changes who your Yar is.',
    episodicWhyTitle: 'Why is this small?',
    episodicWhyBody:
      'Episodic memory holds one distilled summary per consolidation, not every message. Raw conversation lives in the chat_log table on the Database tab.',
    skillsIntro:
      'Procedural memory — markdown instructions loaded only when a message matches. Edit below or drop a SKILL.md into .yar/skills/.',
    consolidationHowTitle: 'How it works.',
    consolidationHowBody: (n: number) =>
      `Every ${n} exchanges, a cheap model reads unconsolidated chat_log and distills it into facts (semantic) plus one episode (episodic).`,
    messagesQueued: 'messages queued',
    triggerThreshold: 'trigger threshold',
    factsFromConsolidation: 'facts from consolidation',
    episodesTotal: 'episodes total',
    distilledFacts: 'Facts it distilled',
    memoryVsDbTitle: 'Memory vs Database — two views of one file.',
    memoryVsDbBody:
      'This tab is the curated, per-pillar view of what Yar remembers. The',
    memoryVsDbBody2:
      ' tab shows the exact same thing as raw SQLite tables (plus FTS5). Same .yar/state.db — different altitude.',
    threePillars: 'The three pillars',
    pillarSemanticDesc: 'durable, distilled facts about you and your people',
    pillarEpisodicDesc: 'one dated summary per consolidation — stays small on purpose',
    pillarSkillsDesc: 'SKILL.md files loaded only when relevant — how to act',
    memoryGateNote:
      'A cheap model decides if a turn needs memory at all, before any lookup — the hero retrieval decision.',
    filesLabel: 'Files',
    toolsAvailableIntro: 'The capabilities the agent can call this turn. Connect more via',
    toolsFlagship: 'Flagship task — scheduling',
    toolsWeb: 'Web search',
    toolsSelfMgmt: 'Self-management — it edits its own memory',
    toolsMcpGroup: 'MCP servers',
    toolsExperimental: 'Experimental',
    toolsOther: 'Other',
    toolsComingSoon: 'Coming soon',
    toolsResultsIntro: 'What tool calls actually wrote. These are results, not the tools.',
    calendarEvents: 'Calendar events',
    noEvents: 'No events yet',
    alsoWrittenTo: 'Also written to',
    outboxTitle: 'Outbox — drafted messages',
    openOutbox: 'open outbox folder',
    noOutbox: 'No drafted messages',
    mcpTitle: 'Model Context Protocol',
    mcpConnected: ' — connected',
    mcpConfigured: ' — configured',
    mcpNotSetup: ' — not set up',
    mcpIntro:
      'MCP lets Yar borrow tools from any external server, namespaced server_tool.',
    mcpServers: 'Configured servers',
    mcpStartChat: 'start a chat to connect them',
    mcpConnectTitle: 'Connect one (30 seconds)',
    mcpStep1: 'install the extra: uv sync --extra mcp',
    mcpStep2: 'create',
    mcpStep3: 'restart the dashboard. Server tools appear under',
    queryIntro:
      'A read-only SQL console over state.db. Only SELECT runs — the file is opened read-only.',
    tryExamples: 'try',
    running: 'running…',
    dbVsMemoryTitle: 'Database vs Memory.',
    dbVsMemoryBody: 'This is the raw persistence layer — literal SQLite tables. The',
    dbVsMemoryBody2:
      ' tab is the friendly view of the same rows. One file, two altitudes.',
    tablesTitle: 'Tables — click a tab above, or a row here',
    ftsTitle: 'FTS5 — the keyword index',
    ftsBody:
      'The *_fts virtual tables make memory searchable by keyword — no embeddings, no vector DB.',
    tokensInAll: 'tokens in · all-time',
    tokensOutAll: 'tokens out · all-time',
    llmCalls: 'LLM calls',
    toolErrors: 'tool errors',
    spendTitle: 'Spend · permanent ledger',
    spendBody:
      'Every LLM call\'s tokens are logged to .yar/usage.jsonl (append-only). Dollar cost is estimated from tokens × pricing.',
    spendByProvider: 'Spend by provider',
    spendPerDay: 'Spend per day',
    gateOpsTitle: 'Retrieval gate — which turns used memory',
    gateDecisionsNote: 'The actual decisions (skipped vs retrieved), most recent first:',
    releaseGateTitle: 'Release gate · the ship/no-ship check',
    releaseGateBody:
      'Before you ship a change, make gate runs deterministic evals (must pass 100%) and judge evals. Manual — one record per run.',
    evalHistory: 'Eval history',
    slowestTurns: 'Slowest turns',
    tracingTitle: 'Tracing · every turn as JSONL',
    openTraces: 'open traces folder',
    traceTailNote: 'A trace is what happened, in order — recent lines:',
    noTraceLines: 'No trace lines yet — talk to Yar',
    traceOtelHint: 'Span waterfalls: make trace + OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317',
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
    save: 'ذخیره',
    apiKey: 'کلید OpenAI',
    baseUrl: 'آدرس پایه',
    baseUrlHint: 'endpoint سازگار با OpenAI (مثلاً AvalAI)',
    yourModels: 'مدل‌های شما',
    yourModelsSub: 'در سوئیچر گفتگو',
    currentModels: 'فعلی',
    loopModel: 'مدل حلقه',
    smallModel: 'مدل کوچک (دروازه / خلاصه‌ساز)',
    addModel: 'شناسه مدل',
    add: 'افزودن',
    makeDefault: 'پیش‌فرض',
    remove: 'حذف',
    switching: 'در حال تعویض…',
    switchedTo: (model: string) => `به ${model} تعویض شد — اکنون فعال است.`,
    gateNow: (model: string) =>
      `مدل دروازه اکنون ${model} است. از پیام بعدی اعمال می‌شود.`,
    modelNow: (model: string) =>
      `مدل اکنون ${model} است. از پیام بعدی اعمال می‌شود.`,
    searchKey: 'کلید جستجوی Tavily',
    searchKeyHint: 'اختیاری — ابزار جستجوی وب',
    catalog: 'فهرست مدل‌ها',
    catalogFilter: 'فیلتر مدل‌ها…',
    useModel: 'استفاده',
    useAsGate: 'دروازه',
    current: 'فعلی',
    gateLabel: 'دروازه',
    noPins: 'هنوز مدلی سنجاق نشده — پایین اضافه کنید.',
    modelListUnavailable: (msg: string) => `فهرست مدل در دسترس نیست: ${msg}`,
    modelsOn: (n: number, endpoint: string) =>
      `${n} مدل روی ${endpoint} · برای تعویض کلیک کنید`,
    pinTitle: 'سنجاق به مدل‌های شما',
    unpinTitle: 'حذف از مدل‌های شما',
    keySet: (last4: string) => `تنظیم ····${last4}`,
    keyUnset: 'تنظیم نشده',
    edit: 'ویرایش',
    delete: 'حذف',
    cancel: 'لغو',
    run: 'اجرا',
    error: 'خطا',
    savedLive: 'ذخیره شد — از نوبت بعد فعال است.',
    confirmDeleteMemory: 'این مورد از حافظه حذف شود؟',
    saveSkill: 'ذخیره SKILL.md',
    saveSoul: 'ذخیره SOUL.md',
    gatewayIntro:
      'همه گفتگوها از داشبورد و CLI — یک مغز مشترک. برای باز کردن در داک گفتگو کلیک کنید. این صندوق ورودی است؛ داک رشته باز است.',
    noConversations: 'هنوز گفتگویی نیست — در داک گفتگو پیام بدهید.',
    subOverview: 'نمای کلی',
    subSemantic: 'معنایی',
    subEpisodic: 'رویدادی',
    subSkills: 'مهارت‌ها',
    subSoul: 'SOUL',
    subConsolidation: 'تجمیع',
    subAvailable: 'موجود',
    subResults: 'نتایج',
    subMcp: 'MCP',
    subQuery: 'کنسول SQL',
    semanticIntro:
      'حقایق پایدار استخراج‌شده از گفتگو — ویرایش یا حذف؛ تغییرات از نوبت بعد اعمال می‌شود.',
    noFacts: 'هنوز حقیقتی نیست',
    noEpisodes: 'هنوز رویدادی نیست',
    noSkills: 'مهارتی بارگذاری نشده',
    soulIntro:
      'SOUL.md شخصیت یار است — پرامپت سیستمی که هر نوبت بارگذاری می‌شود.',
    episodicWhyTitle: 'چرا کوچک است؟',
    episodicWhyBody:
      'حافظه رویدادی یک خلاصه مقطر در هر تجمیع نگه می‌دارد، نه هر پیام. گفتگوی خام در جدول chat_log در برگه پایگاه داده است.',
    skillsIntro:
      'حافظه رویه‌ای — دستورالعمل markdown فقط وقتی پیام مرتبط باشد. ویرایش پایین یا SKILL.md در .yar/skills/.',
    consolidationHowTitle: 'چگونه کار می‌کند.',
    consolidationHowBody: (n: number) =>
      `هر ${n} مبادله، مدل ارزان chat_log تجمیع‌نشده را می‌خواند و به حقایق (معنایی) و یک رویداد (رویدادی) تقطیر می‌کند.`,
    messagesQueued: 'پیام در صف',
    triggerThreshold: 'آستانه راه‌اندازی',
    factsFromConsolidation: 'حقایق از تجمیع',
    episodesTotal: 'کل رویدادها',
    distilledFacts: 'حقایق تقطیرشده',
    memoryVsDbTitle: 'حافظه در برابر پایگاه داده — دو نمای یک فایل.',
    memoryVsDbBody: 'این برگه نمای منتخب ستون‌های حافظه یار است.',
    memoryVsDbBody2:
      ' همان داده را به‌صورت جداول SQLite خام (به‌علاوه FTS5) نشان می‌دهد. همان .yar/state.db — ارتفاع متفاوت.',
    threePillars: 'سه ستون',
    pillarSemanticDesc: 'حقایق پایدار درباره شما و اطرافیان',
    pillarEpisodicDesc: 'یک خلاصه تاریخ‌دار در هر تجمیع — عمداً کوچک',
    pillarSkillsDesc: 'فایل‌های SKILL.md فقط وقتی مرتبط — نحوه عمل',
    memoryGateNote:
      'مدل ارزان پیش از هر جستجو تصمیم می‌گیرد آیا نوبت به حافظه نیاز دارد — تصمیم اصلی بازیابی.',
    filesLabel: 'فایل‌ها',
    toolsAvailableIntro: 'توانایی‌هایی که عامل این نوبت می‌تواند فراخوانی کند. بیشتر از طریق',
    toolsFlagship: 'وظیفه اصلی — زمان‌بندی',
    toolsWeb: 'جستجوی وب',
    toolsSelfMgmt: 'خودمدیریتی — ویرایش حافظه خود',
    toolsMcpGroup: 'سرورهای MCP',
    toolsExperimental: 'آزمایشی',
    toolsOther: 'سایر',
    toolsComingSoon: 'به‌زودی',
    toolsResultsIntro: 'آنچه فراخوان ابزار واقعاً نوشت. نتیجه است، نه خود ابزار.',
    calendarEvents: 'رویدادهای تقویم',
    noEvents: 'هنوز رویدادی نیست',
    alsoWrittenTo: 'همچنین نوشته شده در',
    outboxTitle: 'صندوق خروجی — پیام‌های پیش‌نویس',
    openOutbox: 'باز کردن پوشه outbox',
    noOutbox: 'پیش‌نویسی نیست',
    mcpTitle: 'Model Context Protocol',
    mcpConnected: ' — متصل',
    mcpConfigured: ' — پیکربندی‌شده',
    mcpNotSetup: ' — راه‌اندازی نشده',
    mcpIntro:
      'MCP به یار اجازه می‌دهد ابزار از سرور خارجی بگیرد، با نام server_tool.',
    mcpServers: 'سرورهای پیکربندی‌شده',
    mcpStartChat: 'برای اتصال گفتگو را شروع کنید',
    mcpConnectTitle: 'اتصال در ۳۰ ثانیه',
    mcpStep1: 'نصب extra: uv sync --extra mcp',
    mcpStep2: 'ایجاد',
    mcpStep3: 'داشبورد را راه‌اندازی مجدد کنید. ابزارها در',
    queryIntro:
      'کنسول SQL فقط-خواندنی روی state.db. فقط SELECT — فایل read-only باز می‌شود.',
    tryExamples: 'امتحان',
    running: 'در حال اجرا…',
    dbVsMemoryTitle: 'پایگاه داده در برابر حافظه.',
    dbVsMemoryBody: 'لایه persistence خام — جداول SQLite. برگه',
    dbVsMemoryBody2: ' همان سطرها را به‌صورت دوستانه نشان می‌دهد. یک فایل، دو ارتفاع.',
    tablesTitle: 'جداول — تب بالا یا سطر اینجا',
    ftsTitle: 'FTS5 — نمایه کلیدواژه',
    ftsBody:
      'جداول مجازی *_fts حافظه را با کلیدواژه قابل جستجو می‌کنند — بدون embedding.',
    tokensInAll: 'توکن ورودی · کل',
    tokensOutAll: 'توکن خروجی · کل',
    llmCalls: 'فراخوان LLM',
    toolErrors: 'خطای ابزار',
    spendTitle: 'هزینه · دفتر دائمی',
    spendBody:
      'توکن هر فراخوان LLM در .yar/usage.jsonl ثبت می‌شود. هزینه دلاری تخمینی است.',
    spendByProvider: 'هزینه به‌ازای ارائه‌دهنده',
    spendPerDay: 'هزینه روزانه',
    gateOpsTitle: 'دروازه بازیابی — کدام نوبت‌ها از حافظه استفاده کردند',
    gateDecisionsNote: 'تصمیم‌های واقعی (رد vs بازیابی)، جدیدترین اول:',
    releaseGateTitle: 'دروازه انتشار · بررسی ship/no-ship',
    releaseGateBody:
      'قبل از انتشار تغییر، make gate ارزیابی deterministic (۱۰۰٪) و judge را اجرا می‌کند.',
    evalHistory: 'تاریخچه ارزیابی',
    slowestTurns: 'کندترین نوبت‌ها',
    tracingTitle: 'ردیابی · هر نوبت JSONL',
    openTraces: 'باز کردن پوشه traces',
    traceTailNote: 'ردیابی «چه اتفاقی افتاد» به ترتیب — خطوط اخیر:',
    noTraceLines: 'هنوز خط ردیابی نیست — با یار صحبت کنید',
    traceOtelHint: 'نمودار span: make trace + OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317',
  },
}
